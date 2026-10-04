# ITMS — Internship Training Management System

ITMS là nền tảng quản lý thực tập sinh, hỗ trợ ba vai trò **Admin**, **Mentor** và
**Intern**. Dự án gồm Angular web client, FastAPI REST API và PostgreSQL.

## Trạng thái hiện tại

MVP hiện có các phần nền tảng sau:

- Xác thực bằng email/mật khẩu, JWT access token, làm mới token, đăng xuất và `/me`.
- Đổi mật khẩu; quên/đặt lại mật khẩu bằng OTP qua Gmail SMTP.
- Chuyển hướng sau đăng nhập đến dashboard đúng vai trò; route guard chặn truy cập sai
  vai trò ở phía web client.
- Khung dashboard dùng **NG-ZORRO** cho Admin, Mentor và Intern, với menu theo quyền.
- Migration PostgreSQL cho 20 bảng nghiệp vụ và script seed dữ liệu phát triển.

Các màn nghiệp vụ trong dashboard hiện là khung điều hướng và dữ liệu minh họa; API CRUD
cho đào tạo, task, đánh giá, thông báo và AI sẽ được phát triển ở các nhánh tiếp theo.

## Kiến trúc

```text
┌──────────────────────┐       /api/v1/*       ┌──────────────────────────┐
│ Angular 22 + NG-ZORRO│ ────────────────────▶ │ FastAPI + SQLAlchemy      │
│ http://localhost:4200│ ◀──────────────────── │ http://localhost:8000     │
└──────────────────────┘     JSON / JWT        └────────────┬─────────────┘
                                                            │
                                                            ▼
                                                ┌──────────────────────────┐
                                                │ PostgreSQL               │
                                                │ database: itms           │
                                                └──────────────────────────┘
```

| Thành phần    | Công nghệ                        |
| ------------- | -------------------------------- |
| Web client    | Angular 22, TypeScript, NG-ZORRO |
| API           | Python 3.13, FastAPI, SQLAlchemy |
| Cơ sở dữ liệu | PostgreSQL 16+, Alembic, psycopg |
| Công cụ       | `uv`, npm, Ruff, Pytest          |

## Cấu trúc thư mục

```text
frontend/                  Angular application
backend/                   FastAPI application và Alembic migrations
backend/app/models/        20 SQLAlchemy business entities
backend/scripts/           Script seed dữ liệu phát triển
shared/                    Contracts và fixtures dùng chung
environment.local.example  Mẫu cấu hình local
```

## Yêu cầu

