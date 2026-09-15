# S0-02 — Khởi tạo source, môi trường mẫu và quy ước phát triển

## Mục tiêu

Tạo bộ khung chạy được cho Angular Web Client, FastAPI Backend và vùng tài nguyên dùng chung; bổ sung cấu hình môi trường mẫu, lint/format, tài liệu chạy demo và quy ước Git. Không triển khai API nghiệp vụ, migration, RBAC hay xác thực.

## Căn cứ

- SRS §2.1–2.2, dòng 83–100: kiến trúc web client–server, UI tiếng Việt, browser/Docker/server.
- SRS §7.2, NFR-03, NFR-04, NFR-07, dòng 734–742: bảo mật, không lộ secret, README/config mẫu/kiểm thử workflow.
- SRS §8.1, dòng 746–754: REST/JSON qua HTTPS khi triển khai và Backend là nơi kiểm soát quyền.
- `docs/s0-01-api-access-control.md` §3, §5: tiền tố `/api/v1`; UI không thay thế kiểm soát quyền Backend.

## Quyết định bootstrap

- `frontend/`: Angular standalone, strict, SCSS, routing; npm dùng lockfile. Chỉ có màn hình chào/kiểm tra health cục bộ, không UI kit, auth hoặc business feature.
- `backend/`: FastAPI + `uv`; một route probe `GET /api/v1/health`, cấu hình từ biến môi trường và CORS origin local. Không kết nối DB, không JWT/RBAC, không endpoint nghiệp vụ.
- `shared/`: chỉ tài liệu contract, fixtures và boundary; không cố chia sẻ mã runtime TypeScript/Python. S0-04 sẽ đặt OpenAPI/DTO làm nguồn API chính thức.
- Root: ignore, editorconfig, mẫu biến môi trường, quy ước Prettier, README và CONTRIBUTING. Môi trường local dùng proxy Angular đến FastAPI; HTTPS là cấu hình khi deploy.

## Phase 1 — Nền tảng root

- [x] Thêm ignore, editorconfig, Prettier root và mẫu biến môi trường không có secret.
- [x] Viết README hướng dẫn cài đặt/chạy hai dịch vụ, các URL local, lệnh kiểm tra và ranh giới S0-02.
- [x] Viết CONTRIBUTING: nhánh `feat/<scope>`, `fix/<scope>`, `chore/<scope>`; Conventional Commits; PR checklist.

## Phase 2 — Backend skeleton

- [x] Khởi tạo cấu hình dependency, lockfile, cấu trúc `app/` và kiểm thử.
- [x] Tạo settings an toàn, router `/api/v1` và health endpoint JSON.
- [x] Cấu hình Ruff (lint/format) và pytest; kiểm tra health endpoint.

## Phase 3 — Frontend skeleton

- [x] Khởi tạo Angular trong `frontend/` với strict/standalone/routing/SCSS và lockfile npm.
- [x] Thêm proxy `/api` đến FastAPI và một trang shell tối thiểu kiểm tra trạng thái backend.
- [x] Cấu hình ESLint, Prettier, compile và scripts kiểm tra; môi trường mẫu không chứa secret.

## Phase 4 — Shared và nghiệm thu

- [x] Tạo `shared/contracts` và `shared/fixtures` cùng tài liệu phạm vi/versioning.
- [x] Xác minh lint/format/kiểm thử/compile cho hai ứng dụng; gọi health trực tiếp và qua proxy local.
- [x] Xem lại secret/artefact bị ignore và README có tái tạo được môi trường từ clone sạch.

## Tiêu chí nghiệm thu

- [x] Hai ứng dụng cài dependency bằng lockfile và chạy độc lập.
- [x] `GET /api/v1/health` trả JSON; frontend gọi được qua proxy khi chạy local.
- [x] Lint, format-check, kiểm thử và compile đều thành công.
- [x] Không theo dõi tệp biến môi trường thật, token, key, cache hay artefact máy cục bộ.
- [x] README và CONTRIBUTING nêu đủ cách chạy demo, quy ước nhánh và Conventional Commits.
