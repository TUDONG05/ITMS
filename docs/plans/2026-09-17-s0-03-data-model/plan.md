# S0-03 – Thiết kế mô hình dữ liệu và Schema nền tảng

## 1. Thông tin task

Project: Internship Management System (ITMS)

Task: S0-03 – Thiết kế mô hình dữ liệu và Schema nền tảng

Source of truth:

- `docs/requirements/ITMS-SRS.md`
- SRS version 1.0
- Đặc biệt các mục:
  - §5 Business Rules
  - §6.1 Logic dữ liệu và quan hệ
  - §6.2 Entity và field
  - §6.3 Relationships
  - §6.4 ERD logic

Tài liệu SRS:

`docs/requirements/ITMS-SRS.md`

---

## 2. Mục tiêu

Thiết kế mô hình dữ liệu và schema nền tảng cho ITMS theo SRS.

Kết quả phải xác định rõ:

- Entity
- Attribute/field chính
- Primary Key
- Foreign Key
- Relationship/cardinality
- Enum/status
- Unique constraint
- Check constraint
- Business constraint
- Index
- Data integrity
- Data access scope cho các dữ liệu có phân quyền

Mô hình phải đủ rõ để S0-04 có thể sử dụng làm cơ sở tạo:

S0-03
→ PostgreSQL schema
→ SQLAlchemy model
→ Alembic migration

---

## 3. Phạm vi

### Cần làm

1. Map entity từ SRS §6.1–§6.4.
2. Xác định PK/FK.
3. Xác định relationship/cardinality.
4. Xác định enum/status.
5. Xác định unique constraint.
6. Xác định check constraint.
7. Xác định business constraint.
8. Xác định index cho các query chính.
9. Kiểm tra data integrity.
10. Đối chiếu với Business Rules BR-01 → BR-12.
11. Xác định các điểm SRS chưa đủ rõ cần quyết định thiết kế.
12. Tạo tài liệu ERD/schema và entity-relationship mapping.

### Không làm

- Không tạo database.
- Không tạo PostgreSQL migration.
- Không tạo Alembic migration.
- Không seed dữ liệu.
- Không tạo DTO.
- Không triển khai API.
- Không triển khai authentication.
- Không triển khai RBAC code.
- Không triển khai LMS.
- Không triển khai Task API.
- Không triển khai Evaluation API.
- Không triển khai AI/RAG.
- Không tự ý thêm entity ngoài SRS nếu chưa review.

---

# 4. Quy ước dữ liệu

Theo SRS §6.1:

- PK sử dụng UUID.
- FK sử dụng hậu tố `_id`.
- Time sử dụng timestamp.
- status, role, priority sử dụng enum hoặc catalog tương đương.
- Tất cả FK phải được kiểm tra ở backend.
- Business rules phải được kiểm tra ở backend.
- UI chỉ ẩn button không đủ để đảm bảo permission.

Các quyết định kỹ thuật chưa được SRS quy định rõ phải được đánh dấu là:

"Proposed / Đề xuất"

và không được coi là yêu cầu bắt buộc của SRS.

---

# 5. Entity cần thiết kế

Theo SRS §6.2, mô hình gồm 27 entity:

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

Không tự ý thêm hoặc xóa entity.

---

# 6. Entity và PK/FK

## Users

PK:

- id

Các field chính:

- id
- email
- password_hash
- full_name
- role
- status
- created_at
- updated_at

Constraint:

- email UNIQUE
- email comparison không phân biệt hoa thường

---

## InternshipPeriods

PK:

- id

FK:

- created_by → Users.id

Các field chính:

- name
- start_date
- end_date
- status
- created_by
- created_at

Constraint:

- name UNIQUE
- end_date >= start_date

---

## Internships

PK:

- id

FK:

- intern_id → Users.id
- period_id → InternshipPeriods.id

Các field chính:

- intern_id
- period_id
- status
- start_date
- end_date
- note
- created_at
- updated_at

Constraint:

- intern_id phải tham chiếu User có role INTERN.
- end_date >= start_date.
- Một intern chỉ có tối đa một Internship ACTIVE trên toàn hệ thống.

---

## MentorAssignments

PK:

- id

FK:

- internship_id → Internships.id
- mentor_id → Users.id
- assigned_by → Users.id

Các field chính:

- assigned_at
- ended_at
- is_primary

Constraint:

- mentor_id phải tham chiếu User có role MENTOR.
- assigned_at <= ended_at nếu ended_at có giá trị.
- Mỗi internship chỉ có một primary mentor đang hoạt động.

---