- Node.js 24 LTS và npm 11
- Python 3.13 và [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16 trở lên, đang chạy tại `localhost:5432`

## Khởi chạy nhanh

### 1. Tạo cấu hình local

Tạo file `environment.local` tại thư mục gốc và thay các giá trị mẫu, đặc biệt là URL
PostgreSQL và `ITMS_JWT_SECRET`. File này không được commit.

```bash
cp environment.local.example environment.local
```

Ví dụ cấu hình PostgreSQL local:

```dotenv
ITMS_ENVIRONMENT=development
ITMS_DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/itms
ITMS_JWT_SECRET=replace-with-a-long-random-development-secret
ITMS_ACCESS_TOKEN_TTL_SECONDS=900
ITMS_SESSION_REFRESH_TTL_SECONDS=43200
ITMS_REMEMBERED_REFRESH_TTL_SECONDS=2592000
ITMS_REFRESH_COOKIE_NAME=itms_refresh_token
```

Nếu sử dụng quên mật khẩu qua Gmail, điền `ITMS_SMTP_USERNAME`,
`ITMS_SMTP_PASSWORD` (Gmail App Password) và `ITMS_SMTP_FROM_EMAIL`. Không dùng mật khẩu
Gmail thông thường.

### 2. Cài dependency

```bash
cd backend
uv sync --locked

cd ../frontend
npm ci
```

### 3. Áp schema và seed dữ liệu phát triển

Tạo database `itms` trước nếu database chưa tồn tại, sau đó chạy:

```bash
cd backend
uv run alembic upgrade head
uv run python scripts/seed_system_data.py
```

`seed_system_data.py` chỉ chạy khi `ITMS_ENVIRONMENT=development`; script cập nhật dữ liệu
mẫu theo UUID cố định nên có thể chạy lặp lại mà không sinh thêm bản ghi. Script sẽ đặt lại
mật khẩu cho các tài khoản demo `@itms.local`.

### 4. Chạy backend và frontend

Mở hai terminal riêng:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

```bash
cd frontend
npm start
```

| Dịch vụ             | Địa chỉ                                  |
| ------------------- | ---------------------------------------- |
| Web client          | <http://localhost:4200>                  |
| API health          | <http://localhost:8000/api/v1/health>    |
| API database health | <http://localhost:8000/api/v1/health/db> |

Angular dùng `proxy.conf.json` để chuyển tiếp `/api/*` đến backend khi chạy local.

## Tài khoản demo

| Vai trò | Email               | Mật khẩu       |
| ------- | ------------------- | -------------- |
| Admin   | `admin@itms.local`  | `Admin@12345`  |
| Mentor  | `mentor@itms.local` | `Mentor@12345` |
| Intern  | `intern@itms.local` | `Intern@12345` |

Seed cũng tạo thêm một Mentor và bốn Intern để minh họa phân công, tiến độ, task và đánh giá.
Không dùng các tài khoản này ngoài môi trường phát triển.

## API đang có

Tiền tố API cố định: `/api/v1`.

| Phương thức | Endpoint                | Mô tả                            |
| ----------- | ----------------------- | -------------------------------- |
| `GET`       | `/health`               | Health probe của dịch vụ         |
| `GET`       | `/health/db`            | Kiểm tra kết nối PostgreSQL      |
| `POST`      | `/auth/login`           | Đăng nhập, tạo session DB và đặt refresh cookie |
| `POST`      | `/auth/refresh`         | Xoay refresh token từ cookie (không cần bearer) |
| `POST`      | `/auth/logout`          | Thu hồi session hiện tại và xóa cookie |
| `POST`      | `/auth/change-password` | Đổi mật khẩu khi đã đăng nhập (thu hồi mọi session) |
| `POST`      | `/auth/forgot-password` | Gửi OTP đặt lại mật khẩu         |
| `POST`      | `/auth/reset-password`  | Xác thực OTP và đặt mật khẩu mới |
| `GET`       | `/me`                   | Lấy tài khoản từ Bearer token    |

### Phiên đăng nhập bền vững

- Access token (JWT, 15 phút) chỉ giữ trong bộ nhớ Angular, không lưu web storage.
- Refresh token dạng opaque lưu băm SHA-256 trong bảng `phien_dang_nhap`; giá trị gốc
  chỉ nằm trong cookie `itms_refresh_token` (`HttpOnly`, `SameSite=Lax`,
  path `/api/v1/auth`; `Secure` trên production).
- Không chọn “Ghi nhớ đăng nhập”: session cookie, tối đa 12 giờ. Có chọn: persistent
  cookie, tối đa 30 ngày. Mỗi lần refresh xoay token một lần; token cũ mất hiệu lực.
- Đổi/đặt lại mật khẩu thu hồi toàn bộ session; đăng xuất thu hồi session hiện tại.
- `X-User-Id` chỉ có tác dụng ở `development`/`test`; Bearer UUID luôn bị từ chối.

### Triển khai phiên bản session

1. Bắt buộc chạy `uv run alembic upgrade head` trước khi deploy (migration
   `0007_auth_sessions` tạo bảng `phien_dang_nhap`).
2. Đặt đủ biến `ITMS_SESSION_REFRESH_TTL_SECONDS`,
   `ITMS_REMEMBERED_REFRESH_TTL_SECONDS`, `ITMS_REFRESH_COOKIE_NAME` nếu cần khác mặc định.
3. Sau deploy, mọi phiên cũ phải đăng nhập lại một lần để tạo session mới.

## Mô hình dữ liệu

Migration hiện quản lý 21 bảng: 20 bảng nghiệp vụ với tên bảng/thuộc tính tiếng Việt, Chúng bao phủ:

- phiên đăng nhập bền vững (`phien_dang_nhap`);

- người dùng và phân quyền;
- đợt/thành viên/yêu cầu thực tập;
- lộ trình, giai đoạn, nội dung và tiến độ học tập;
- quiz, câu hỏi, lượt làm bài;
- task, bài nộp và trao đổi;
- tiêu chí và kết quả đánh giá;
- thông báo/lượt đọc; và hội thoại/tin nhắn AI.

Xem migration tại `backend/migrations/versions/` và model tại `backend/app/models/`.

## Kiểm tra chất lượng

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

```bash
cd frontend
npm run lint
npm run format:check
npm run compile
```

## Lưu ý phát triển

- Không commit `environment.local`, thông tin SMTP, mật khẩu hay JWT secret.
- Session đang được lưu trong bộ nhớ của tiến trình FastAPI. Vì vậy logout/refresh chỉ có
  hiệu lực trên tiến trình đang phục vụ request; trước khi triển khai nhiều instance cần
  thay bằng session store dùng chung.
- Tạo nhánh chức năng từ `develop`, mở pull request về `develop`, và chỉ seed database local.

## Giấy phép

Dự án phục vụ mục đích học tập và quản lý nội bộ.
