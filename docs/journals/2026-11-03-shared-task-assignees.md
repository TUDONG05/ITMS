# 2026-11-03 — Task chung với nhiều người nhận

Yêu cầu chọn nhiều intern cần một task có nhiều người nhận. Gửi nhiều yêu cầu tạo task riêng sẽ không giữ chung ID, danh sách thành viên hay vòng review; triển khai chuyển sang bảng liên kết task/thành viên và một yêu cầu tạo chứa toàn bộ ID.

Người dùng chọn hỗ trợ cả hai cách làm: `GROUP` dùng một bài nộp/review chung; `INDIVIDUAL` dùng bài riêng và review có người nhận cụ thể. Chế độ cố định sau khi tạo. Bài riêng chỉ hiện cho chủ bài và mentor, còn danh sách thành viên và trao đổi dùng chung. Task tổng hợp chỉ hoàn thành khi tất cả bài riêng hoàn thành.

Review phát hiện dashboard/trợ lý còn đọc trạng thái tổng hợp cho intern và cờ nộp muộn chỉ đọc một bài bất kỳ. Đã sửa sang trạng thái cá nhân và kiểm tra mọi bài trong phạm vi được phép. Các thao tác cập nhật trạng thái khóa hàng task để tuần tự hóa submit, xóa, review và hủy; truy vấn tên thành viên/đợt được tải theo nhóm.

Migration `0010` và `0011` đã được áp dụng cục bộ sau khi tạo bản sao lưu trong `.tmp`. Đã đối chiếu giữ nguyên ID task, bài nộp và trao đổi; task cũ được chuyển sang `GROUP`. Không tự gộp các task lịch sử có nội dung giống nhau. Downgrade từ chối dữ liệu không thể biểu diễn bằng schema cũ.

Kiểm tra cuối: frontend có 52/52 test đạt, build và lint đạt; backend có 200/200 test đạt, Ruff và định dạng đạt. Local frontend, backend, database health và API task qua proxy đều hoạt động.
