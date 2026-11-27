import json
import uuid
from importlib import import_module
from types import SimpleNamespace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_engine, get_session_factory
from app.main import app
from app.models.document import Document
from app.models.roadmap import LearningContent, Phase, Roadmap
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.schemas.training import LearningContentCreate, LearningContentUpdate
from app.services.document import DocumentService, resource_urls
from app.services.training import TrainingService


@pytest.fixture
def library_data():
    with get_session_factory()() as db:
        users = {
            role: User(
                email=f"library-{uuid.uuid4().hex}@example.com",
                password_hash="hash",
                full_name=role,
                role=role,
                status="ACTIVE",
            )
            for role in ("ADMIN", "MENTOR", "INTERN")
        }
        roadmap = Roadmap(name=f"Library {uuid.uuid4().hex}", status="ACTIVE")
        db.add_all([*users.values(), roadmap])
        db.flush()
        phases = [
            Phase(roadmap_id=roadmap.id, name=f"Phase {index}", order_no=index) for index in (1, 2)
        ]
        db.add_all(phases)
        db.commit()
        yield db, users, phases, roadmap


def h(users, role="ADMIN"):
    return {"X-User-Id": str(users[role].id)}


def create_doc(client, users, **kwargs):
    # Catalog records can be seeded internally, but the public API requires upload.
    payload = DocumentCreate(
        **{"title": "Document", "url": f"https://example.com/{uuid.uuid4().hex}.pdf", **kwargs}
    )
    with get_session_factory()() as db:
        document = DocumentService.create(db, payload, users["ADMIN"].id)
        return DocumentService.read(db, document).model_dump(mode="json")


def replace_source(db, document_id, url):
    return DocumentService.replace_file(
        db,
        document_id,
        DocumentUpdate(),
        {"url": url, "original_filename": url.rsplit("/", 1)[-1], "size_bytes": 1},
    )


