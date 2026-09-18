# S0-04 – Migration và DTO/API nền tảng

## 1. Mục tiêu

Database PostgreSQL chạy được từ database trống và các module có
contract API/DTO nền tảng nhất quán với schema S0-03.

S0-04 sử dụng S0-03 làm nguồn chuẩn cho data model.

Không được tự ý thay đổi entity, relationship, PK/FK, enum hoặc business
constraint của S0-03 nếu chưa được xác nhận.

---

## 2. Phạm vi

### Cần làm

1. Cấu hình PostgreSQL cho Backend.
2. Cấu hình SQLAlchemy.
3. Cấu hình Alembic.
4. Tạo entity/model theo schema S0-03.
5. Tạo migration PostgreSQL.
6. Kiểm tra migration trên database trống.
7. Kiểm tra rollback migration.
8. Kiểm tra migrate lại sau rollback.
9. Kiểm tra Backend kết nối PostgreSQL.
10. Tạo DTO/API contract nền tảng sau khi migration ổn định.

### Không làm

- Không seed dữ liệu.
- Không tạo Postman collection.
- Không triển khai toàn bộ API nghiệp vụ của các module tương lai.
- Không tự ý thay đổi schema S0-03.
- Không triển khai đầy đủ Authentication/RBAC/LMS/Task/RAG nếu chưa thuộc
  phạm vi S0-04.

---

## 3. Công nghệ

Backend:

- Python 3.13
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- psycopg

Project sử dụng `uv` để quản lý dependency.

---

## 4. Cấu trúc Backend hiện tại

backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── health.py
│   │       ├── router.py
│   │       └── __init__.py
│   ├── core/
│   │   ├── settings.py
│   │   └── __init__.py
│   └── __init__.py
├── tests/
│   └── test_health.py
├── pyproject.toml
└── uv.lock

---

## 5. Data model source of truth

S0-04 phải triển khai theo tài liệu S0-03.

S0-03 gồm 27 entity:

1. Users
2. InternshipPeriods
3. Internships
4. MentorAssignments
5. Roadmaps
6. RoadmapPhases
7. Contents
8. Exams
9. ExamAttempts
10. Questions
11. ExamQuestions
12. AttemptAnswers
13. Tasks
14. TaskSubmissions
15. TaskComments
16. TaskStatusHistory
17. Evaluations
18. Notifications
19. LifecycleRequests
20. LifecycleApprovals
21. Feedback
22. AuditLogs
23. Documents
24. DocumentChunks
25. LearningProgress
26. Conversations
27. ChatMessages

---

## 6. Nguyên tắc schema

- Tất cả PK sử dụng UUID.
- FK sử dụng hậu tố `_id`.
- Foreign key phải tham chiếu đúng entity tương ứng.
- Enum/status phải nhất quán với S0-03.
- Các unique constraint và business constraint của S0-03 phải được giữ.
- Các index đã xác định trong S0-03 phải được tạo trong migration.
- Không tự ý thêm field nghiệp vụ mới.
- Không tự ý xóa field nghiệp vụ.
- Không tự ý đổi tên field.
- Không tự ý đổi relationship.

---

## 7. Enum / Status

### UserRole

INTERN
MENTOR
MANAGER
ADMIN

### UserStatus

ACTIVE
INACTIVE
LOCKED

### InternshipPeriodStatus

PLANNED
ACTIVE
CLOSED
CANCELLED

### InternshipStatus

PLANNED
ACTIVE
EXTENDED
COMPLETED
TERMINATED

### RoadmapStatus

DRAFT
PUBLISHED
ARCHIVED

### ContentType

TEXT
LINK
FILE
VIDEO

### ExamAttemptStatus

IN_PROGRESS
SUBMITTED
GRADED
EXPIRED

### TaskPriority

LOW
MEDIUM
HIGH
URGENT

### TaskStatus

ASSIGNED
PENDING_REVIEW
REVISION_REQUIRED
COMPLETED
CANCELLED

### EvaluationType

PERIODIC
FINAL

### EvaluationStatus

DRAFT
PUBLISHED

### DocumentStatus

PENDING
INDEXED
FAILED
ARCHIVED

---

## 8. Các constraint quan trọng

### Users

- email UNIQUE.
- Email comparison không phân biệt hoa thường.

### InternshipPeriods

- end_date >= start_date.

### Internships

- end_date >= start_date.
- intern_id phải tham chiếu User có role INTERN.
- Một intern chỉ có tối đa một Internship ACTIVE.

### MentorAssignments

- mentor_id phải tham chiếu User có role MENTOR.
- assigned_at <= ended_at nếu ended_at có giá trị.
- Một internship chỉ có một primary mentor đang hoạt động.

### RoadmapPhases

- UNIQUE(roadmap_id, sequence_no).
- duration_days > 0 nếu có giá trị.

### Contents

- UNIQUE(phase_id, sequence_no).
- Nếu content_type = TEXT thì content_body phải có giá trị.

### Exams

- duration_minutes > 0.
- max_attempts > 0.
- passing_score từ 0 đến 100.
- close_at > open_at.

### ExamAttempts

- UNIQUE(exam_id, intern_id, attempt_no).