## Roadmaps

PK:

- id

FK:

- period_id → InternshipPeriods.id
- created_by → Users.id

Các field chính:

- title
- description
- status
- created_at

Business rule:

- Chỉ roadmap PUBLISHED được áp dụng.

---

## RoadmapPhases

PK:

- id

FK:

- roadmap_id → Roadmaps.id

Các field chính:

- title
- sequence_no
- duration_days
- completion_rule

Constraint:

- UNIQUE(roadmap_id, sequence_no)
- duration_days > 0 nếu có giá trị

---

## Contents

PK:

- id

FK:

- phase_id → RoadmapPhases.id

Các field chính:

- title
- content_type
- content_body
- resource_url
- sequence_no
- is_required

Constraint:

- UNIQUE(phase_id, sequence_no)
- Nếu content_type = TEXT thì content_body phải có giá trị.

---

## Exams

PK:

- id

FK:

- phase_id → RoadmapPhases.id

Các field chính:

- title
- duration_minutes
- max_attempts
- passing_score
- open_at
- close_at

Constraint:

- duration_minutes > 0
- max_attempts > 0
- passing_score từ 0 đến 100
- close_at > open_at

---

## ExamAttempts

PK:

- id

FK:

- exam_id → Exams.id
- intern_id → Users.id

Các field chính:

- attempt_no
- score
- started_at
- submitted_at
- status

Constraint:

- UNIQUE(exam_id, intern_id, attempt_no)

---

## Questions

PK:

- id

Các field chính:

- content
- question_type
- difficulty
- correct_answer

---

## ExamQuestions

Khóa chính đề xuất:

- (exam_id, question_id)

FK:

- exam_id → Exams.id
- question_id → Questions.id

Các field:

- order_no
- points

Constraint:

- UNIQUE(exam_id, question_id)
- order_no duy nhất trong một exam

Ghi chú:

Việc sử dụng composite PK (exam_id, question_id) là thiết kế đề xuất
phù hợp với quan hệ N-N trong SRS.

---

## AttemptAnswers

PK:

- id

FK:

- attempt_id → ExamAttempts.id
- question_id → Questions.id

Các field:

- answer
- is_correct
- score

---

## Tasks

PK:

- id

FK:

- internship_id → Internships.id
- mentor_id → Users.id

Các field:

- title
- description
- priority
- deadline
- status
- created_at
- updated_at

Constraint/business rule:

- mentor_id phải là mentor được phân công phù hợp với internship.
- Intern không được tự chuyển task sang COMPLETED.
- Mentor xác nhận hoàn thành.

---

## TaskSubmissions

PK:

- id

FK:

- task_id → Tasks.id

Các field:

- content
- link
- attachment_url
- version_no
- submitted_at
- reviewed_at
- review_comment

Constraint:

- UNIQUE(task_id, version_no)
- Ít nhất một trong content/link/attachment_url phải có giá trị.

---

## TaskComments

PK:

- id

FK:

- task_id → Tasks.id
- author_id → Users.id

Các field:

- content
- created_at

---

## TaskStatusHistory

PK:

- id

FK:

- task_id → Tasks.id
- changed_by → Users.id

Các field:

- old_status
- new_status
- changed_at

---

## Evaluations

PK:

- id

FK:

- internship_id → Internships.id
- evaluator_id → Users.id

Các field:

- evaluation_type
- score
- comment
- status
- published_at

Constraint:

- score từ 0 đến 100.
- Nếu status = PUBLISHED thì published_at phải có.

Business rule:

- DRAFT chỉ Mentor/Admin thấy.
- PUBLISHED mới hiển thị cho Intern.

---

## Notifications

PK:

- id

FK:

- recipient_id → Users.id

Các field:

- type
- title
- content
- reference_type
- reference_id
- is_read
- read_at
- created_at

---

## LifecycleRequests

PK:

- id

FK:

- internship_id → Internships.id

Các field:

- request_type
- reason
- status

Business rule:

- Không có đồng thời nhiều lifecycle request đang chờ cho cùng internship.

---

## LifecycleApprovals

PK:

- id

FK:

- request_id → LifecycleRequests.id
- approver_id → Users.id

Các field:

- decision
- decided_at

---

## Feedback

PK:

- id

FK:

- sender_id → Users.id

Các field:

- content
- status
- response

Các giá trị status chưa được SRS quy định đầy đủ phải được đánh dấu
là Proposed.

---

## AuditLogs

PK:

- id

FK:

- actor_id → Users.id

Các field:

- action
- entity_type
- entity_id
- created_at
- metadata

