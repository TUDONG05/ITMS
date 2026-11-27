from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, inspect, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.document import DOCUMENT_FILE_FORMATS, Document, content_documents
from app.models.roadmap import LearningContent
from app.schemas.document import (
    DocumentCreate,
    DocumentPage,
    DocumentRead,
    DocumentUpdate,
    document_format,
)


def resource_urls(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        parsed = value
    items = parsed if isinstance(parsed, list) else [parsed]
    return list(
        dict.fromkeys(item.strip() for item in items if isinstance(item, str) and item.strip())
    )


def materialized_urls(urls: list[str]) -> str | None:
    urls = list(dict.fromkeys(urls))
    return json.dumps(urls, ensure_ascii=False) if len(urls) > 1 else (urls[0] if urls else None)


class DocumentService:
    @staticmethod
    def mutation_lock(db: Session) -> None:
        # Admin catalog edits and roadmap resource edits share materialized URLs.
        # One transaction-level lock keeps their read/merge/write cycle consistent
        # without taking document/content row locks in conflicting graph orders.
        db.execute(text("SELECT pg_advisory_xact_lock(46124839678395)"))

    @staticmethod
    def get(db: Session, document_id: uuid.UUID, lock=False) -> Document:
        query = select(Document).where(Document.id == document_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        document = db.scalar(query)
        if document is None:
            raise HTTPException(404, "Không tìm thấy tài liệu.")
        return document

    @staticmethod
    def read(db: Session, document: Document) -> DocumentRead:
        result = DocumentRead.model_validate(document)
        result.usage_count = (
            db.scalar(
                select(func.count())
                .select_from(content_documents)
                .where(content_documents.c.document_id == document.id)
            )
            or 0
        )
        return result

    @staticmethod
    def list(
        db: Session, search=None, position=None, format=None, skip=0, limit=20
    ) -> DocumentPage:
        query = select(Document).where(Document.format.in_(DOCUMENT_FILE_FORMATS))
        if search and search.strip():
            term = search.strip()
            query = query.where(
                or_(
                    Document.title.icontains(term, autoescape=True),
                    Document.description.icontains(term, autoescape=True),
                )
            )
        if position:
            query = query.where(
                or_(Document.positions == [], Document.positions.contains([position]))
            )
        if format:
            query = query.where(Document.format == format.lower())
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        documents = list(
            db.scalars(
                query.order_by(Document.updated_at.desc(), Document.id).offset(skip).limit(limit)
            )
        )
        ids = [document.id for document in documents]
        counts = (
            dict(
                db.execute(
                    select(content_documents.c.document_id, func.count())
                    .where(content_documents.c.document_id.in_(ids))
                    .group_by(content_documents.c.document_id)
                ).all()
            )
            if ids
            else {}
        )
        items = []
        for document in documents:
            item = DocumentRead.model_validate(document)
            item.usage_count = counts.get(document.id, 0)
            items.append(item)
        formats = list(
            db.scalars(
                select(Document.format)
                .where(Document.format.in_(DOCUMENT_FILE_FORMATS))
                .distinct()
                .order_by(Document.format)
            )
        )
        return DocumentPage(items=items, total=total, formats=formats)

    @staticmethod
    def create(db: Session, data: DocumentCreate, creator_id=None, commit=True) -> Document:
        DocumentService.mutation_lock(db)
        document = Document(
            **data.model_dump(), format=document_format(data.url), created_by=creator_id
        )
        try:
            with db.begin_nested():
                db.add(document)
                db.flush()
        except IntegrityError as exc:
            if (
                getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                == "document_library_url_key"
            ):
                raise HTTPException(409, "URL này đã có trong thư viện tài liệu.") from exc
            raise
        if commit:
            db.commit()
            db.refresh(document)
        return document

    @staticmethod
    def update(db: Session, document_id: uuid.UUID, data: DocumentUpdate) -> Document:
        return DocumentService._save_changes(db, document_id, data.model_dump(exclude_unset=True))

    @staticmethod
    def replace_file(
        db: Session, document_id: uuid.UUID, metadata: DocumentUpdate, stored: dict
    ) -> Document:
        # Uploaded sources only: reuse file-format validation used for catalog registration.
        validated = DocumentCreate(title=metadata.title or "File", url=stored["url"])
        changes = metadata.model_dump(exclude_unset=True)
        changes.update(
            url=validated.url,
            original_filename=stored["original_filename"],
            size_bytes=stored["size_bytes"],
        )
        return DocumentService._save_changes(db, document_id, changes)

    @staticmethod
    def _save_changes(db: Session, document_id: uuid.UUID, changes: dict) -> Document:
        DocumentService.mutation_lock(db)
        document = DocumentService.get(db, document_id, lock=True)
        old_url = document.url
        new_url = changes.get("url", old_url)
        if new_url != old_url:
            duplicate = db.scalar(
                select(Document.id).where(Document.url == new_url, Document.id != document_id)
            )
            if duplicate:
                raise HTTPException(409, "URL này đã có trong thư viện tài liệu.")
            linked = list(
                db.scalars(
                    select(LearningContent)
                    .join(content_documents, content_documents.c.content_id == LearningContent.id)
                    .where(content_documents.c.document_id == document_id)
                    .execution_options(populate_existing=True)
                )
            )
            for content in linked:
                urls = [
                    new_url if url == old_url else url
                    for url in resource_urls(content.resource_url)
                ]
                if new_url not in urls:
                    urls.append(new_url)
                content.resource_url = materialized_urls(urls)
                content.updated_at = datetime.now(UTC)
            changes["format"] = document_format(new_url)
        for key, value in changes.items():
            setattr(document, key, value)
        document.updated_at = datetime.now(UTC)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if (
                getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                == "document_library_url_key"
            ):
                raise HTTPException(409, "URL này đã có trong thư viện tài liệu.") from exc
            raise
        db.refresh(document)
        return document

    @staticmethod
    def delete(db: Session, document_id: uuid.UUID) -> None:
        DocumentService.mutation_lock(db)
        document = DocumentService.get(db, document_id, lock=True)
        used = db.scalar(
            select(content_documents.c.content_id)
            .where(content_documents.c.document_id == document_id)
            .limit(1)
        )
        if used is not None:
            raise HTTPException(409, "Tài liệu đang được sử dụng trong lộ trình, không thể xóa.")
        db.delete(document)
        db.commit()

    @staticmethod
    def bind_content(
        db: Session,
        content: LearningContent,
        document_ids: list[uuid.UUID] | None,
        submitted_resource_url: str | None,
        resource_url_provided: bool,
    ) -> None:
        DocumentService.mutation_lock(db)
        if inspect(content).persistent:
            db.refresh(content)
            db.expire(content, ["documents"])
            previous = list(
                db.scalars(
                    select(Document)
                    .join(content_documents, content_documents.c.document_id == Document.id)
                    .where(content_documents.c.content_id == content.id)
                    .order_by(Document.created_at, Document.id)
                    .execution_options(populate_existing=True)
                )
            )
        else:
            previous = list(content.documents)
        old_urls = {document.url for document in previous}
        urls = resource_urls(
            submitted_resource_url if resource_url_provided else content.resource_url
        )
        manual_urls = [url for url in urls if url not in old_urls]
        if document_ids is None:
            selected = previous
            # Legacy resource editors that submit an existing catalog URL reuse that entry.
            if resource_url_provided and manual_urls:
                matches = list(
                    db.scalars(
                        select(Document)
                        .where(
                            Document.url.in_(manual_urls),
                            Document.format.in_(DOCUMENT_FILE_FORMATS),
                        )
                        .order_by(Document.id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                )
                selected = list(
                    {document.id: document for document in [*previous, *matches]}.values()
                )
        else:
            unique_ids = list(dict.fromkeys(document_ids))
            selected = list(
                db.scalars(
                    select(Document)
                    .where(Document.id.in_(unique_ids))
                    .order_by(Document.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
            if len(selected) != len(unique_ids):
                raise HTTPException(404, "Một hoặc nhiều tài liệu đã chọn không tồn tại.")
        content.documents = selected
        content.resource_url = materialized_urls(
            [*manual_urls, *(document.url for document in selected)]
        )
