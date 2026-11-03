# Giao task cho nhiều intern

Một task có thể được giao cho nhiều thành viên thực tập; mỗi thành viên có thể nhận nhiều task. Các intern cùng nhìn thấy một ID task và toàn bộ danh sách người được giao. Trong form giao task, bộ lọc Đợt thực tập nằm cạnh ô chọn nhiều intern; đổi đợt sẽ bỏ những lựa chọn không thuộc đợt mới.

## Hai cách thực hiện

| Chế độ | Bài nộp và review | Trạng thái |
| --- | --- | --- |
| `GROUP` — Làm chung | Một bài nộp chung. Các intern được giao có thể nộp, sửa hoặc xóa bài chung khi task chưa đóng; mentor review chung. | Một kết quả cho cả nhóm. |
| `INDIVIDUAL` — Làm độc lập | Mỗi intern nộp bài riêng, chỉ đọc/sửa/xóa bài của mình; mentor xem tất cả và chọn người cần review. | Theo từng intern; bài đã được chấp nhận bị khóa, kể cả khi người khác chưa xong. |

Chế độ được chọn khi tạo và không đổi khi sửa task. Với `INDIVIDUAL`, task chung chỉ hoàn thành khi tất cả intern hoàn thành. Khi chưa hoàn thành hết, trạng thái tổng hợp ưu tiên `SUBMITTED`, rồi `REVISION_REQUIRED`, còn lại là `TODO`. Intern xem trạng thái cá nhân trên trang task, dashboard và trợ lý; mentor xem trạng thái tổng hợp. Danh sách người được giao và phần trao đổi của task vẫn dùng chung.

## API

Mentor gửi **một** yêu cầu `POST /api/v1/tasks`:

```json
{
  "title": "Xây dựng API đăng nhập",
  "internship_member_ids": [
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002"
  ],
  "assignment_mode": "INDIVIDUAL",
  "priority": "MEDIUM"
}
```

Các ID là ID thành viên thực tập, không phải ID người dùng. Backend loại ID lặp, yêu cầu ít nhất một người và từ chối toàn bộ yêu cầu nếu có người không thuộc quyền quản lý của mentor. Một intern không được chọn qua hai tư cách thành viên khác nhau trên cùng task. Không truyền chế độ thì mặc định là `GROUP`; trường đơn `internship_member_id` cũ vẫn được chấp nhận khi tạo để tương thích.

Phản hồi gồm `internship_member_ids`, `assignment_mode` và `assignees` với tên intern, đợt thực tập và trạng thái. `POST /api/v1/tasks/{task_id}/submit` và `DELETE /api/v1/tasks/{task_id}/submission` tự xác định bài riêng theo intern đang đăng nhập trong chế độ `INDIVIDUAL`.

Review bài riêng bằng `POST /api/v1/tasks/{task_id}/review`:

```json
{
  "internship_member_id": "00000000-0000-0000-0000-000000000001",
  "decision": "COMPLETED",
  "review_comment": "Đạt yêu cầu"
}
```

`decision` nhận `COMPLETED` hoặc `REVISION_REQUIRED`. Với `GROUP`, không cần trường người nhận review. Mentor phải có quyền quản lý người được review.

## Migration

Từ thư mục `backend`, áp dụng migration theo hướng dẫn môi trường của dự án:

```powershell
uv run alembic upgrade head
```

- `0010_task_assignees` tạo bảng liên kết task/thành viên và chuyển người nhận cũ sang bảng này trước khi bỏ cột đơn.
- `0011_task_assignment_modes` thêm chế độ, trạng thái từng thành viên và bài nộp riêng; task cũ mặc định `GROUP`.

Task, bài nộp và trao đổi cũ giữ nguyên ID. Các task có nội dung giống nhau không tự động gộp. Downgrade từ `0011` bị từ chối khi còn task `INDIVIDUAL`; downgrade từ `0010` bị từ chối khi còn task có nhiều người nhận để tránh mất dữ liệu.
