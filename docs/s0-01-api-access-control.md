# S0-01 — Quy ước API và lớp kiểm soát quyền

| Thuộc tính | Giá trị |
|---|---|
| Trạng thái | Đã chốt cho S0-01 |
| Phạm vi áp dụng | Web Client, Backend API, M01–M07 |
| Nguồn yêu cầu | `ITMS-SRS.md` mục 2.1, 3.1–3.2, 4.1–4.7, 5, 6, 7.2, 8 và 9 |
| Quyết định bổ sung | `ADMIN` kế thừa quyền nghiệp vụ của `MANAGER`; `MANAGER` xem toàn bộ các đợt trong bản demo |

## 1. Mục tiêu

Tài liệu này thống nhất ranh giới API và cách kiểm soát quyền để các module triển khai cùng một nguyên tắc:

- Web Client chỉ điều khiển trải nghiệm; Backend là nơi quyết định quyền.
- Mọi request vào M01–M07 đều qua cùng lớp xác thực và RBAC.
- Quyền truy cập gồm cả permission theo vai trò và phạm vi dữ liệu theo quan hệ nghiệp vụ.
- Module đích vẫn kiểm tra ownership, assignment, trạng thái và quy tắc nghiệp vụ.
- M07 chỉ tra cứu dữ liệu bằng cùng policy của người hỏi và không có quyền mutation nhạy cảm.

## 2. Phạm vi và ngoài phạm vi

### Trong phạm vi S0-01

- Base path, namespace module và quy ước request/response chung.
- Mô hình access token, refresh session và thu hồi phiên.
- Permission naming, ma trận quyền và quy tắc data scope.
- Thứ tự thực thi lớp kiểm soát quyền.
- Hợp đồng truy vấn nội bộ read-only cho M07.
- Error semantics, audit và các tình huống kiểm thử bắt buộc.

### Ngoài phạm vi

- Danh sách endpoint, method và DTO đầy đủ: chốt tại S0-04 sau migration.
- Code dependency/guard/repository cụ thể: triển khai tại S0-10.
- API Gateway, auth server hoặc microservice riêng cho từng module.
- Policy engine động như OPA/Casbin trong phiên bản demo.

## 3. Quy ước API chung

### 3.1 Giao thức và định dạng

| Quy ước | Quyết định |
|---|---|
| Public base path | `/api/v1` |
| Giao thức | REST/JSON; HTTPS khi triển khai |
| Tên JSON | `snake_case` |
| Định danh | UUID biểu diễn bằng chuỗi |
| Thời gian | ISO 8601/RFC 3339, lưu và trả theo UTC |
| Xác thực | `Authorization: Bearer <access_token>` |
| Correlation | Mỗi request có `request_id`; server sinh nếu client không gửi |
| Content type | `application/json`; upload dùng cơ chế riêng của endpoint file |

Tên resource dùng danh từ số nhiều và kebab-case. Hành động nghiệp vụ ưu tiên sub-resource thay vì động từ tùy ý, ví dụ:

```text
POST /api/v1/tasks/{task_id}/submissions
POST /api/v1/tasks/{task_id}/reviews
POST /api/v1/internships/{internship_id}/lifecycle-requests
```

### 3.2 Namespace theo module

Bảng này chỉ chốt ownership và prefix, chưa phải danh sách endpoint hoàn chỉnh.

| Module | Namespace dự kiến | Ownership |
|---|---|---|
| M01 | `/auth`, `/me`, `/users` | Đăng nhập, phiên, hồ sơ, tài khoản và vai trò |
| M02 | `/internship-periods`, `/internships`, `/mentor-assignments` | Đợt, quá trình thực tập và phân mentor |
| M03 | `/roadmaps`, `/learning-contents`, `/questions`, `/exams` | LMS, tiến độ và bài kiểm tra |
| M04 | `/tasks`; submission/comment là resource con của task | Task, bài nộp, review và trao đổi |
| M05 | `/evaluation-criteria`, `/evaluations`, `/lifecycle-requests` | Đánh giá và vòng đời thực tập |
| M06 | `/notifications`, `/announcements`, `/feedback`, `/dashboard`, `/reports`, `/audit-logs`, `/settings` | Điều hành, báo cáo và audit |
| M07 | `/documents`, `/ai/conversations`, `/ai/queries` | Kho tri thức, lịch sử và hỏi đáp AI |

### 3.3 Danh sách, lọc và phân trang

Request danh sách sử dụng `page`, `page_size`, `sort` và các filter đã khai báo trong OpenAPI. Response có dạng:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