Mục đích:

- Audit trace.
- Có thể lưu before/after trong metadata.

---

## Documents

PK:

- id

FK:

- uploaded_by → Users.id

Các field:

- title
- source_url
- file_type
- access_scope
- version
- status
- created_at
- activated_at

Business rule:

- Access scope phải được kiểm tra trước khi truy xuất dữ liệu.
- Phục vụ AI/RAG.

---

## DocumentChunks

PK:

- id

FK:

- document_id → Documents.id

Các field:

- chunk_no
- text
- vector
- metadata
- access_scope

Constraint:

- chunk_no duy nhất trong từng document.

Business rule:

- Chunk phải tuân thủ access scope của tài liệu/người hỏi.

---

## LearningProgress

PK:

- id

FK:

- intern_id → Users.id
- content_id → Contents.id

Các field:

- status
- completed_at

Constraint:

- UNIQUE(intern_id, content_id)

---

## Conversations

PK:

- id

FK:

- user_id → Users.id

Các field:

- title
- created_at

---

## ChatMessages

PK:

- id

FK:

- conversation_id → Conversations.id

Các field:

- sender_type
- content
- citations
- created_at

Business rule:

- AI conversation phải kiểm tra permission trước khi trả lời.
- Nếu không có evidence thì không được đoán.
- Câu trả lời RAG phải có source/citation.

---

# 7. Enum / Status

Các enum chính:

## UserRole

- INTERN
- MENTOR
- MANAGER
- ADMIN

## UserStatus

- ACTIVE
- INACTIVE
- LOCKED

## InternshipPeriodStatus

- PLANNED
- ACTIVE
- CLOSED
- CANCELLED

## InternshipStatus

- PLANNED
- ACTIVE
- EXTENDED
- COMPLETED
- TERMINATED

## RoadmapStatus

- DRAFT
- PUBLISHED
- ARCHIVED

## ContentType

- TEXT
- LINK
- FILE
- VIDEO

## ExamAttemptStatus

- IN_PROGRESS
- SUBMITTED
- GRADED
- EXPIRED

## TaskPriority

- LOW
- MEDIUM
- HIGH
- URGENT

## TaskStatus

- ASSIGNED
- PENDING_REVIEW
- REVISION_REQUIRED
- COMPLETED
- CANCELLED

## EvaluationType

- PERIODIC
- FINAL

## EvaluationStatus

- DRAFT
- PUBLISHED

## DocumentStatus

- PENDING
- INDEXED
- FAILED
- ARCHIVED

Các enum khác nếu cần phải được đối chiếu trực tiếp với SRS và đánh dấu
Proposed nếu SRS chưa quy định giá trị cụ thể.

---

# 8. Relationship / Cardinality

Các relationship chính:

- Users 1-N Internships
- InternshipPeriods 1-N Internships
- Internships 1-N MentorAssignments
- Users(Mentor) 1-N MentorAssignments
- InternshipPeriods 1-N Roadmaps
- Roadmaps 1-N RoadmapPhases
- RoadmapPhases 1-N Contents
- RoadmapPhases 1-N Exams
- Exams 1-N ExamAttempts
- Exams N-N Questions thông qua ExamQuestions
- ExamAttempts 1-N AttemptAnswers
- Internships 1-N Tasks
- Tasks 1-N TaskSubmissions
- Tasks 1-N TaskComments
- Tasks 1-N TaskStatusHistory
- Internships 1-N Evaluations
- Users 1-N Evaluations
- Users 1-N Notifications
- Users(Admin) 1-N Documents
- Documents 1-N DocumentChunks
- Users N-N Contents thông qua LearningProgress
- Internships 1-N LifecycleRequests
- LifecycleRequests 1-N LifecycleApprovals
- Users 1-N Feedback
- Users 1-N AuditLogs
- Users 1-N Conversations
- Conversations 1-N ChatMessages

---

# 9. Business Rules Mapping

Phải kiểm tra mô hình dữ liệu có hỗ trợ:

## BR-01

Một Intern chỉ có một primary Mentor tại một thời điểm trong internship.

Liên quan:

- Internships
- MentorAssignments

---

## BR-02

Chỉ Mentor được phân công mới được tạo/sửa/review task và evaluation
của intern.

Liên quan:

- MentorAssignments
- Tasks
- Evaluations

Permission phải được backend kiểm tra.

---

## BR-03

Intern không được tự chuyển task sang COMPLETED.

Liên quan:

- Tasks
- TaskStatusHistory

---

## BR-04

Task status:

- ASSIGNED
- PENDING_REVIEW
- REVISION_REQUIRED
- COMPLETED
- CANCELLED

---

## BR-05

Late submission có thể được phép nhưng phải được đánh dấu late.

S0-03 cần xác định field/schema cần thiết hoặc ghi rõ đây là logic
backend nếu chưa có field trong SRS.

Không tự ý thêm field nếu chưa review.

---

## BR-06

Evaluation:

- DRAFT → chỉ Mentor/Admin.
- PUBLISHED → Intern có thể xem.

---

## BR-07

LOCKED account:

- Không login.
- Không tạo action mới.

---

## BR-08

Danh sách/dashboard phải được filter theo permission.

---

## BR-09

Exam attempt phải tuân thủ:

- open window
- duration
- max attempts

---

## BR-10

Không có đồng thời nhiều lifecycle-extension request pending cho cùng
internship.

---

## BR-11

AI chỉ truy xuất:

- documents
- business data

trong permission scope của người hỏi.

---

## BR-12

RAG:

- Phải có source/citation.
- Không có evidence thì không đoán.

---

# 10. Constraint Design

Cần xác định rõ:

- PK
- FK
- UNIQUE
- CHECK
- Partial UNIQUE nếu PostgreSQL được chọn
- Relationship constraints
- Business constraints

Các constraint phải được phân loại:

### Database-level constraint

Ví dụ:

- PK
- FK
- UNIQUE
- CHECK

### Backend-level business rule

Ví dụ:

- User role phải phù hợp với FK business role.
- Mentor phải là mentor được assign.
- Intern không được complete task.
- Permission của Evaluation.
- Lifecycle pending.
- RAG access scope.

Không giả định rằng database constraint có thể thay thế toàn bộ
business authorization.

---

# 11. Index Design

Index phải được xác định dựa trên query chính.

## Users

- UNIQUE(email)

Query:

- login / lookup user by email.

## Internships

- intern_id
- period_id
- status
- partial UNIQUE(intern_id) WHERE status = ACTIVE

Query:

- internship của intern.
- internship theo period.
- filter status.
- đảm bảo một ACTIVE internship.

## MentorAssignments

- internship_id
- mentor_id
- partial UNIQUE(internship_id)
  WHERE is_primary = true AND ended_at IS NULL

Query:

- tìm mentor của internship.
- tìm internship của mentor.
- đảm bảo primary mentor duy nhất.

## Roadmaps

- period_id

## RoadmapPhases

- UNIQUE(roadmap_id, sequence_no)

## Contents

- UNIQUE(phase_id, sequence_no)

## Exams

- phase_id

## ExamAttempts

- exam_id
- intern_id
- UNIQUE(exam_id, intern_id, attempt_no)

## Tasks

- internship_id
- mentor_id
- status
- deadline

Query:

- task của internship.
- task của mentor.
- filter task status.
- task theo deadline.

## TaskSubmissions

- task_id
- UNIQUE(task_id, version_no)

## Evaluations

- internship_id
- evaluator_id

## Notifications

- recipient_id
- is_read

Query:

- notification của user.
- notification chưa đọc.

## Documents

- uploaded_by
- status

## DocumentChunks

- document_id

Vector index:

- Chưa chốt trong S0-03.
- Sẽ được xác định khi triển khai RAG/vector store.

## LearningProgress

- UNIQUE(intern_id, content_id)

## TaskComments

- task_id

## TaskStatusHistory

- task_id

## LifecycleRequests

- internship_id
- status

## LifecycleApprovals

- request_id
- approver_id

## Feedback

- sender_id
- status

## AuditLogs

- actor_id
- entity_type
- entity_id

## Conversations

- user_id

## ChatMessages

- conversation_id

---

# 12. ERD

S0-03 phải có ERD thể hiện:

- 27 entity.
- PK.
- FK.
- Relationship.
- Cardinality.
- Các bảng trung gian N-N.

ERD có thể được tạo bằng Mermaid, draw.io, dbdiagram hoặc công cụ
phù hợp với repository.

Không cần tạo migration từ ERD ở S0-03.

---

# 13. Các quyết định thiết kế cần review

Những nội dung SRS chưa quy định hoàn toàn phải được đánh dấu
"Proposed" và review trước khi S0-04.

Các điểm cần review:

1. PostgreSQL hay database khác.
2. UUID generation strategy.
3. timestamp/timestamptz.
4. access_scope lưu enum hay JSON/JSONB.
5. metadata/citations lưu JSON/JSONB.
6. ChatMessage.sender_type values.
7. Feedback.status values.
8. LifecycleApproval.decision values.
9. Questions.question_type values.
10. Questions.difficulty values.
11. ON DELETE behavior.
12. Late submission có cần field riêng hay xử lý bằng deadline/submitted_at.
13. Vector storage/index strategy cho DocumentChunks.
14. reference_id type.

