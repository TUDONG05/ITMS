# Thiết kế phiên xác thực phù hợp với Vercel

**Ngày:** 04/10/2026
**Trạng thái:** Đã phê duyệt để lập kế hoạch triển khai
**Nhánh:** `fix/vercel-auth-session`

## 1. Mục đích

Thay thế cơ chế lưu phiên xác thực trong bộ nhớ tiến trình bằng phiên được lưu bền vững trong cơ sở dữ liệu. Phiên đăng nhập phải tiếp tục hoạt động khi Vercel cold start hoặc chuyển yêu cầu sang một Function instance khác. Hệ thống đồng thời bổ sung cơ chế xoay vòng refresh token an toàn để ứng dụng Angular tự khôi phục khi access token ngắn hạn hết hiệu lực.

Sau khi hoàn thành, luồng xác thực phải đáp ứng các yêu cầu sau:

- duy trì đăng nhập khi tải lại trang hoặc Vercel thay đổi Function instance;
- sử dụng access token có thời hạn 15 phút và refresh token mà JavaScript không thể đọc;
- thu hồi đúng một phiên thiết bị khi đăng xuất và thu hồi toàn bộ phiên sau khi đổi mật khẩu;
- từ chối header định danh chỉ dành cho kiểm thử trên môi trường production;
- không hiển thị dashboard đã xác thực chỉ dựa trên trạng thái cũ trong trình duyệt;
- giữ nguyên vai trò người dùng và cấu trúc phản hồi API hiện có trong phạm vi tương thích.

## 2. Phạm vi

### 2.1. Trong phạm vi

- Thêm bảng phiên xác thực và migration Alembic tương ứng.
- Điều chỉnh luồng đăng nhập, làm mới token, đăng xuất, đổi mật khẩu và lấy người dùng hiện tại.
- Thống nhất dependency xác thực dùng chung cho các endpoint được bảo vệ.
- Bổ sung khởi tạo trạng thái xác thực, lưu access token trong bộ nhớ, route guard, HTTP interceptor và thông báo lỗi xác thực cho Angular.
- Bổ sung kiểm thử hồi quy backend và frontend cho toàn bộ vòng đời phiên.

### 2.2. Ngoài phạm vi

- OAuth hoặc đăng nhập qua nhà cung cấp danh tính bên thứ ba.
- Màn hình cho phép người dùng xem và thu hồi phiên trên thiết bị khác.
- Thay đổi vai trò, quy tắc mật khẩu hoặc phương thức gửi mã đặt lại mật khẩu.
- Chuyển xác thực sang một dịch vụ danh tính bên ngoài.
- Tách frontend và API sang hai tên miền khác nhau; hệ thống tiếp tục sử dụng định tuyến cùng nguồn qua `/api`.

## 3. Kiến trúc được lựa chọn

Hệ thống sử dụng hai loại thông tin xác thực với trách nhiệm khác nhau:

1. Access token dạng JWT, có thời hạn ngắn, dùng để cấp quyền cho các yêu cầu API thông thường.
2. Refresh token dạng chuỗi ngẫu nhiên, không chứa thông tin nghiệp vụ, dùng để nhận diện một phiên trong cơ sở dữ liệu và chỉ được truyền bằng cookie HttpOnly.

Cơ sở dữ liệu là nguồn sự thật về trạng thái phiên thay vì bộ nhớ của tiến trình Python. Mỗi yêu cầu được bảo vệ phải xác minh JWT, người dùng và phiên trong cơ sở dữ liệu. Cách này giúp đăng xuất có hiệu lực ngay và không phụ thuộc việc các yêu cầu liên tiếp có chạy trên cùng Vercel Function instance hay không.

## 4. Mô hình dữ liệu

Thêm model `AuthSession`, ánh xạ tới bảng `phien_dang_nhap`:

| Cột | Kiểu dữ liệu | Quy tắc |
| --- | --- | --- |
| `id` | UUID | Khóa chính, đồng thời là claim `sid` của JWT |
| `user_id` | UUID | Khóa ngoại tới `nguoi_dung.id`, `ON DELETE CASCADE`, có chỉ mục |
| `refresh_token_hash` | String(64) | Giá trị băm SHA-256 dạng hexadecimal, duy nhất và có chỉ mục |
| `remember_me` | Boolean | Quyết định cookie tồn tại theo phiên hay có thời hạn dài |
| `expires_at` | Timestamp có múi giờ | Thời điểm phiên refresh hết hạn trên máy chủ |
| `last_used_at` | Timestamp có múi giờ | Cập nhật sau mỗi lần xoay vòng thành công |
| `revoked_at` | Timestamp có múi giờ, nullable | Phiên không hợp lệ khi trường này khác null |
| `created_at` | Timestamp có múi giờ | Thời điểm tạo phiên |

Không cần chuyển đổi dữ liệu hiện có. Các token được cấp trước thời điểm triển khai không có phiên tương ứng trong cơ sở dữ liệu, vì vậy người dùng cần đăng nhập lại một lần sau khi phát hành phiên bản mới.

### 4.1. Biểu diễn refresh token

Trình duyệt nhận chuỗi `<session-uuid>.<secret>`. Trong đó, `secret` chứa tối thiểu 32 byte ngẫu nhiên và được mã hóa Base64 an toàn cho URL. Cơ sở dữ liệu chỉ lưu `SHA-256(full-token)`.

UUID trong token hỗ trợ phát hiện hành vi tái sử dụng. Nếu phiên vẫn tồn tại nhưng giá trị băm không còn khớp sau khi token đã được xoay vòng, hệ thống thu hồi phiên và từ chối yêu cầu.

## 5. Chính sách token và cookie

### 5.1. Access token

- Thời hạn được cấu hình bởi `ITMS_ACCESS_TOKEN_TTL_SECONDS`, mặc định 900 giây.
- Các claim gồm `sub`, `sid`, `tv`, `iat`, `exp`, `iss` và `aud`.
- Chỉ được lưu trong bộ nhớ Angular.
- Được gửi qua header `Authorization: Bearer <token>`.

### 5.2. Phiên refresh

- Khi không chọn “Ghi nhớ đăng nhập”: phiên trên máy chủ mặc định tồn tại 12 giờ; cookie không có `Max-Age` hoặc `Expires`, vì vậy là session cookie của trình duyệt.
- Khi chọn “Ghi nhớ đăng nhập”: phiên và cookie mặc định tồn tại 30 ngày.
- Bổ sung các biến môi trường:
  - `ITMS_SESSION_REFRESH_TTL_SECONDS=43200`;
  - `ITMS_REMEMBERED_REFRESH_TTL_SECONDS=2592000`.

### 5.3. Cookie

- Tên cookie: `itms_refresh_token`.
- `HttpOnly=true`.
- `SameSite=Lax`.
- `Secure=true` trên production và `false` khi phát triển/kiểm thử bằng HTTP cục bộ.
- `Path=/api/v1/auth`.
- Khi xóa cookie, máy chủ sử dụng cùng path và thuộc tính đã dùng khi tạo.

Một số trình duyệt có thể khôi phục session cookie khi người dùng bật chức năng khôi phục phiên. Thời hạn 12 giờ phía máy chủ tạo giới hạn độc lập cho trường hợp này.

## 6. Hợp đồng API

### 6.1. `POST /api/v1/auth/login`

Yêu cầu:

```json
{
  "email": "admin@itms.local",
  "password": "...",
  "remember_me": false
}
```

`remember_me` mặc định là `false` để tương thích ngược. Khi đăng nhập thành công, body tiếp tục sử dụng `LoginResponse` hiện có và phản hồi đồng thời thiết lập refresh cookie. Thông tin không hợp lệ tiếp tục trả về `401 INVALID_CREDENTIALS`.

### 6.2. `POST /api/v1/auth/refresh`

- Yêu cầu refresh cookie và không yêu cầu bearer token.
- Kiểm tra phiên, trạng thái người dùng, thời hạn, giá trị băm token và `token_version`.
- Xoay vòng refresh secret trong cùng một transaction.
- Trả về cấu trúc `LoginResponse` hiện có và thay thế cookie.
- Cookie bị thiếu, hết hạn, đã thu hồi hoặc bị tái sử dụng sẽ trả về `401 INVALID_REFRESH_TOKEN` và xóa cookie.

### 6.3. `POST /api/v1/auth/logout`

- Có tính idempotent.
- Thu hồi phiên được xác định bởi refresh cookie.
- Nếu thiếu cookie, bearer token hợp lệ có thể được dùng để xác định phiên.
- Luôn xóa cookie và trả về thông báo thành công hiện có.

