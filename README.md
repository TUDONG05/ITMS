# ITMS

Nền tảng quản lý thực tập, khởi tạo ở Sprint 0 theo kiến trúc Angular Web Client và FastAPI Backend.

## Cấu trúc

```text
frontend/  Angular Web Client
backend/   FastAPI REST/JSON API
shared/    Contract và fixture dùng chung (không chia sẻ runtime TS/Python)
docs/      SRS, quyết định kiến trúc và kế hoạch
```

## Yêu cầu cài đặt

- Node.js 24 LTS và npm 11.
- Python 3.13 và `uv`.

## Chạy môi trường demo

Tạo cấu hình local từ mẫu, không commit tệp local này:

```bash
cp environment.local.example environment.local
set -a; source environment.local; set +a
```

Từ clone sạch, cài dependency với lockfile:

```bash
cd backend
uv sync --locked

cd ../frontend
npm ci
```

Mở hai terminal.

```bash
cd backend
uv run uvicorn app.main:app --reload
```

```bash
cd frontend
npm start
```

- Web client: `http://localhost:4200`
- Backend health: `http://localhost:8000/api/v1/health`
- Web client chuyển `/api/*` tới Backend qua `proxy.conf.json`.

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

## Ranh giới Sprint 0

S0-02 chỉ dựng source, môi trường và health probe. OpenAPI/DTO thuộc S0-04; xác thực, RBAC, database, migration và CI thuộc các task Sprint 0 tiếp theo. Quy ước API/RBAC đã chốt ở `docs/s0-01-api-access-control.md`.

Tiền tố API công khai là cố định: `/api/v1`.