Filter của client chỉ được thu hẹp kết quả. Backend luôn giao filter đó với data scope lấy từ server; client không thể dùng filter để mở rộng phạm vi.

### 3.4 Error response

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Không tìm thấy task",
    "details": {},
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

| HTTP status | Khi sử dụng |
|---|---|
| `401` | Thiếu access token; token/session hết hạn, sai hoặc đã bị thu hồi. Account bị khóa đã thu hồi session cũng đi theo nhánh này |
| `403` | Token/session còn hợp lệ nhưng account không `ACTIVE`, hoặc principal không có permission cho hành động |
| `404` | Resource không tồn tại hoặc nằm ngoài data scope, tránh làm lộ ID |
| `409` | Xung đột trạng thái hoặc vi phạm quy tắc nghiệp vụ |
| `422` | Request không đạt validation |
| `429` | Vượt rate limit của endpoint được giới hạn |
| `503` | AI/provider tạm lỗi; không biến lỗi M07 thành lỗi của M01–M06 |

`message` phục vụ người dùng; client xử lý ổn định bằng `error.code`, không parse nội dung `message`.

## 4. Xác thực và quản lý phiên

### 4.1 Access token

- Access token là JWT sống ngắn, TTL cấu hình theo môi trường.
- Claim tối thiểu: `sub`, `sid`, `iat`, `exp`, `iss`, `aud`.
- Không đưa danh sách intern, đợt hoặc data scope vào JWT.
- Backend nạp lại role và trạng thái tài khoản từ nguồn tin cậy; không tin role/scope do client gửi.

### 4.2 Refresh session

- Refresh token là chuỗi ngẫu nhiên và single-use. Rotation dùng row lock hoặc atomic compare-and-update để vô hiệu token cũ trước khi cấp token mới.
- Mỗi record có tối thiểu `family_id`, `parent_token_id` hoặc `replaced_by`, `used_at`, `expires_at`, `revoked_at` và hash token. Record đã rotate được giữ ít nhất đến khi hết hạn để phát hiện replay.
- Tái sử dụng refresh token đã rotate làm thu hồi toàn bộ session family liên quan và tạo security audit.
- Trình duyệt nhận refresh token qua cookie host-only có `Path=/api/v1/auth`, `HttpOnly`, `Secure`, mặc định `SameSite=Lax`; không cấu hình thuộc tính `Domain` nếu không có yêu cầu chia sẻ subdomain.
- Endpoint dùng refresh cookie chỉ chấp nhận `Origin` nằm trong allowlist và từ chối request trình duyệt thiếu `Origin`. Nếu topology buộc dùng `SameSite=None`, S0-04 phải bổ sung CSRF token; không được chỉ dựa vào CORS.
- Backend chỉ lưu hash refresh token và metadata phiên cần thiết; không lưu token gốc.
- Logout thu hồi phiên hiện tại.
- Đổi/reset mật khẩu, khóa tài khoản hoặc đổi role thu hồi toàn bộ phiên của người dùng.
- Request mới bị từ chối ngay khi account không còn `ACTIVE` hoặc session đã bị revoke; không chờ JWT tự hết hạn.

Các route không yêu cầu access token chỉ gồm login, refresh và password recovery. Đây không phải bypass middleware: refresh vẫn kiểm tra cookie, session và `Origin`; recovery vẫn kiểm tra token một lần và giới hạn tần suất. Các route còn lại mặc định yêu cầu phiên hợp lệ.

## 5. Mô hình kiểm soát quyền

### 5.1 Nguyên tắc

- Deny by default: endpoint không khai báo policy hợp lệ thì không được truy cập.
- UI guard chỉ dùng để ẩn/khóa thao tác cho đúng UX; không thay thế backend authorization.
- Permission trả lời câu hỏi “vai trò có được làm hành động này không?”.
- Data scope trả lời câu hỏi “người dùng được làm trên bản ghi nào?”.
- Business rule trả lời câu hỏi “resource ở trạng thái hiện tại có cho phép hành động không?”.
- Danh sách và dashboard phải lọc scope ngay trong query; không tải rộng rồi lọc ở UI hoặc Python.

### 5.2 Pipeline bắt buộc

Danh sách sau là vocabulary tối thiểu, không phải catalog đầy đủ:

```text
Request
  → xác thực access token và session
  → kiểm tra account ACTIVE
  → nạp principal và permission từ server
  → kiểm tra permission của route
  → suy ra data scope từ DB
  → query resource trong scope
  → kiểm tra ownership/assignment/trạng thái/business rule
  → thực thi transaction
  → ghi audit nếu là thao tác nhạy cảm
  → lọc trường response theo policy
```