### 6.4. `POST /api/v1/auth/change-password`

- Yêu cầu access token hợp lệ và phiên đang hoạt động.
- Cập nhật mật khẩu và tăng `token_version`.
- Thu hồi toàn bộ phiên đang hoạt động của người dùng.
- Xóa refresh cookie hiện tại.
- Người dùng phải đăng nhập lại.

### 6.5. Các endpoint được bảo vệ

Mọi endpoint được bảo vệ sử dụng một dependency xác thực dùng chung, thực hiện:

1. yêu cầu Bearer JWT;
2. kiểm tra chữ ký, issuer, audience và thời hạn;
3. truy vấn người dùng và phiên từ PostgreSQL;
4. kiểm tra trạng thái người dùng, trạng thái/thời hạn phiên, quyền sở hữu phiên và `token_version`.

Bearer UUID bị loại bỏ trong mọi môi trường. `X-User-Id` chỉ được chấp nhận khi `ITMS_ENVIRONMENT` là `development` hoặc `test`; production luôn từ chối header này.

## 7. Thành phần backend

- `app/models/auth.py`: model `AuthSession`.
- Alembic revision `0003_auth_sessions`: tạo hoặc xóa bảng cùng các chỉ mục.
- `app/core/settings.py`: cấu hình thời hạn refresh và cookie.
- `app/core/security.py`: hàm xử lý access token và refresh token ngẫu nhiên.
- `app/auth/service.py`: tạo, xoay vòng, xác minh, thu hồi phiên và thu hồi toàn bộ phiên sau khi đổi mật khẩu.
- `app/api/v1/auth.py`: vận chuyển token qua cookie và triển khai hợp đồng endpoint mới.
- `app/core/deps.py`: dependency duy nhất cho tài nguyên được bảo vệ, ủy quyền việc xác thực cho authentication service.

Tầng service sở hữu chính sách token và phiên. API route chỉ xử lý header/cookie HTTP và thao tác thiết lập hoặc xóa cookie.

## 8. Thành phần Angular và luồng dữ liệu

### 8.1. Trạng thái xác thực

`AuthService` lưu access token và người dùng đã xác thực trong signal. Service không lưu access token và không tin dữ liệu người dùng được tuần tự hóa trong web storage.

### 8.2. Khởi tạo ứng dụng

Một initializer thông qua `provideAppInitializer` gọi `/auth/refresh` trước khi hoàn tất điều hướng tới route được bảo vệ. Nếu thành công, hệ thống khôi phục access token và người dùng trong bộ nhớ. Phản hồi 401 được xem là trạng thái chưa đăng nhập và không tạo lỗi ứng dụng toàn cục.

### 8.3. HTTP interceptor

Functional interceptor thực hiện:

- không gắn bearer token cho login, refresh, forgot-password và reset-password;
- gắn access token trong bộ nhớ vào các yêu cầu API được bảo vệ;
- khi gặp 401 lần đầu, chuyển vào một thao tác refresh dùng chung;
- thử lại mỗi yêu cầu đang chờ đúng một lần bằng access token mới;
- không bao giờ thử lại chính yêu cầu refresh;
- khi refresh thất bại, xóa trạng thái xác thực và điều hướng về `/login`.

Quy tắc single-flight ngăn nhiều yêu cầu dashboard nhận 401 cùng lúc xoay vòng cùng một refresh token song song.

### 8.4. Điều hướng và giao diện

- `dashboardRoleGuard` kiểm tra signal `currentUser` đã được khởi tạo cùng vai trò tương ứng.
- Màn hình đăng nhập gửi giá trị checkbox qua trường `remember_me`.
- Đăng xuất gọi backend trước khi xóa trạng thái cục bộ; trạng thái cục bộ vẫn được xóa nếu yêu cầu mạng thất bại.
- Dashboard và hồ sơ phân biệt lỗi 401, 403, lỗi kết nối và lỗi máy chủ.

## 9. Xử lý lỗi và bảo mật