def test_library_crud_permissions_and_file_only_contract(library_data):
    _, users, _, _ = library_data
    client = TestClient(app)
    assert client.get("/api/v1/documents").status_code == 401
    assert (
        client.post(
            "/api/v1/documents",
            headers=h(users),
            json={"title": "No URL creation", "url": "https://example.com/no.pdf"},
        ).status_code
        == 405
    )
    for role in ("INTERN", "MENTOR"):
        assert client.get("/api/v1/documents", headers=h(users, role)).status_code == 403
        assert (
            client.post(
                "/api/v1/documents/upload",
                headers=h(users, role),
                data={"title": "No"},
                files={"file": ("file.pdf", b"pdf", "application/pdf")},
            ).status_code
            == 403
        )
    document = create_doc(client, users, positions=["BACKEND", "BACKEND"], title="  API guide  ")
    assert document["title"] == "API guide"
    assert document["format"] == "pdf"
    assert document["positions"] == ["BACKEND"]
    assert document["usage_count"] == 0
    with pytest.raises(HTTPException) as duplicate:
        create_doc(client, users, url=document["url"])
    assert duplicate.value.status_code == 409
    for url in (
        "javascript:alert(1)",
        "/api/v1/uploads/training/../../secret",
        "https://example.com/%252e%252e/secret.pdf",
        "https://example.com/webpage",
        "https://example.com/index.html",
    ):
        with pytest.raises(ValidationError):
            DocumentCreate(title="Bad", url=url)
    for body in (
        {"title": " "},
        {"url": None},
        {"url": "https://example.com/file.pdf"},
        {"positions": ["INVALID"]},
    ):
        assert (
            client.patch(
                f"/api/v1/documents/{document['id']}", headers=h(users), json=body
            ).status_code
            == 422
        )
    for role in ("INTERN", "MENTOR"):
        assert (
            client.get(f"/api/v1/documents/{document['id']}", headers=h(users, role)).status_code
            == 403
        )
        assert (
            client.patch(
                f"/api/v1/documents/{document['id']}", headers=h(users, role), json={"title": "No"}
            ).status_code
            == 403
        )
        assert (
            client.delete(f"/api/v1/documents/{document['id']}", headers=h(users, role)).status_code
            == 403
        )
    updated = client.patch(
        f"/api/v1/documents/{document['id']}",
        headers=h(users),
        json={"title": "New", "description": "Description", "positions": []},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["format"] == "pdf"
    assert client.delete(f"/api/v1/documents/{document['id']}", headers=h(users)).status_code == 204
    assert client.get(f"/api/v1/documents/{document['id']}", headers=h(users)).status_code == 404


def test_library_filters_combine_common_positions_and_pagination(library_data):
    _, users, _, _ = library_data
    client = TestClient(app)
    common = create_doc(client, users, title="API 100% common", positions=[])
    backend = create_doc(client, users, title="API 100% backend", positions=["BACKEND"])
    create_doc(client, users, title="API 100% frontend", positions=["FRONTEND"])
    create_doc(client, users, title="API 100x video", url="https://example.com/video.mp4")
    response = client.get(
        "/api/v1/documents",
        headers=h(users),
        params={"search": "100%", "position": "BACKEND", "format": "PDF", "limit": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1
    assert payload["formats"] == ["mp4", "pdf"]
    second = client.get(
        "/api/v1/documents",
        headers=h(users),
        params={"search": "100%", "position": "BACKEND", "format": "pdf", "limit": 1, "skip": 1},
    ).json()
    assert {payload["items"][0]["id"], second["items"][0]["id"]} == {common["id"], backend["id"]}
    assert (
        client.get("/api/v1/documents", headers=h(users), params={"limit": 101}).status_code == 422
    )


def create_content(client, users, phase, **kwargs):
    response = client.post(
        "/api/v1/training/contents",
        headers=h(users),
        json={
            "phase_id": str(phase.id),
            "title": "Material",
            "type": "DOCUMENT",
            "order_no": 1,
            **kwargs,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_reuse_materializes_urls_and_updates_propagate_without_losing_manual_links(library_data):
    db, users, phases, roadmap = library_data
    client = TestClient(app)
    document = create_doc(client, users)
    manual = "https://example.com/manual"
    contents = [
        create_content(client, users, phase, document_ids=[document["id"]], resource_url=manual)
        for phase in phases
    ]
    assert all(content["document_ids"] == [document["id"]] for content in contents)
    assert contents[0]["documents"][0]["title"] == document["title"]
    assert json.loads(contents[0]["resource_url"]) == [manual, document["url"]]
    assert (
        client.get(f"/api/v1/documents/{document['id']}", headers=h(users)).json()["usage_count"]
        == 2
    )
    assert client.delete(f"/api/v1/documents/{document['id']}", headers=h(users)).status_code == 409
    new_url = "https://example.com/new.pdf"
    replace_source(db, uuid.UUID(document["id"]), new_url)
    db.expire_all()
    for content in contents:
        stored = db.get(LearningContent, uuid.UUID(content["id"]))
        assert json.loads(stored.resource_url) == [manual, new_url]
    detail = client.get(f"/api/v1/training/roadmaps/{roadmap.id}", headers=h(users)).json()
    assert detail["phases"][0]["contents"][0]["documents"][0]["url"] == new_url
    # Omitting selection preserves associations; removing it removes only catalog URLs.
    url = f"/api/v1/training/contents/{contents[0]['id']}"
    assert client.patch(url, headers=h(users), json={"title": "Changed"}).json()[
        "document_ids"
    ] == [document["id"]]
    removed = client.patch(url, headers=h(users), json={"document_ids": []}).json()
    assert removed["resource_url"] == manual
    assert removed["documents"] == []
    assert (
        client.delete(
            f"/api/v1/training/contents/{contents[1]['id']}", headers=h(users)
        ).status_code
        == 204
    )
    assert client.delete(f"/api/v1/documents/{document['id']}", headers=h(users)).status_code == 204


def test_legacy_resource_url_reuses_existing_catalog_and_bad_ids_fail(library_data):
    _, users, phases, _ = library_data
    client = TestClient(app)
    document = create_doc(client, users)
    content = create_content(client, users, phases[0], resource_url=document["url"])
    assert content["document_ids"] == [document["id"]]
    result = client.patch(
        f"/api/v1/training/contents/{content['id']}",
        headers=h(users),
        json={"document_ids": [str(uuid.uuid4())]},
    )
    assert result.status_code == 404


def test_upload_is_registered_in_catalog_and_validates_size_type(
    library_data, tmp_path, monkeypatch
):
    _, users, _, _ = library_data
    from app.services import document_storage

    monkeypatch.setattr(document_storage, "TRAINING_UPLOAD_DIR", tmp_path)
    for key in ("VERCEL", "BLOB_READ_WRITE_TOKEN", "BLOB_STORE_ID"):
        monkeypatch.delenv(key, raising=False)
    client = TestClient(app)
    response = client.post(
        "/api/v1/documents/upload",
        headers=h(users),
        data={"title": "Uploaded PDF", "positions": '["AI"]'},
        files={"file": ("guide.pdf", b"%PDF-test", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["positions"] == ["AI"]
    assert payload["original_filename"] == "guide.pdf"
    assert payload["size_bytes"] == 9
    assert payload["url"].startswith("/api/v1/uploads/training/")
    assert len(list(tmp_path.iterdir())) == 1
    old_upload = client.post(
        "/api/v1/training/upload",
        headers=h(users),
        files=[("files", ("notes.txt", b"text", "text/plain"))],
    )
    assert old_upload.status_code == 200, old_upload.text
    assert old_upload.json()["documents"][0]["url"] == old_upload.json()["urls"][0]
    assert (
        client.post(
            "/api/v1/documents/upload",
            headers=h(users),
            data={"title": "No"},
            files={"file": ("bad.exe", b"a", "application/pdf")},
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/v1/documents/upload",
            headers=h(users),
            data={"title": "No"},
            files={"file": ("big.pdf", b"a" * (4 * 1024 * 1024 + 1), "application/pdf")},
        ).status_code
        == 413
    )


def test_upload_uses_durable_blob_when_configured(library_data, monkeypatch):
    _, users, _, _ = library_data
    from app.services import document_storage

    calls = []

    async def put_blob(path, data, **kwargs):
        calls.append((path, data, kwargs))
        return SimpleNamespace(url="https://blob.example.com/training/file.pdf")

    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "test-token")
    monkeypatch.setattr(document_storage, "put_blob", put_blob)
    result = TestClient(app).post(
        "/api/v1/documents/upload",
        headers=h(users),
        data={"title": "Blob"},
        files={"file": ("file.pdf", b"pdf", "application/pdf")},
    )
    assert result.status_code == 201, result.text
    assert result.json()["url"] == "https://blob.example.com/training/file.pdf"
    assert calls[0][2]["access"] == "public"


def test_replace_uploaded_file_propagates_and_updates_metadata(library_data, monkeypatch):
    _, users, phases, _ = library_data
    from app.services import document_storage

    calls = []

    async def put_blob(path, data, **kwargs):
        calls.append(path)
        return SimpleNamespace(url="https://blob.example.com/replacement.md")

    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "test-token")
    monkeypatch.setattr(document_storage, "put_blob", put_blob)
    client = TestClient(app)
    document = create_doc(client, users, description="Old description", positions=["BACKEND"])
    content = create_content(
        client,
        users,
        phases[0],
        document_ids=[document["id"]],
        resource_url="https://example.com/legacy-page",
    )
    url = f"/api/v1/documents/{document['id']}/file"
    for role in ("MENTOR", "INTERN"):
        denied = client.put(
            url,
            headers=h(users, role),
            data={"title": "Denied"},
            files={"file": ("new.md", b"text", "text/markdown")},
        )
        assert denied.status_code == 403
    assert client.put(url, headers=h(users), data={"title": "Missing file"}).status_code == 422
    missing = client.put(
        f"/api/v1/documents/{uuid.uuid4()}/file",
        headers=h(users),
        data={"title": "Missing document"},
        files={"file": ("new.md", b"text", "text/markdown")},
    )
    assert missing.status_code == 404
    assert calls == []
    result = client.put(
        url,
        headers=h(users),
        data={"title": "Replacement", "positions": "[]", "description": ""},
        files={"file": ("new.md", b"text", "text/markdown")},
    )
    assert result.status_code == 200, result.text
    changed = result.json()
    assert changed["id"] == document["id"]
    assert changed["title"] == "Replacement"
    assert changed["format"] == "md"
    assert changed["positions"] == []
    assert changed["description"] is None
    assert changed["original_filename"] == "new.md"
    assert changed["size_bytes"] == 4
    assert changed["usage_count"] == 1
    resources = client.get(
        f"/api/v1/training/phases/{phases[0].id}/contents", headers=h(users)
    ).json()[0]
    assert resources["id"] == content["id"]
    assert resource_urls(resources["resource_url"]) == [
        "https://example.com/legacy-page",
        changed["url"],
    ]
    assert resources["documents"][0]["url"] == changed["url"]
    assert client.get("/api/v1/documents", headers=h(users)).json()["formats"] == ["md"]


def test_legacy_webpage_resources_stay_outside_file_catalog(library_data):
    db, users, phases, _ = library_data
    client = TestClient(app)
    webpage = "https://example.com/training-page"
    content = create_content(client, users, phases[0], type="LINK", resource_url=webpage)
    assert content["resource_url"] == webpage
    assert content["documents"] == []
    assert client.get("/api/v1/documents", headers=h(users)).json()["items"] == []
    with pytest.raises(IntegrityError) as invalid:
        with db.begin_nested():
            db.add(Document(title="Webpage", url=webpage, format="link", positions=[]))
            db.flush()
    assert invalid.value.orig.diag.constraint_name == "ck_documents_file_format"


def test_migration_indexes_legacy_resources_without_changing_content(library_data):
    db, _, phases, _ = library_data
    first_url = "https://example.com/legacy.pdf"
    second_url = "https://example.com/video.mp4"
    contents = [
        LearningContent(
            phase_id=phases[0].id,
            title="Legacy lesson",
            type="LESSON",
            order_no=1,
            resource_url=first_url,
        ),
        LearningContent(
            phase_id=phases[1].id,
            title="Legacy video",
            type="VIDEO",
            order_no=1,
            resource_url=json.dumps(
                [first_url, second_url, first_url, "https://example.com/webpage"]
            ),
        ),
    ]
    db.add_all(contents)
    db.commit()
    original = [content.resource_url for content in contents]
    migration = import_module("migrations.versions.0017_document_library")
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.downgrade()
        migration.upgrade()
        import_module("migrations.versions.0018_file_documents_only").upgrade()
    db.commit()
    db.expire_all()
    documents = list(db.scalars(select(Document)))
    assert len(documents) == 2
    assert all(document.positions == [] for document in documents)
    assert {document.format for document in documents} == {"pdf", "mp4"}
    assert db.scalar(text("SELECT count(*) FROM learning_content_documents")) == 3
    assert [db.get(LearningContent, content.id).resource_url for content in contents] == original


def test_independent_stale_sessions_do_not_restore_old_urls_or_lose_manual_edits():
    engine = get_engine()
    if "single_intern_test_" not in str(engine.url.query.get("options", "")):
        pytest.skip("Independent committed sessions require the disposable-schema runner")
    roadmap_id = document_id = None
    with (
        Session(engine, expire_on_commit=False) as first,
        Session(engine, expire_on_commit=False) as second,
    ):
        try:
            roadmap = Roadmap(name=f"Concurrent library {uuid.uuid4().hex}", status="ACTIVE")
            first.add(roadmap)
            first.flush()
            roadmap_id = roadmap.id
            phase = Phase(roadmap_id=roadmap.id, name="Phase", order_no=1)
            first.add(phase)
            first.commit()
            document = DocumentService.create(
                first, DocumentCreate(title="Guide", url="https://example.com/old.pdf")
            )
            document_id = document.id
            content = TrainingService.create_content(
                first,
                LearningContentCreate(
                    phase_id=phase.id,
                    title="Content",
                    type="DOCUMENT",
                    order_no=1,
                    document_ids=[document.id],
                    resource_url="https://example.com/manual",
                ),
            )
            assert content.documents[0].url.endswith("old.pdf")
            # A library editor commits while another session retains the old identities.
            replace_source(second, document.id, "https://example.com/new.pdf")
            TrainingService.update_content(
                first, content.id, LearningContentUpdate(document_ids=[document.id])
            )
            assert resource_urls(content.resource_url) == [
                "https://example.com/manual",
                "https://example.com/new.pdf",
            ]
            # Reverse direction: stale catalog editor must preserve a new manual URL.
            stale_content = second.get(LearningContent, content.id)
            assert "https://example.com/manual" in resource_urls(stale_content.resource_url)
            TrainingService.update_content(
                first,
                content.id,
                LearningContentUpdate(resource_url="https://example.com/manual-edited"),
            )
            replace_source(second, document.id, "https://example.com/final.pdf")
            first.expire_all()
            refreshed = first.get(LearningContent, content.id)
            assert resource_urls(refreshed.resource_url) == [
                "https://example.com/manual-edited",
                "https://example.com/final.pdf",
            ]
            # Both mutation paths use one transaction lock, excluding concurrent mergers.
            DocumentService.mutation_lock(first)
            assert second.scalar(text("SELECT pg_try_advisory_xact_lock(46124839678395)")) is False
            first.rollback()
            assert second.scalar(text("SELECT pg_try_advisory_xact_lock(46124839678395)")) is True
            second.rollback()
        finally:
            first.rollback()
            second.rollback()
            if roadmap_id:
                TrainingService.delete_roadmap(first, roadmap_id)
            if document_id:
                DocumentService.delete(first, document_id)