Không nhận `user_id`, `role`, `mentor_id` hoặc `access_scope` của client làm bằng chứng quyền. Các trường này chỉ là dữ liệu request khi use case yêu cầu và phải được kiểm chứng lại.

### 5.3 Permission naming

Permission dùng một chuẩn duy nhất: `resource.action`.

```text
account.manage
role.assign
internship.read
mentor_assignment.manage
roadmap.manage
exam.attempt
task.create
task.submit
task.review
evaluation.draft
evaluation.publish
lifecycle.request
lifecycle.approve
report.read
audit.read
document.manage
ai.ask
ai.business_data_read
```

Không đặt role trong tên permission vì cùng một action còn phụ thuộc data scope và trạng thái resource. Tại S0-04, mỗi endpoint phải được map tới ít nhất một permission và một scope policy; endpoint thiếu mapping bị từ chối theo deny-by-default.

## 6. Ma trận quyền mức module

Ký hiệu “trong scope” luôn bao gồm kiểm tra ownership/assignment và business rule của module.

| Module | INTERN | MENTOR | MANAGER | ADMIN |
|---|---|---|---|---|
| M01 | Xem/sửa trường hồ sơ của mình; quản lý phiên của mình | Như Intern | Như Intern | Kế thừa Manager; tạo/sửa/khóa/mở khóa tài khoản, gán role, thu hồi phiên |
| M02 | Xem quá trình thực tập của mình | Xem intern đang được phân công | Quản lý đợt, intern và phân công; xem toàn bộ đợt demo | Kế thừa Manager |
| M03 | Xem nội dung được giao; làm bài; xem kết quả được công bố/cấu hình cho phép. Tiến độ do hệ thống cập nhật từ sự kiện học/thi, không có quyền tự sửa | Xem tiến độ và kết quả của intern được phân công | Quản lý roadmap, nội dung, câu hỏi, exam; xem thống kê | Kế thừa Manager |
| M04 | Xem task của mình; nộp/nộp lại; bình luận trong task của mình | Tạo/giao/review task và bình luận cho intern được phân công | Đọc toàn bộ dữ liệu task trong đợt demo phục vụ điều hành | Kế thừa Manager |
| M05 | Xem evaluation đã `PUBLISHED`; gửi yêu cầu gia hạn của mình | Tạo/sửa nháp/công bố evaluation cho intern được phân công; đề xuất gia hạn/dừng/kết thúc | Quản lý tiêu chí; chỉ xem evaluation đã công bố và dữ liệu được phép dùng khi quyết định lifecycle; phê duyệt/từ chối lifecycle | Kế thừa Manager; được xem evaluation nháp để giám sát nhưng không mặc nhiên được sửa/công bố nếu không có policy evaluator |
| M06 | Xem notification của mình; gửi feedback của mình | Chỉ xem notification của chính mình; xem dashboard theo intern được phân công | Gửi thông báo chung; xử lý feedback; xem dashboard/report toàn bộ đợt demo | Kế thừa Manager; xem audit và quản lý settings |
| M07 | Hỏi AI, xem lịch sử của mình trong scope được cấp | Hỏi AI theo scope intern được phân công | Hỏi AI theo toàn bộ đợt demo | Kế thừa Manager; quản lý, kích hoạt và archive tài liệu RAG |

### 6.1 Quy tắc phạm vi dữ liệu

| Role | Data scope do server suy ra |
|---|---|
| `INTERN` | `Users.id = principal.user_id`; internship hiện tại; roadmap/tài liệu được giao; task/submission của mình; evaluation đã công bố; notification, feedback và conversation của mình |
| `MENTOR` | Internship có `MentorAssignments` còn hiệu lực với `mentor_id = principal.user_id`; task/progress/evaluation liên quan |
| `MANAGER` | Toàn bộ các đợt trong phạm vi bản demo; khi hệ thống bổ sung phân công Manager–đợt thì policy phải thu hẹp theo quan hệ đó |
| `ADMIN` | Toàn hệ thống; kế thừa quyền nghiệp vụ Manager và có thêm quyền quản trị |

### 6.2 Các rule bắt buộc

