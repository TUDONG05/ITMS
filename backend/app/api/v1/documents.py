import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import InternshipPosition, UserRole
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentPage, DocumentRead, DocumentUpdate
from app.services.document import DocumentService
from app.services.document_storage import store_document

router = APIRouter(prefix="/documents", tags=["documents"])
admin_only = require_roles([UserRole.ADMIN])


@router.get("", response_model=DocumentPage)
def list_documents(
    search: str | None = Query(None, max_length=255),
    position: InternshipPosition | None = None,
    format: str | None = Query(None, min_length=1, max_length=20, pattern=r"^[A-Za-z0-9]+$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> DocumentPage:
    return DocumentService.list(db, search, position, format, skip, limit)


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(None),
    positions: str = Form("[]"),
    user: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> DocumentRead:
    try:
        metadata = DocumentUpdate(
            title=title,
            description=description,
            positions=json.loads(positions),
        )
    except (ValueError, ValidationError) as exc:
        raise HTTPException(422, "Tên tài liệu hoặc danh sách vị trí không hợp lệ.") from exc
    stored = await store_document(file)
    payload = DocumentCreate(
        title=metadata.title,
        description=metadata.description,
        positions=metadata.positions or [],
        url=stored["url"],
    )
    document = DocumentService.create(db, payload, user.id, commit=False)
    document.original_filename = stored["original_filename"]
    document.size_bytes = stored["size_bytes"]
    db.commit()
    db.refresh(document)
    return DocumentService.read(db, document)


@router.put("/{document_id}/file", response_model=DocumentRead)
async def replace_document_file(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(None),
    positions: str = Form("[]"),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> DocumentRead:
    # Check existence and validate metadata before storing an uploaded replacement.
    DocumentService.get(db, document_id)
    try:
        metadata = DocumentUpdate(
            title=title, description=description, positions=json.loads(positions)
        )
    except (ValueError, ValidationError) as exc:
        raise HTTPException(422, "Tên tài liệu hoặc danh sách vị trí không hợp lệ.") from exc
    stored = await store_document(file)
    document = DocumentService.replace_file(db, document_id, metadata, stored)
    return DocumentService.read(db, document)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: uuid.UUID, _: User = Depends(admin_only), db: Session = Depends(get_db)
) -> DocumentRead:
    return DocumentService.read(db, DocumentService.get(db, document_id))


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> DocumentRead:
    return DocumentService.read(db, DocumentService.update(db, document_id, payload))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID, _: User = Depends(admin_only), db: Session = Depends(get_db)
) -> None:
    DocumentService.delete(db, document_id)
