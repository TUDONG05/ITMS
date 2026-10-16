# Tài liệu 9 tool của chatbot ITMS

## 1. Tổng quan

Chatbot ITMS không truy cập cơ sở dữ liệu trực tiếp. Khi người dùng hỏi về dữ liệu nghiệp vụ, mô hình AI chọn một trong 9 tool dưới đây. Backend thực thi tool theo danh tính và vai trò hiện tại, sau đó chỉ gửi kết quả đã được giới hạn về cho mô hình.

| STT | Tool | Chức năng |
| --- | --- | --- |
| 1 | `find_accessible_interns` | Tìm thực tập sinh trong phạm vi được phép truy cập |
| 2 | `get_mentor_assignment` | Lấy mentor đang phụ trách thực tập sinh |
| 3 | `get_roadmap` | Lấy roadmap, phase và nội dung học tập |
| 4 | `get_learning_progress` | Lấy số liệu tiến độ học tập |
| 5 | `get_tasks` | Lấy task theo thực tập sinh và trạng thái |
| 6 | `get_deadlines` | Lấy task sắp đến hạn hoặc quá hạn |
| 7 | `get_quiz_results` | Lấy kết quả quiz, không trả đáp án |
| 8 | `get_evaluations` | Lấy đánh giá theo quyền truy cập |
| 9 | `get_notifications` | Lấy thông báo đã nhận hoặc đã gửi |

Đây là các function tool nội bộ, không phải REST endpoint công khai. Client chỉ gọi API chat; backend tự truyền người dùng đã xác thực vào tool.

## 2. Phân quyền chung

| Vai trò | Phạm vi |
| --- | --- |
| `INTERN` | Chỉ dữ liệu của chính người đang đăng nhập. Nếu AI truyền ID của intern khác, backend vẫn dùng ID của người hiện tại. |
| `MENTOR` | Chỉ dữ liệu của các thực tập sinh thuộc bản ghi thực tập do mentor phụ trách. |
| `ADMIN` | Có thể truy vấn toàn bộ dữ liệu thuộc phạm vi của từng tool. |

Backend kiểm tra lại vai trò, trạng thái tài khoản và phạm vi phân công trong quá trình xử lý. Nếu quyền thay đổi giữa lúc bắt đầu và hoàn tất truy vấn, yêu cầu bị từ chối thay vì trả dữ liệu theo quyền cũ.

## 3. Quy ước chung

- `limit` được ép vào khoảng từ 1 đến 20.
- Giới hạn mặc định thường là 10; riêng `find_accessible_interns` mặc định là 5.
- `total_count` là tổng số bản ghi phù hợp trước khi áp dụng giới hạn.
- `returned_count` là số bản ghi chi tiết thực tế được trả về.
- `truncated = true` nghĩa là còn dữ liệu phù hợp nhưng phần chi tiết đã bị cắt theo `limit`.
- Khi trả lời câu hỏi “bao nhiêu”, chatbot phải dùng `total_count`, không dùng `returned_count`.
- Nội dung văn bản dài được rút gọn ở mức tối đa 2.000 ký tự trước khi gửi sang AI.
- UUID và thời gian được chuẩn hóa thành chuỗi trong payload gửi đến nhà cung cấp AI.

## 4. Chi tiết từng tool

### 4.1. `find_accessible_interns`

Mục đích: tìm thực tập sinh theo tên hoặc email. Tool thường được dùng khi câu hỏi nhắc đến một người cụ thể nhưng chưa xác định được `intern_id`.

Phân quyền:

- Intern chỉ tìm thấy chính mình.
- Mentor chỉ tìm thấy thực tập sinh do mình phụ trách.
- Admin tìm trên toàn bộ thực tập sinh.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `query` | string | Chuỗi rỗng | Tìm không phân biệt hoa thường theo họ tên hoặc email |
| `limit` | integer | 5 | Số dòng chi tiết, từ 1 đến 20 |

Kết quả có `total_count`, `returned_count`, `truncated` và `interns`. Mỗi intern gồm `intern_id`, `full_name`, `internship`, `member_status`.

Ví dụ: “Tìm thực tập sinh Nguyễn Văn A”, “Có tất cả bao nhiêu thực tập sinh?”

### 4.2. `get_mentor_assignment`

Mục đích: lấy mentor phụ trách thực tập sinh trong các bản ghi thực tập có trạng thái `ACTIVE` hoặc `EXTENDED`.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `intern_id` | UUID string | Theo vai trò | Intern luôn dùng ID của mình; Mentor/Admin có thể chỉ định intern |
| `limit` | integer | 10 | Số phân công tối đa, từ 1 đến 20 |

Mỗi phần tử trong `assignments` gồm:

- `intern_id`, `intern_name`
- `mentor_id`, `mentor_name`; có thể là `null` nếu chưa phân mentor
- `internship`, `member_status`