- Intern truy cập ID của intern khác nhận `404`.
- Mentor truy cập intern không được phân công hoặc phân công đã hết hiệu lực nhận `404`.
- Chỉ mentor phụ trách được tạo/review task và đánh giá của intern đó.
- Intern không thể tự chuyển task sang hoàn thành.
- Intern chỉ nhận evaluation có trạng thái `PUBLISHED`.
- Manager không đọc evaluation `DRAFT`; Admin chỉ được đọc draft để giám sát, không mặc nhiên có quyền sửa/công bố.
- Notification luôn giới hạn theo `recipient_id`; Mentor không được đọc notification của intern được phân công.
- Chỉ Manager/Admin được phê duyệt hoặc từ chối lifecycle request.
- Dashboard, report, export và signed file URL dùng cùng data scope như API danh sách.
- Việc đổi mentor, đổi role hoặc khóa account phải có hiệu lực với request tiếp theo.
- Tiến độ học của Intern chỉ được hệ thống cập nhật từ sự kiện hoàn thành nội dung/lượt thi hợp lệ; client không có permission sửa trực tiếp phần trăm hoặc trạng thái tiến độ.

## 7. Hợp đồng truy cập dữ liệu của M07

Trong kiến trúc monolith FastAPI, “API nội bộ” là authorized query interface dùng chung policy, không bắt buộc là HTTP hoặc microservice riêng.

```text
AuthorizedQueryService.get_tasks(principal, filters)
AuthorizedQueryService.get_deadlines(principal, filters)
AuthorizedQueryService.get_learning_progress(principal, filters)
AuthorizedQueryService.get_summary(principal, filters)
```

Quy tắc bắt buộc:

- `principal` lấy từ phiên người hỏi, không lấy từ prompt hoặc dữ liệu do client tự khai.
- Mỗi tool call chạy lại permission và data-scope policy tương ứng của M01–M06.
- Chỉ allowlist truy vấn read-only; không hỗ trợ SQL tùy ý, URL tùy ý hoặc mutation nghiệp vụ.
- M07 không có quyền review/complete task, publish evaluation hoặc approve lifecycle request.
- Mỗi tool khai báo allowlist field/filter, giới hạn số bản ghi và time budget; không cung cấp truy vấn/export không giới hạn ngay cả khi dữ liệu nằm trong scope.
- Kết quả tool chỉ chứa trường tối thiểu cần cho câu trả lời.
- Retrieval lọc `Documents.access_scope` và `DocumentChunks.access_scope` trước khi gửi context cho LLM.
- Khi đọc lại lịch sử, Backend kiểm tra cả ownership conversation và scope hiện tại của dữ liệu/citation. Nội dung đã mất quyền phải được ẩn hoặc thay bằng trạng thái không còn quyền; cache và lịch sử không được bypass policy.
- LLM trả draft; M07 kiểm tra citation rồi mới phản hồi hoặc trả trạng thái không đủ bằng chứng.
- Ngay trước khi lưu hoặc trả assistant message, M07 phải xác thực lại session, account, permission và current scope. Nếu quyền thay đổi sau retrieval, M07 bắt buộc hủy toàn bộ draft/citation và không persist nội dung đã sinh; hệ thống trả fallback hoặc chạy lại retrieval/generation từ đầu dưới scope mới. Không lọc hậu kỳ câu trả lời free-form.
- Timeout/lỗi provider được cô lập; M01–M06 vẫn hoạt động bình thường.

Nếu M07 được tách thành service sau này, service identity chỉ xác thực dịch vụ; quyền dữ liệu vẫn được quyết định theo delegated principal của người hỏi.

## 8. Audit và logging

### 8.1 Sự kiện phải audit

- Login/logout, login thất bại, reset mật khẩu, thu hồi phiên và refresh-token replay.
- Tạo/sửa/khóa/mở khóa tài khoản và đổi role.
- Gán hoặc đổi mentor.
- Review/chuyển trạng thái task quan trọng.
- Công bố evaluation.
- Phê duyệt/từ chối gia hạn, dừng hoặc kết thúc.
- Upload, kích hoạt hoặc archive tài liệu RAG.
- M07 gọi tool đọc dữ liệu nghiệp vụ.
- Từ chối các thao tác nhạy cảm do thiếu permission hoặc sai scope.
- Thay đổi cấu hình hệ thống.

### 8.2 Trường tối thiểu

`actor_id`, `action`, `entity_type`, `entity_id`, `request_id`, `outcome`, `created_at` và metadata before/after đã loại dữ liệu nhạy cảm khi cần.

Audit của mutation thành công được ghi cùng transaction nghiệp vụ để tránh trạng thái nửa vời. Không ghi mật khẩu, token, secret, toàn bộ prompt/context nhạy cảm hoặc nội dung tệp vào log.

## 9. Tiêu chí kiểm thử và nghiệm thu

