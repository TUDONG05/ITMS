# Quy ước đóng góp

## Nhánh

- `main`: nhánh tích hợp ổn định.
- `feat/<scope>`: tính năng mới, ví dụ `feat/auth-login`.
- `fix/<scope>`: sửa lỗi, ví dụ `fix/health-proxy`.
- `chore/<scope>`: tooling, tài liệu hoặc bảo trì, ví dụ `chore/format-config`.

Không làm việc trực tiếp trên `main`. Mỗi pull request nên nhỏ, có mô tả phạm vi và liên kết task Trello.

## Conventional Commits

Mẫu commit là `type(scope): mô tả ngắn`, ví dụ:

```text
feat(auth): add login endpoint
fix(frontend): handle unavailable backend
chore(tooling): configure lint rules
docs(srs): clarify task scope
```

Type dùng: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`.

## Trước khi tạo pull request

- Không đưa token, mật khẩu, khóa riêng hoặc cấu hình local vào source.
- Chạy lint, format và kiểm tra phù hợp với phần đã sửa.
- Giữ API dưới `/api/v1`; backend mới là nơi thực thi quyền.
- Không gộp công việc của S0-04/S0-10 vào S0-02.