Ví dụ: “Mentor của tôi là ai?”, “Ai đang phụ trách Nguyễn Văn A?”

### 4.3. `get_roadmap`

Mục đích: lấy roadmap đã gán, các phase và nội dung học tập trong từng phase.

Phân quyền bổ sung: Intern chỉ xem roadmap `ACTIVE` trên bản ghi thực tập `ACTIVE` hoặc `EXTENDED`. Mentor và Admin xem theo phạm vi tương ứng.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `intern_id` | UUID string | Theo vai trò | Chọn intern khi người gọi là Mentor/Admin |
| `include_contents` | boolean | `true` | Có trả nội dung trong từng phase hay không |

Kết quả chính nằm trong `roadmaps`:

- Roadmap: `intern_id`, `roadmap_id`, `name`, `status`
- Phase: `id`, `name`, `order_no`
- Content: `id`, `title`, `type`

Tool trả tối đa 20 roadmap, 20 phase trên mỗi roadmap và 20 nội dung trên mỗi phase.

Ví dụ: “Roadmap của tôi gồm những giai đoạn nào?”

### 4.4. `get_learning_progress`

Mục đích: tính tiến độ dựa trên nội dung của roadmap và các bản ghi học tập.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `intern_id` | UUID string | Theo vai trò | Chọn intern khi người gọi là Mentor/Admin |

| Trường trong `progress` | Ý nghĩa |
| --- | --- |
| `intern_id` | ID thực tập sinh |
| `roadmap_assigned` | Đã được gán roadmap hay chưa |
| `total_contents` | Tổng số nội dung |
| `completed_contents` | Số nội dung hoàn thành |
| `in_progress_contents` | Số nội dung đang học |
| `not_started_contents` | Số nội dung chưa bắt đầu |
| `progress_percent` | Trung bình tiến độ của toàn bộ nội dung |

`progress_percent` bằng tổng phần trăm của các bản ghi tiến độ chia cho tổng số nội dung trong roadmap.

Ví dụ: “Tiến độ học tập của tôi thế nào?”

### 4.5. `get_tasks`

Mục đích: lấy task trong phạm vi được phép xem và có thể lọc theo trạng thái.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `intern_id` | UUID string | Theo vai trò | Chọn intern khi người gọi là Mentor/Admin |
| `status` | enum string | Tất cả | `TODO`, `SUBMITTED`, `REVISION_REQUIRED`, `COMPLETED`, `CANCELLED` |
| `limit` | integer | 10 | Số dòng chi tiết, từ 1 đến 20 |

Kết quả có `total_count`, `returned_count`, `truncated` và `tasks`. Mỗi task gồm `id`, `intern_id`, `intern_name`, `title`, `status`, `priority`, `deadline`.

Task được sắp theo deadline gần nhất; task không có deadline xếp sau.

Ví dụ: “Tôi có bao nhiêu task chưa làm?”

### 4.6. `get_deadlines`

Mục đích: lấy task chưa hoàn tất và chưa hủy có deadline thuộc khoảng yêu cầu.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `intern_id` | UUID string | Theo vai trò | Chọn intern khi người gọi là Mentor/Admin |
| `range` | enum string | `NEXT_7_DAYS` | `NEXT`, `NEXT_7_DAYS`, `NEXT_30_DAYS`, `OVERDUE` |
| `limit` | integer | 10 | Số dòng chi tiết, từ 1 đến 20 |

| Giá trị `range` | Ý nghĩa |
| --- | --- |
| `NEXT` | Tất cả deadline từ hiện tại trở đi |
| `NEXT_7_DAYS` | Từ hiện tại đến 7 ngày tiếp theo |
| `NEXT_30_DAYS` | Từ hiện tại đến 30 ngày tiếp theo |
| `OVERDUE` | Deadline đã qua nhưng task chưa hoàn tất hoặc hủy |

Kết quả có metadata và `deadlines`. Mỗi dòng gồm `task_id`, `intern_id`, `intern_name`, `title`, `deadline`, `status`, `deadline_state`. Trạng thái deadline là `UPCOMING` hoặc `OVERDUE`.

Ví dụ: “Deadline gần nhất của tôi là gì?”, “Có task nào quá hạn không?”

### 4.7. `get_quiz_results`

Mục đích: lấy lịch sử làm quiz trong phạm vi được phép xem.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `intern_id` | UUID string | Theo vai trò | Chọn intern khi người gọi là Mentor/Admin |
| `quiz_id` | UUID string | Tất cả quiz | Chỉ lấy kết quả của một quiz |

Kết quả có metadata và `quiz_results`. Mỗi lượt làm gồm `quiz_id`, `intern_id`, `intern_name`, `title`, `attempt_no`, `score`, `passed`, `started_at`, `submitted_at`.