Không tự ý biến các đề xuất này thành requirement của SRS.

---

# 14. Data Integrity Review

Review tối thiểu:

- Tất cả FK tham chiếu đúng PK.
- Không có FK tới entity không tồn tại.
- Relationship không mâu thuẫn.
- N-N có bảng trung gian.
- Unique constraint phù hợp.
- Check constraint phù hợp.
- Enum không mâu thuẫn với business rule.
- Index hỗ trợ query chính.
- Không tạo duplicate active primary mentor.
- Không tạo duplicate active internship.
- Không vi phạm learning progress uniqueness.
- Không vi phạm task submission version uniqueness.
- Không vi phạm exam attempt numbering.

---

# 15. Boundary với S0-04

## S0-03

Thiết kế:

- Entity
- Fields
- PK
- FK
- Relationship
- Cardinality
- Enum
- Constraint
- Index
- Business Rule mapping
- ERD
- Data integrity

## S0-04

Triển khai:

S0-03
→ PostgreSQL
→ SQLAlchemy Model
→ Alembic Migration
→ Upgrade
→ Rollback
→ DTO/API Contract

S0-03 không tạo migration và không seed dữ liệu.

---

# 16. Expected Deliverables

S0-03 phải bàn giao:

1. ERD/schema.
2. Tài liệu mapping Entity → Relationship theo SRS.
3. Danh sách PK/FK.
4. Danh sách enum/status.
5. Danh sách unique/check/business constraint.
6. Danh sách index.
7. Lý do của các index theo query chính.
8. Mapping BR-01 → BR-12.
9. Data integrity review.
10. Danh sách các điểm Proposed cần review.
11. Tài liệu/báo cáo review xác nhận mô hình đáp ứng business rules.
12. Link PR hoặc tài liệu để S0-04 sử dụng làm nguồn tạo migration.

---

# 17. Acceptance Criteria

S0-03 hoàn thành khi:

- Đủ 27 entity theo SRS.
- PK/FK được xác định.
- Relationship/cardinality được xác định.
- Enum/status được xác định.
- Unique constraint được xác định.
- Check/business constraint được xác định.
- Index được xác định và có lý do.
- BR-01 → BR-12 được đối chiếu.
- ERD thể hiện đúng mô hình.
- Các điểm chưa rõ được đánh dấu Proposed.
- Không tạo migration.
- Không seed.
- Không tạo DTO/API implementation.
- Tài liệu đủ rõ để S0-04 tạo migration.

---

# 18. Quy trình thực hiện

1. Đọc SRS.
2. Map 27 entity.
3. Map field.
4. Xác định PK/FK.
5. Xác định relationship.
6. Xác định enum/status.
7. Xác định constraint.
8. Xác định index.
9. Map BR-01 → BR-12.
10. Xác định các điểm Proposed.
11. Tạo ERD.
12. Review data integrity.
13. Review với team.
14. Chốt S0-03.
15. Bàn giao cho S0-04.

---

# 19. Yêu cầu đối với AI Coding Agent

Trước khi thực hiện:

- Đọc CONTRIBUTING.md.
- Đọc README.md.
- Đọc SRS.
- Đọc architecture/data-flow hiện có.
- Đọc toàn bộ tài liệu liên quan trong docs/plans.

Không được:

- tự ý thêm entity.
- tự ý xóa entity.
- tự ý đổi field.
- tự ý đổi PK/FK.
- tự ý đổi relationship.
- tự ý đổi enum.
- tự ý bỏ constraint.
- tự ý thêm migration.
- tự ý tạo database.
- tự ý seed.
- tự ý tạo API.

Nếu SRS và repository có mâu thuẫn:

1. Không tự ý quyết định.
2. Ghi rõ conflict.
3. Đề xuất phương án.
4. Chờ review.

Giai đoạn đầu chỉ phân tích và lập plan.
Không code implementation cho S0-04.

---

# 20. Handover cho S0-04

Sau khi S0-03 được review và chốt:

S0-04 được phép sử dụng:

- ERD.
- Entity mapping.
- PK/FK.
- Enum.
- Constraint.
- Index.
- Business rule mapping.

để triển khai:

- PostgreSQL schema.
- SQLAlchemy model.
- Alembic migration.
- Rollback.
- DTO/API contract nền tảng.