### ExamQuestions

- UNIQUE(exam_id, question_id).
- order_no duy nhất trong một exam.

### TaskSubmissions

- UNIQUE(task_id, version_no).
- Ít nhất một trong content/link/attachment_url phải có giá trị.

### Evaluations

- score từ 0 đến 100.
- Nếu status = PUBLISHED thì published_at phải có.

### LearningProgress

- UNIQUE(intern_id, content_id).

### LifecycleRequests

- Không có đồng thời nhiều request pending cho cùng internship.

---

## 9. Index

Tạo các index theo S0-03.

Các index chính:

- Users: UNIQUE(email)
- Internships: intern_id, period_id, status
- Internships: partial UNIQUE intern_id WHERE status = ACTIVE
- MentorAssignments: internship_id, mentor_id
- MentorAssignments: partial UNIQUE internship_id WHERE is_primary = true AND ended_at IS NULL
- Roadmaps: period_id
- RoadmapPhases: UNIQUE(roadmap_id, sequence_no)
- Contents: UNIQUE(phase_id, sequence_no)
- Exams: phase_id
- ExamAttempts: exam_id, intern_id
- ExamAttempts: UNIQUE(exam_id, intern_id, attempt_no)
- Tasks: internship_id, mentor_id, status, deadline
- TaskSubmissions: task_id
- TaskSubmissions: UNIQUE(task_id, version_no)
- Evaluations: internship_id, evaluator_id
- Notifications: recipient_id, is_read
- Documents: uploaded_by, status
- DocumentChunks: document_id
- LearningProgress: UNIQUE(intern_id, content_id)
- TaskComments: task_id
- TaskStatusHistory: task_id
- LifecycleRequests: internship_id, status
- LifecycleApprovals: request_id, approver_id
- Feedback: sender_id, status
- AuditLogs: actor_id, entity_type, entity_id
- Conversations: user_id
- ChatMessages: conversation_id

---

## 10. Migration requirements

Migration phải:

1. Chạy được từ PostgreSQL database trống.
2. Tạo đầy đủ schema theo S0-03.
3. Tạo enum.
4. Tạo table.
5. Tạo PK/FK.
6. Tạo unique constraint.
7. Tạo check constraint phù hợp.
8. Tạo index.
9. Có downgrade/rollback.
10. Sau rollback có thể upgrade lại thành công.

Không seed dữ liệu.

---

## 11. Kiểm tra migration

Phải kiểm tra:

### Upgrade

alembic upgrade head

Kết quả mong muốn:

- Migration thành công.
- Database chứa đúng các table.
- PK/FK/constraint/index được tạo.

### Rollback

alembic downgrade -1

Kết quả mong muốn:

- Migration được rollback thành công.

### Upgrade lại

alembic upgrade head

Kết quả mong muốn:

- Database được tạo lại thành công.

---

## 12. DTO/API nền tảng

Chỉ tạo DTO/API contract nền tảng sau khi migration ổn định.

DTO phải nhất quán với SQLAlchemy model và database schema.

Không triển khai đầy đủ business API.

Có thể bắt đầu với các contract nền tảng phục vụ kiểm tra:

- Health
- Database connectivity
- User model/schema cơ bản
- InternshipPeriod model/schema cơ bản
- Internship model/schema cơ bản

API public prefix:

/api/v1

Backend phải là nơi kiểm tra permission/business rules.

---

## 13. Database configuration

DATABASE_URL phải được cấu hình thông qua environment/local config.

Không commit:

- password
- secret
- token
- private key
- local credentials

Không hard-code database password trong source code.

---

## 14. Testing

Phải có kiểm tra tối thiểu:

- Backend kết nối PostgreSQL.
- Migration upgrade.
- Migration downgrade.
- Migration upgrade lại.
- Model import thành công.
- DTO/schema import thành công.
- Existing health endpoint không bị phá vỡ.

---

## 15. Acceptance Criteria

S0-04 được xem là hoàn thành khi:

- PostgreSQL connection hoạt động.
- Database có thể tạo từ database trống bằng migration.
- Migration upgrade hoạt động.
- Migration rollback hoạt động.
- Upgrade lại sau rollback hoạt động.
- Schema nhất quán với S0-03.
- Entity/model nhất quán với schema.
- DTO/API contract nền tảng nhất quán với model/schema.
- Không có seed.
- Không có secret được commit.
- Existing `/api/v1/health` vẫn hoạt động.

---

## 16. Boundary với S0-03

S0-03:

Data Model
→ Entity
→ Relationship
→ PK/FK
→ Enum
→ Constraint
→ Index
→ Business Rules

S0-04:

S0-03
→ SQLAlchemy Model
→ PostgreSQL
→ Alembic Migration
→ Rollback
→ DTO/API Contract

Không tự thiết kế lại data model trong S0-04.

---

## 17. Expected deliverables

- SQLAlchemy models.
- Alembic configuration.
- Initial migration.
- Database configuration.
- DTO/schema nền tảng.
- API contract nền tảng.
- Test migration/rollback.
- Test PostgreSQL connection.
- Documentation cập nhật cách chạy migration.

Không bao gồm seed và Postman collection.