- Request ngoài allowlist không có phiên hợp lệ nhận `401`.
- Session sai/hết hạn/revoke nhận `401`; token/session còn hợp lệ nhưng account không `ACTIVE` nhận `403`.
- Khóa account phải thu hồi toàn bộ session; request tiếp theo không tạo được thao tác mới.
- Refresh token đã rotate không dùng lại được; phát hiện reuse phải thu hồi session family và tạo audit.
- Hai request refresh đồng thời chỉ một request được rotate thành công; request còn lại kích hoạt replay handling theo policy.
- Refresh bằng cookie từ `Origin` ngoài allowlist hoặc request trình duyệt thiếu `Origin` phải bị từ chối; `SameSite=None` bắt buộc có CSRF token.
- Role không có permission nhận `403`; resource ngoài scope nhận `404`.
- Intern A không đọc/sửa dữ liệu của Intern B bằng cách thay UUID.
- Mentor không đọc hoặc thao tác intern ngoài phân công; quyền cũ mất sau khi đổi mentor.
- Intern không thấy evaluation nháp và không tự hoàn thành task.
- Manager không thấy evaluation nháp; Admin chỉ có quyền đọc draft khi policy giám sát cho phép.
- Mentor thay UUID không đọc được notification của intern.
- Manager xem toàn bộ đợt demo; Admin thực hiện được quyền Manager và các quyền quản trị riêng.
- List, dashboard, report, export và signed file URL đều bị lọc theo cùng scope.
- Mutation nhạy cảm thành công sinh đúng một audit record; transaction lỗi không để audit/nghiệp vụ nửa vời.
- M07 không gọi được tool mutation; giả mạo principal hoặc scope bị từ chối.
- Tool M07 phải chặn filter/field ngoài allowlist, vượt giới hạn bản ghi hoặc time budget.
- RAG không retrieve chunk ngoài scope; thiếu citation trả fallback.
- Lịch sử/citation AI được tái kiểm theo scope hiện tại sau khi đổi role hoặc đổi mentor.
- Nếu quyền đổi trong lúc LLM đang xử lý, M07 không được lưu/trả dữ liệu theo scope cũ.
- Provider AI lỗi nhưng API M01–M06 vẫn dùng được.

## 10. Truy vết SRS

| Quyết định trong tài liệu | Xem chi tiết trong SRS |
|---|---|
| Web client–server; Backend API xử lý RBAC | Mục 2.1, dòng 83–92 |
| Bốn vai trò và bảy module | Mục 3.1–3.2, dòng 112–134 |
| Xác thực, phiên, RBAC, khóa tài khoản | Mục 4.1, FR-01–FR-04, dòng 138–145 |
| Scope Mentor và Manager | Mục 4.2, FR-07–FR-08, dòng 147–154 |
| Quyền LMS và kết quả thi | Mục 4.3, FR-09–FR-15, dòng 156–170 |
| Ownership task, submission và review | Mục 4.4, FR-16–FR-20, dòng 172–188 |
| Evaluation nháp/công bố và lifecycle approval | Mục 4.5, FR-21–FR-26, dòng 190–203 |
| Notification, dashboard, report và audit | Mục 4.6, FR-27–FR-32, dòng 205–218 |
| M07, internal API, citation và giới hạn an toàn | Mục 4.7, FR-33–FR-37, dòng 220–242 |
| Quy tắc ownership, scope và backend enforcement | Mục 5, BR-02–BR-12, dòng 244–261 |
| User role/status, assignment, task, evaluation, document scope, audit/chat | Mục 6.1–6.3, dòng 267–539 |
| Bảo mật, timeout và cô lập lỗi AI | Mục 7.2, NFR-02–NFR-06, dòng 732–742 |
| REST/JSON/HTTPS và AI dùng cùng lớp kiểm soát quyền | Mục 8.1, dòng 744–754 |
| Kiểm thử RBAC, AI/RAG và tiêu chí nghiệm thu | Mục 8.2–8.3 và 9, dòng 756–787 |

## 11. Bàn giao sang task sau

- S0-04 dùng tài liệu này để chốt OpenAPI, method, request/response DTO và mã lỗi theo endpoint.
- S0-10 dùng tài liệu này để triển khai auth dependency, permission guard, scoped repository query và test matrix.
- Nếu schema bổ sung quan hệ Manager–đợt, policy `MANAGER` phải đổi từ toàn bộ dữ liệu demo sang tập đợt được phân công.

## Câu hỏi chưa giải quyết

Không còn câu hỏi chặn S0-01. TTL token và thời hạn lưu audit/chat được cấu hình/chốt chi tiết ở S0-04 hoặc task triển khai liên quan.
