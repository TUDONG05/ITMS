# ITMS — Internship Training Management System

![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI 0.141](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white)
![Angular 22](https://img.shields.io/badge/Angular-22-DD0031?style=flat-square&logo=angular&logoColor=white)
![PostgreSQL 16+](https://img.shields.io/badge/PostgreSQL-16%2B-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)

ITMS là hệ thống quản lý thực tập sinh dành cho ba vai trò **Admin**, **Mentor** và
**Intern**. Ứng dụng cung cấp giao diện Angular, REST API FastAPI và cơ sở dữ liệu
PostgreSQL trong cùng một repository.

## Chức năng chính

- Xác thực bằng email/mật khẩu, JWT access token và refresh token `HttpOnly`.
- Quản lý người dùng, vai trò và trạng thái tài khoản.
- Quản lý đợt thực tập, thành viên, phân công Mentor và yêu cầu thực tập.
- Quản lý lộ trình, giai đoạn, nội dung đào tạo, quiz và câu hỏi.
- Quản lý công việc, bài nộp, phản hồi và trao đổi giữa Mentor–Intern.
- Dashboard theo vai trò, tổng hợp tiến độ và số liệu vận hành.
- Quản lý hồ sơ cá nhân và ảnh đại diện.
- Quên/đặt lại mật khẩu bằng OTP qua Gmail SMTP.

## Kiến trúc

```text
┌─────────────────────────┐       /api/v1/*       ┌──────────────────────────┐
│ Angular 22 + NG-ZORRO   │ ────────────────────▶ │ FastAPI + SQLAlchemy     │
│ http://localhost:4200   │ ◀──────────────────── │ http://localhost:8000    │
└─────────────────────────┘     JSON / JWT        └────────────┬─────────────┘
                                                               │
                                                               ▼
                                                   ┌─────────────────────────┐
                                                   │ PostgreSQL + Alembic    │
                                                   └─────────────────────────┘
```

## Công nghệ sử dụng

| Nhóm            | Công nghệ                                                 |
| --------------- | --------------------------------------------------------- |
| Frontend        | Angular 22, TypeScript 6, RxJS 7, NG-ZORRO 22             |
| Backend         | Python 3.13, FastAPI, Uvicorn                             |
| Data layer      | SQLAlchemy 2, Pydantic 2                                  |
| Database        | PostgreSQL 16+, Alembic, psycopg 3                        |
| Kiểm thử        | Pytest, Angular Test Runner, Vitest, jsdom                |
| Chất lượng mã   | Ruff, ESLint, Prettier                                    |
| Quản lý package | uv, npm 11                                                |
| Triển khai      | Vercel Functions, Vercel Git Integration, Neon PostgreSQL |
| CI              | GitHub Actions                                            |

## Cấu trúc repository

```text
ITMS/
├── api/                         Vercel Python Function entry point
├── backend/
│   ├── app/                     FastAPI application
│   ├── app/models/              SQLAlchemy models
│   ├── migrations/versions/     Alembic revisions
│   ├── scripts/                 Development seed scripts
│   └── tests/                   Backend test suite
├── frontend/                    Angular application
├── .github/workflows/ci.yml     CI checks
├── environment.local.example    Mẫu cấu hình local
└── vercel.json                  Vercel build, function và routing config
```

## Yêu cầu môi trường

- Node.js 24 LTS và npm 11.
- Python 3.13 và [uv](https://docs.astral.sh/uv/).
- PostgreSQL 16 trở lên.
- Vercel CLI khi thao tác với môi trường production.

## Khởi chạy local

### 1. Tạo cấu hình

Sao chép file mẫu tại thư mục gốc:

```bash
cp environment.local.example environment.local
```

Các biến tối thiểu:

```dotenv
ITMS_ENVIRONMENT=development
ITMS_DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/itms
ITMS_JWT_SECRET=replace-with-a-long-random-development-secret
ITMS_ACCESS_TOKEN_TTL_SECONDS=900
ITMS_SESSION_REFRESH_TTL_SECONDS=43200
ITMS_REMEMBERED_REFRESH_TTL_SECONDS=2592000
ITMS_REFRESH_COOKIE_NAME=itms_refresh_token
```

Nếu sử dụng chức năng OTP, cấu hình thêm `ITMS_SMTP_USERNAME`,
`ITMS_SMTP_PASSWORD` và `ITMS_SMTP_FROM_EMAIL`. Chỉ sử dụng Gmail App Password;
không dùng mật khẩu Gmail thông thường.

> `environment.local`, `.env*` và `.vercel/` chứa thông tin nhạy cảm và đã được
> Git bỏ qua. Không commit hoặc gửi các file này qua kênh công khai.

### 2. Cài dependency

```bash
cd backend
uv sync --locked

cd ../frontend
npm ci
```

### 3. Tạo schema và dữ liệu phát triển

```bash
cd backend
uv run alembic upgrade head
uv run python scripts/seed_system_data.py
```

`seed_system_data.py` chỉ chạy khi `ITMS_ENVIRONMENT=development`. Script có thể
chạy lặp lại và chỉ dành cho máy phát triển; tuyệt đối không seed production.

### 4. Chạy ứng dụng

Mở hai terminal riêng:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

```bash
cd frontend
npm start
```

| Dịch vụ         | Địa chỉ                                  |
| --------------- | ---------------------------------------- |
| Web client      | <http://localhost:4200>                  |
| API health      | <http://localhost:8000/api/v1/health>    |
| Database health | <http://localhost:8000/api/v1/health/db> |

Angular sử dụng `frontend/proxy.conf.json` để chuyển tiếp `/api/*` tới backend
trong môi trường local.

## Tài khoản phát triển

Script seed tạo tài khoản mẫu cho Admin, Mentor và Intern với domain
`@itms.local`. Thông tin khởi tạo nằm trong `backend/scripts/seed_system_data.py`
và chỉ được phép sử dụng ở môi trường development.

## API

Tất cả endpoint sử dụng tiền tố `/api/v1`.

| Nhóm        | Endpoint tiêu biểu                                            | Mục đích                                |
| ----------- | ------------------------------------------------------------- | --------------------------------------- |
| Health      | `/health`, `/health/db`                                       | Kiểm tra service và kết nối DB          |
| Auth        | `/auth/login`, `/auth/refresh`, `/auth/logout`, `/me`         | Quản lý phiên đăng nhập                 |
| Users       | `/users`                                                      | Quản lý tài khoản và trạng thái         |
| Internships | `/internships`, `/internship-members`                         | Quản lý đợt và thành viên               |
| Mentor      | `/mentor/overview`, `/mentor/interns`, `/mentor/assignments`  | Theo dõi và phân công Intern            |
| Training    | `/training/roadmaps`, `/training/phases`, `/training/quizzes` | Quản lý đào tạo                         |
| Tasks       | `/tasks`                                                      | Quản lý công việc, bài nộp và bình luận |
| Profile     | `/profile`, `/profile/avatar`                                 | Quản lý hồ sơ cá nhân                   |
| Dashboard   | `/dashboard`                                                  | Dữ liệu tổng quan theo vai trò          |

FastAPI cung cấp OpenAPI tại `/docs` khi tài liệu API không bị tắt theo môi
trường triển khai.

## Cơ chế phiên đăng nhập

- Access token là JWT có thời hạn mặc định 15 phút và chỉ được giữ trong bộ nhớ
  Angular, không lưu vào `localStorage` hoặc `sessionStorage`.
- Refresh token là giá trị opaque. Backend chỉ lưu SHA-256 hash trong bảng
  `phien_dang_nhap`; token gốc nằm trong cookie `itms_refresh_token`.
- Cookie production sử dụng `HttpOnly`, `Secure`, `SameSite=Lax` và path
  `/api/v1/auth`.
- “Ghi nhớ đăng nhập” dùng persistent cookie tối đa 30 ngày. Khi bỏ chọn, hệ
  thống dùng session cookie và giới hạn phiên phía server là 12 giờ.
- Refresh token được xoay sau mỗi lần sử dụng; token cũ mất hiệu lực.
- Đổi/đặt lại mật khẩu thu hồi mọi phiên. Đăng xuất chỉ thu hồi phiên hiện tại.
- Header `X-User-Id` chỉ dùng trong `development` hoặc `test`; production luôn
  yêu cầu JWT hợp lệ.

## Quy trình migration database

### Nguyên tắc bắt buộc

Migration là một bước phát hành độc lập với Vercel build:

- `vercel.json` chỉ build frontend và đóng gói FastAPI; **không chạy Alembic**.
- Job `Apply database migrations` trong GitHub Actions chạy trên PostgreSQL tạm
  của CI tại `localhost`; **không cập nhật production DB**.
- Mỗi thành viên phải kiểm tra Alembic revision trước và sau khi phát hành code
  có thay đổi model/schema.
- Không chạy `seed_system_data.py` trên production.
- Migration xóa cột, xóa bản ghi hoặc thay đổi constraint phải được backup và
  review dữ liệu trước khi chạy.

### Local và test

```bash
cd backend
uv run alembic current
uv run alembic heads
uv run alembic upgrade head
uv run alembic current
```

Kết quả của `current` sau cùng phải trùng với revision được đánh dấu `(head)`.

### Production trên Vercel/Neon

Project production có tên `itms`; domain là `itms-two.vercel.app`. Không link
nhầm vào project khác chỉ vì tên domain giống nhau.

#### 1. Cài đặt và đăng nhập Vercel CLI

```bash
npm install -g vercel
vercel login
vercel link --yes --project itms
```

Xác nhận `.vercel/project.json` có `"projectName":"itms"`.

#### 2. Kéo biến production

Chạy tại thư mục gốc:

```bash
vercel env pull .vercel/.env.production.local --environment=production --yes
```

Nếu CLI ghi `[SENSITIVE]` cho `DATABASE_URL_UNPOOLED`, không tự thay bằng URL
khác. Yêu cầu project owner cung cấp URL qua kênh bí mật hoặc chạy migration từ
môi trường CI/provider đã được cấp quyền.

Ưu tiên `DATABASE_URL_UNPOOLED` cho migration. URL do provider trả về có thể bắt
đầu bằng `postgresql://`; Alembic của dự án sử dụng psycopg 3 nên cần chuẩn hóa
thành `postgresql+psycopg://` trong process.

PowerShell:

```powershell
$line = Get-Content '.vercel\.env.production.local' |
  Where-Object { $_ -match '^DATABASE_URL_UNPOOLED=' } |
  Select-Object -First 1

$url = ($line -split '=', 2)[1].Trim('"')
$url = $url -replace '^postgres(ql)?://', 'postgresql+psycopg://'
$env:ITMS_DATABASE_URL = $url
```

Không dùng `Write-Output`, `echo` hoặc log giá trị `$url`.

#### 3. Kiểm tra tác động và backup

```powershell
cd backend
uv run alembic current
uv run alembic heads
```

Đọc toàn bộ migration còn thiếu trong `backend/migrations/versions/`. Nếu có
thao tác `DROP`, `DELETE`, gộp dữ liệu hoặc đổi trạng thái, phải:

1. đếm bản ghi bị ảnh hưởng bằng truy vấn chỉ đọc;
2. tạo backup/snapshot database;
3. được reviewer hoặc người phụ trách production xác nhận.

#### 4. Áp dụng migration

```powershell
uv run alembic upgrade head
uv run alembic current
```

Không đóng terminal khi migration chưa trả về exit code `0`. Revision sau cùng
phải trùng với `uv run alembic heads`.

#### 5. Deploy code

- Merge pull request vào `develop` sau khi CI xanh.
- Vercel Git Integration tự tạo deployment cho commit mới.
- Với migration chỉ mở rộng và tương thích ngược: migrate trước, deploy sau.
- Với thay đổi phá vỡ tương thích: tách thành **expand → deploy/backfill →
  contract**; không drop cột/bảng mà phiên bản đang chạy còn sử dụng.

#### 6. Kiểm tra hậu triển khai

```bash
curl -i https://itms-two.vercel.app/api/v1/health
curl -i https://itms-two.vercel.app/api/v1/health/db
vercel logs https://itms-two.vercel.app --since 10m --level error --no-follow
```

Ngoài health check, cần kiểm tra luồng:

1. đăng nhập;
2. gọi `/api/v1/me`;
3. refresh bằng cookie, không gửi Bearer token;
4. đăng xuất;
5. xác nhận access token cũ nhận `401`.

Không in access token, refresh cookie, database URL hoặc secret vào terminal/log.

### Xử lý sự cố schema lệch

Dấu hiệu thường gặp:

- frontend hiển thị “Không thể đăng nhập” nhưng `/health/db` vẫn trả `200`;
- API trả `500` ngay sau khi merge code có model mới;
- Vercel log có `UndefinedTable`, `UndefinedColumn` hoặc lỗi constraint.

Cách xử lý:

1. Dừng redeploy; build lại không sửa được schema.
2. Dùng đúng production DB và chạy `alembic current`.
3. So sánh với `alembic heads` trong commit đang deploy.
4. Review tác động dữ liệu và backup nếu cần.
5. Chạy `alembic upgrade head`.
6. Kiểm tra lại API và quét error logs.

Không dùng `alembic stamp head` để bỏ qua migration. `stamp` chỉ thay revision
metadata và không tạo bảng/cột thực tế.

## Kiểm tra chất lượng

Backend:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npm run format:check
npm run build
```

CI phải xanh trước khi merge, nhưng CI xanh không thay thế bước migration và
smoke test production.

## Quy trình Git

1. Cập nhật `develop` và tạo feature/fix branch.
2. Thực hiện thay đổi, migration và test tương ứng.
3. Chạy toàn bộ quality gates local.
4. Mở pull request về `develop` và chờ CI xanh.
5. Review tác động migration, backup và áp dụng đúng môi trường.
6. Merge, theo dõi Vercel deployment và chạy smoke test.

Không commit secret, token, file environment, dữ liệu upload hoặc dữ liệu test.

## Giấy phép

Dự án phục vụ mục đích học tập và quản lý nội bộ.
