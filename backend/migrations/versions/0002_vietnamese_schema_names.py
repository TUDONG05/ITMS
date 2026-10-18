"""Rename ITMS business tables and columns to Vietnamese identifiers.

Revision ID: 0002_vietnamese_schema_names
Revises: 0001_initial_schema
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_vietnamese_schema_names"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAMES = {
    "users": "nguoi_dung",
    "internships": "dot_thuc_tap",
    "internship_members": "thanh_vien_thuc_tap",
    "internship_requests": "yeu_cau_thuc_tap",
    "roadmaps": "lo_trinh_dao_tao",
    "phases": "giai_doan",
    "learning_contents": "noi_dung_dao_tao",
    "learning_progress": "tien_do_hoc_tap",
    "quizzes": "bai_kiem_tra",
    "questions": "cau_hoi",
    "quiz_attempts": "lan_lam_bai",
    "tasks": "cong_viec",
    "task_submissions": "bai_nop_cong_viec",
    "task_comments": "binh_luan_cong_viec",
    "evaluation_criteria": "tieu_chi_danh_gia",
    "evaluations": "danh_gia",
    "notifications": "thong_bao",
    "notification_reads": "luot_doc_thong_bao",
    "ai_conversations": "hoi_thoai_ai",
    "ai_messages": "tin_nhan_ai",
}

COLUMN_NAMES = {
    "users": {"full_name": "ho_ten", "phone": "so_dien_thoai", "role": "vai_tro"},
    "internships": {
        "name": "ten",
        "description": "mo_ta",
        "start_date": "ngay_bat_dau",
        "end_date": "ngay_ket_thuc",
        "created_by": "nguoi_tao_id",
    },
    "roadmaps": {"name": "ten", "description": "mo_ta", "created_by": "nguoi_tao_id"},
    "phases": {
        "roadmap_id": "lo_trinh_id",
        "name": "ten",
        "description": "mo_ta",
        "order_no": "thu_tu",
    },
    "learning_contents": {
        "phase_id": "giai_doan_id",
        "title": "tieu_de",
        "description": "mo_ta",
        "type": "loai",
        "content": "noi_dung",
        "order_no": "thu_tu",
    },
    "internship_members": {
        "internship_id": "dot_thuc_tap_id",
        "intern_id": "thuc_tap_sinh_id",
        "mentor_id": "nguoi_huong_dan_id",
        "roadmap_id": "lo_trinh_id",
        "start_date": "ngay_bat_dau",
        "end_date": "ngay_ket_thuc",
    },
    "internship_requests": {
        "internship_member_id": "thanh_vien_id",
        "requested_by": "nguoi_yeu_cau_id",
        "type": "loai",
        "reason": "ly_do",
        "requested_end_date": "ngay_ket_thuc_de_xuat",
        "reviewed_by": "nguoi_duyet_id",
        "review_note": "ghi_chu_duyet",
    },
    "learning_progress": {
        "internship_member_id": "thanh_vien_id",
        "content_id": "noi_dung_id",
        "progress_percent": "phan_tram_tien_do",
    },
    "quizzes": {
        "phase_id": "giai_doan_id",
        "title": "tieu_de",
        "description": "mo_ta",
        "duration_minutes": "thoi_luong_phut",
        "pass_score": "diem_dat",
        "max_attempts": "so_lan_lam_toi_da",
    },
    "questions": {
        "quiz_id": "bai_kiem_tra_id",
        "content": "noi_dung",
        "type": "loai",
        "options": "lua_chon",
        "correct_answer": "dap_an_dung",
        "score": "diem",
        "order_no": "thu_tu",
    },
    "quiz_attempts": {
        "quiz_id": "bai_kiem_tra_id",
        "internship_member_id": "thanh_vien_id",
        "attempt_no": "lan_lam",
        "answers": "cau_tra_loi",
        "score": "diem",
        "passed": "dat",
    },
    "tasks": {
        "internship_member_id": "thanh_vien_id",
        "created_by": "nguoi_tao_id",
        "title": "tieu_de",
        "description": "mo_ta",
        "priority": "uu_tien",
    },
    "task_submissions": {
        "task_id": "cong_viec_id",
        "content": "noi_dung",
        "review_comment": "nhan_xet",
        "reviewed_by": "nguoi_duyet_id",
    },
    "task_comments": {"task_id": "cong_viec_id", "user_id": "nguoi_dung_id", "content": "noi_dung"},
    "evaluation_criteria": {
        "name": "ten",
        "description": "mo_ta",
        "max_score": "diem_toi_da",
        "weight": "trong_so",
    },
    "evaluations": {
        "internship_member_id": "thanh_vien_id",
        "mentor_id": "nguoi_huong_dan_id",
        "evaluation_type": "loai_danh_gia",
        "criteria_scores": "diem_tieu_chi",
        "total_score": "tong_diem",
        "comment": "nhan_xet",
    },
    "notifications": {
        "title": "tieu_de",
        "content": "noi_dung",
        "target_type": "doi_tuong_nhan",
        "target_data": "du_lieu_nguoi_nhan",
        "created_by": "nguoi_tao_id",
    },
    "notification_reads": {"notification_id": "thong_bao_id", "user_id": "nguoi_dung_id"},
    "ai_conversations": {"user_id": "nguoi_dung_id", "title": "tieu_de"},
    "ai_messages": {
        "conversation_id": "hoi_thoai_id",
        "content": "noi_dung",
        "citations": "trich_dan",
    },
}


def upgrade() -> None:
    for old_name, new_name in TABLE_NAMES.items():
        op.rename_table(old_name, new_name)
    for old_table, columns in COLUMN_NAMES.items():
        table_name = TABLE_NAMES[old_table]
        for old_name, new_name in columns.items():
            op.alter_column(table_name, old_name, new_column_name=new_name)


def downgrade() -> None:
    for old_table, columns in reversed(tuple(COLUMN_NAMES.items())):
        table_name = TABLE_NAMES[old_table]
        for old_name, new_name in reversed(tuple(columns.items())):
            op.alter_column(table_name, new_name, new_column_name=old_name)
    for old_name, new_name in reversed(tuple(TABLE_NAMES.items())):
        op.rename_table(new_name, old_name)
