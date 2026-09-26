import uuid
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import _sqlalchemy_url
from app.main import app
from app.models.enums import InternshipMemberStatus, InternshipStatus, UserRole, UserStatus
from app.schemas.internship import InternshipBase, InternshipMemberBase, InternshipRead
from app.schemas.user import UserCreate, UserRead


def test_all_20_entities_registered():
    """Verify the 20 business entities of the agreed MVP schema are registered."""
    expected_tables = {
        "nguoi_dung",
        "dot_thuc_tap",
        "thanh_vien_thuc_tap",
        "yeu_cau_thuc_tap",
        "lo_trinh_dao_tao",
        "giai_doan",
        "noi_dung_dao_tao",
        "tien_do_hoc_tap",
        "bai_kiem_tra",
        "cau_hoi",
        "lan_lam_bai",
        "cong_viec",
        "bai_nop_cong_viec",
        "binh_luan_cong_viec",
        "tieu_chi_danh_gia",
        "danh_gia",
        "thong_bao",
        "luot_doc_thong_bao",
        "hoi_thoai_ai",
        "tin_nhan_ai",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert len(actual_tables) == 20
    assert actual_tables == expected_tables


def test_core_enums_defined():
    """Verify the role and internship values defined for the MVP schema."""
    assert UserRole.INTERN == "INTERN"
    assert UserStatus.ACTIVE == "ACTIVE"
    assert InternshipStatus.OPEN == "OPEN"
    assert InternshipMemberStatus.EXTENDED == "EXTENDED"


def test_user_schemas():
    now = datetime.now(UTC)
    user_id = uuid.uuid4()
    user_create = UserCreate(
        email="intern@example.com",
        full_name="Nguyễn Văn A",
        role=UserRole.INTERN,
        password="secretpassword",
    )
    assert user_create.email == "intern@example.com"

    user_read = UserRead(
        id=user_id,
        email="intern@example.com",
        full_name="Nguyễn Văn A",
        role=UserRole.INTERN,
        status=UserStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    assert user_read.id == user_id


def test_internship_schemas_validation():
    now = datetime.now(UTC)
    mentor_id = uuid.uuid4()
    intern_id = uuid.uuid4()
    internship_id = uuid.uuid4()

    # Valid internship period
    internship = InternshipRead(
        id=internship_id,
        name="Internship 2026-Q1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        status=InternshipStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    assert internship.name == "Internship 2026-Q1"

    # Invalid period: end_date < start_date
    with pytest.raises(ValueError, match="end_date must not be before start_date"):
        InternshipBase(
            name="Invalid Period",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 4, 1),
        )

    member = InternshipMemberBase(
        intern_id=intern_id,
        internship_id=internship_id,
        mentor_id=mentor_id,
        status=InternshipMemberStatus.ACTIVE,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
    )
    assert member.status == InternshipMemberStatus.ACTIVE

    # Invalid internship: end_date < start_date
    with pytest.raises(ValueError, match="end_date must not be before start_date"):
        InternshipMemberBase(
            intern_id=intern_id,
            internship_id=internship_id,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 5, 1),
        )


def test_health_endpoints():
    client = TestClient(app)

    # Legacy probe
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "itms-backend"

    # Database connectivity probe
    resp_db = client.get("/api/v1/health/db")
    assert resp_db.status_code == 200
    db_data = resp_db.json()
    assert db_data["service"] == "itms-backend"
    assert "database" in db_data


def test_database_url_uses_psycopg_v3_for_generic_postgres_urls():
    assert _sqlalchemy_url("postgres://user:pass@example.com/itms") == (
        "postgresql+psycopg://user:pass@example.com/itms"
    )
    assert _sqlalchemy_url("postgresql://user:pass@example.com/itms") == (
        "postgresql+psycopg://user:pass@example.com/itms"
    )