- Tối đa 20 lượt làm gần nhất được trả về.
- `correct_answers_included` luôn là `false`.
- Tool không trả câu trả lời của intern hoặc đáp án đúng.

Ví dụ: “Kết quả quiz gần nhất của tôi là bao nhiêu?”

### 4.8. `get_evaluations`

Mục đích: lấy đánh giá thực tập sinh theo quyền và trạng thái công bố.

Phân quyền bổ sung:

- Intern chỉ xem đánh giá `PUBLISHED`.
- Mentor xem đánh giá `PUBLISHED` và bản nháp do chính mentor đó tạo.
- Admin xem toàn bộ đánh giá trong phạm vi truy vấn.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `intern_id` | UUID string | Theo vai trò | Chọn intern khi người gọi là Mentor/Admin |
| `status` | enum string | Các trạng thái được phép | `DRAFT` hoặc `PUBLISHED` |
| `limit` | integer | 10 | Số dòng chi tiết, từ 1 đến 20 |

Kết quả có metadata và `evaluations`. Mỗi đánh giá gồm `id`, `intern_id`, `intern_name`, `type`, `status`, `total_score`, `comment`, `published_at`.

`comment` được giới hạn tối đa 2.000 ký tự trước khi gửi sang AI.

Ví dụ: “Đánh giá mới nhất của tôi là gì?”

### 4.9. `get_notifications`

Mục đích: lấy thông báo đúng theo đối tượng nhận, tìm theo nội dung và đếm số chưa đọc.

Phân quyền:

- Intern/Mentor nhận thông báo có đối tượng `ALL`, đúng `ROLE`, hoặc chỉ định trực tiếp `USER` của mình.
- Admin xem toàn bộ thông báo đã gửi.
- Admin không có trạng thái đọc cá nhân, vì vậy `status = UNREAD` không hợp lệ với Admin.

| Tham số | Kiểu | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `query` | string | Chuỗi rỗng | Tìm không phân biệt hoa thường trong tiêu đề hoặc nội dung |
| `status` | enum string | `ALL` | `ALL` hoặc `UNREAD`; `UNREAD` chỉ cho Intern/Mentor |
| `limit` | integer | 10 | Số dòng chi tiết, từ 1 đến 20 |

| Trường kết quả | Ý nghĩa |
| --- | --- |
| `scope` | `RECEIVED` với Intern/Mentor; `ALL_SENT` với Admin |
| `status` | Bộ lọc đã áp dụng |
| `total_count` | Tổng thông báo phù hợp sau lọc, trước `limit` |
| `unread_count` | Số chưa đọc trong tập tìm kiếm; `null` với Admin |
| `returned_count` | Số thông báo chi tiết được trả về |
| `truncated` | Có bị cắt theo giới hạn hay không |
| `notifications` | Danh sách thông báo |

Mỗi thông báo luôn có `id`, `title`, `content`, `target_type`, `created_at`, `creator_name`.

- Intern/Mentor có thêm `is_read`, `read_at`.
- Admin có thêm `recipient_names`, `read_count`.
- Tool không gửi `target_data` hoặc `created_by` sang mô hình AI.

Ví dụ: “Tôi có bao nhiêu thông báo chưa đọc?”, “Admin đã gửi bao nhiêu thông báo?”

## 5. Lỗi có thể gặp

| Mã lỗi | HTTP | Nguyên nhân |
| --- | --- | --- |
| `UNKNOWN_AI_TOOL` | 422 | Mô hình yêu cầu tool không tồn tại |
| `INVALID_TOOL_ARGUMENT` | 422 | UUID, trạng thái hoặc tham số không hợp lệ |
| `INTERN_NOT_FOUND` | 404 | Không tìm thấy intern trong phạm vi được phép xem |
| `FORBIDDEN` | 403 | Vai trò không được phép sử dụng trợ lý |
| `AI_SCOPE_CHANGED` | 409 | Vai trò, trạng thái tài khoản hoặc phạm vi phân công thay đổi trong lúc xử lý |

## 6. Lưu ý về contract hiện tại

- `get_mentor_assignment`, `get_roadmap` và `get_learning_progress` chưa trả metadata đếm.
- `get_quiz_results` và `get_evaluations` trả object danh sách tối giản khi người dùng không có bản ghi thực tập phù hợp; khi có phạm vi truy vấn mới có metadata đếm.
- `get_roadmap` giới hạn dữ liệu theo từng tầng nhưng chưa trả cờ `truncated` cho roadmap, phase hoặc content.
- Các điểm trên cần được lưu ý nếu frontend hoặc consumer khác dùng trực tiếp kết quả tool.

## 7. Nguồn triển khai

- Định nghĩa và thực thi: `backend/app/services/assistant_tools.py`
- Điều phối, kiểm tra phạm vi và citation: `backend/app/services/assistant.py`
- Kiểm thử contract và phân quyền: `backend/tests/test_assistant_chat.py`