- Phản hồi xác thực tiếp tục sử dụng envelope `ApiError` hiện có.
- Lỗi refresh không tiết lộ người dùng hoặc phiên có tồn tại hay không.
- Refresh secret không xuất hiện trong JSON, log, local storage hoặc session storage.
- Đổi mật khẩu thu hồi toàn bộ phiên trong cùng một transaction.
- Xoay vòng refresh token có tính transaction để một phản hồi thành công chỉ tương ứng với một giá trị băm token hiện hành.
- Production từ chối header ghi đè định danh trước khi truy vấn người dùng.
- Định tuyến cùng nguồn, `SameSite=Lax` và chỉ cho phép refresh/logout bằng POST giúp hạn chế CSRF; CORS tiếp tục giới hạn theo danh sách origin cấu hình.
- Phản hồi login và refresh gửi `Cache-Control: no-store`.

## 10. Migration và phát hành

1. Áp dụng migration Alembic `0003_auth_sessions` trên cơ sở dữ liệu production.
2. Triển khai backend và frontend cùng lúc vì hợp đồng refresh thay đổi.
3. Các phiên cũ mất hiệu lực một lần; người dùng đăng nhập lại.
4. Kiểm tra môi trường production và thuộc tính bảo mật cookie.
5. Xác minh đăng nhập, tải dashboard, phục hồi sau tải lại trang, refresh khi hết hạn, đăng xuất và thu hồi phiên sau đổi mật khẩu trên bản triển khai production.

Migration không xóa hoặc biến đổi dữ liệu nghiệp vụ. Khi rollback, hệ thống chỉ xóa bảng `phien_dang_nhap`; người dùng và dữ liệu nghiệp vụ được giữ nguyên.

## 11. Chiến lược kiểm thử

### 11.1. Backend

- Đăng nhập tạo phiên bền vững và đúng loại cookie.
- “Ghi nhớ đăng nhập” tạo cookie tồn tại 30 ngày.
- Access JWT tiếp tục hoạt động với một `AuthService` instance mới, mô phỏng Vercel cold start.
- Refresh xoay vòng secret và từ chối token cũ bị sử dụng lại.
- Phiên hết hạn hoặc bị thu hồi trả về `INVALID_REFRESH_TOKEN`.
- Đăng xuất chỉ thu hồi phiên hiện tại.
- Đổi mật khẩu thu hồi mọi phiên và tăng `token_version`.
- Người dùng đã xóa, bị khóa hoặc không hoạt động không thể refresh hoặc truy cập tài nguyên.
- Production từ chối `X-User-Id` và mọi Bearer UUID.
- Development/test chỉ cho phép `X-User-Id` để hỗ trợ kiểm thử.

### 11.2. Frontend

- Quá trình khởi tạo khôi phục người dùng đã xác thực thông qua cookie.
- Login truyền đúng `remember_me`.
- Interceptor gắn access token.
- Một phản hồi 401 kích hoạt một lần refresh và một lần thử lại.
- Nhiều phản hồi 401 đồng thời dùng chung một yêu cầu refresh.
- Refresh thất bại sẽ xóa trạng thái và điều hướng về trang đăng nhập.
- Guard từ chối người dùng không tồn tại hoặc không đúng vai trò.
- Logout xóa trạng thái cục bộ kể cả khi yêu cầu HTTP thất bại.

### 11.3. Kiểm chứng toàn bộ

- Chạy toàn bộ bộ kiểm thử pytest của backend.
- Chạy unit test, lint và production build của Angular.
- Kiểm tra hợp đồng API theo chuỗi login, refresh, truy cập tài nguyên được bảo vệ và logout mà không hiển thị giá trị token trong đầu ra.

## 12. Tiêu chí nghiệm thu

- Phiên hợp lệ tồn tại qua lần khởi động lại tiến trình và thay đổi Vercel Function instance.
- Access token hết hạn được làm mới mà không gây gián đoạn nhìn thấy được.
- Đóng phiên trình duyệt không ghi nhớ thường loại bỏ refresh cookie; phiên ghi nhớ tồn tại tối đa 30 ngày.
- Đăng xuất và đổi mật khẩu thực hiện đúng phạm vi thu hồi đã quy định.
- Không endpoint production nào xác thực raw UUID hoặc `X-User-Id`.
- Ứng dụng Angular không hiển thị dashboard được bảo vệ chỉ dựa vào dữ liệu cũ trong trình duyệt.
- Toàn bộ kiểm thử mới và kiểm thử hiện có đều vượt qua.