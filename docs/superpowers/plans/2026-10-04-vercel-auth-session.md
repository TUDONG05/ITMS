# Kế hoạch triển khai phiên xác thực phù hợp với Vercel

> **Dành cho agent triển khai:** BẮT BUỘC dùng `superpowers:executing-plans` để thực hiện lần lượt từng task. Mỗi bước dùng checkbox (`- [ ]`) để theo dõi.

**Mục tiêu:** Xây dựng phiên xác thực lưu trong PostgreSQL, refresh token HttpOnly có xoay vòng và Angular interceptor tự phục hồi access token trên Vercel.

**Kiến trúc:** Backend phát access JWT 15 phút và refresh token dạng opaque được băm trong bảng `phien_dang_nhap`. Mọi API bảo vệ kiểm tra JWT, người dùng và phiên trong PostgreSQL; Angular chỉ giữ access token trong bộ nhớ, khôi phục phiên qua cookie và dùng interceptor single-flight để refresh/retry.

**Công nghệ:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL/SQLite test, pytest, Angular 22, RxJS 7, Angular HTTP functional interceptors.

**Đặc tả:** `docs/superpowers/specs/2026-10-04-vercel-auth-session-design.md`

## Ràng buộc toàn cục

- Access token mặc định sống 900 giây.
- Session refresh không ghi nhớ sống tối đa 43.200 giây và dùng session cookie.
- Session ghi nhớ sống tối đa 2.592.000 giây và dùng persistent cookie.
- Cookie là `HttpOnly`, `SameSite=Lax`, path `/api/v1/auth`; `Secure=true` trên production.
- Refresh token không xuất hiện trong JSON, log, `localStorage` hoặc `sessionStorage`.
- Bearer UUID luôn bị từ chối; `X-User-Id` chỉ được phép trong `development` và `test`.
- Không thay đổi dữ liệu nghiệp vụ hoặc vai trò người dùng.
- Mọi thay đổi hành vi phải theo RED–GREEN–REFACTOR.

## Trọng tâm rà soát

- Hai yêu cầu refresh đồng thời dùng cùng cookie: frontend phải single-flight, backend chỉ chấp nhận một lần xoay vòng.
- Cookie hợp lệ nhưng user bị khóa/xóa: phải thu hồi/từ chối mà không tiết lộ tài khoản tồn tại.
- Access JWT còn hạn nhưng session đã logout: API bảo vệ phải trả 401 ngay.
- Production nhận đồng thời JWT và `X-User-Id`: phải bỏ qua/từ chối header test, không cho ghi đè danh tính.
- Đổi mật khẩu từ một thiết bị: toàn bộ session của người dùng phải mất hiệu lực.

---

### Task 1: Mô hình phiên, cấu hình và primitive token

**Files:**
- Create: `backend/app/models/auth.py`
- Create: `backend/migrations/versions/0007_auth_sessions.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/core/settings.py`
- Modify: `backend/app/core/security.py`
- Modify: `environment.local.example`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `AuthSession`, `create_refresh_token(session_id) -> str`, `hash_refresh_token(token) -> str`, và các setting TTL/cookie.

- [ ] **Bước 1: Viết test thất bại cho refresh-token primitive và setting mặc định**

```python
def test_refresh_token_contains_session_id_and_only_hash_is_stable() -> None:
    session_id = uuid4()
    token = create_refresh_token(session_id)
    assert token.startswith(f"{session_id}.")
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert token != hash_refresh_token(token)

def test_refresh_settings_have_secure_defaults() -> None:
    settings = get_settings()
    assert settings.session_refresh_ttl_seconds == 43200
    assert settings.remembered_refresh_ttl_seconds == 2592000
    assert settings.refresh_cookie_name == "itms_refresh_token"
```

- [ ] **Bước 2: Chạy test và xác nhận RED**

Run: `cd backend; .venv/Scripts/python -m pytest tests/test_auth.py -k "refresh_token_contains or refresh_settings" -q`

Expected: FAIL vì các hàm/field chưa tồn tại.

- [ ] **Bước 3: Thêm model, migration, setting và primitive tối thiểu**

```python
def create_refresh_token(session_id: UUID) -> str:
    return f"{session_id}.{secrets.token_urlsafe(32)}"

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

Migration tạo `phien_dang_nhap` đúng schema trong spec, FK `ON DELETE CASCADE`, unique index cho `refresh_token_hash` và index cho `user_id`.

- [ ] **Bước 4: Chạy test mục tiêu và kiểm tra migration**

Run: `cd backend; .venv/Scripts/python -m pytest tests/test_auth.py -k "refresh_token_contains or refresh_settings" -q`

Expected: PASS.

Run: `cd backend; .venv/Scripts/alembic upgrade head`

Expected: database nâng lên revision `0007_auth_sessions`.

- [ ] **Bước 5: Commit**

```bash
git add backend/app/models/auth.py backend/app/models/__init__.py backend/app/core/settings.py backend/app/core/security.py backend/migrations/versions/0007_auth_sessions.py backend/tests/test_auth.py environment.local.example
git commit -m "feat(auth): add persistent session model"
```

### Task 2: Service quản lý vòng đời phiên bền vững

**Files:**
- Modify: `backend/app/auth/service.py`
- Modify: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `AuthSession`, `create_refresh_token`, `hash_refresh_token`, các TTL setting.
- Produces: `LoginResult(access_token, refresh_token, account, remember_me)`, `refresh_session`, `revoke_session`, `get_account_from_access_token`.

- [ ] **Bước 1: Viết test thất bại cho cold start và xoay vòng**

```python
def test_persisted_session_survives_service_recreation(db, settings, active_user):
    first = AuthService().login(db, active_user.email, "Intern@12345", settings, False)
    account = AuthService().get_account_from_access_token(db, first.access_token, settings)
    assert account.id == active_user.id

def test_refresh_rotates_token_and_rejects_reuse(db, settings, active_user):
    login = AuthService().login(db, active_user.email, "Intern@12345", settings, True)
    refreshed = AuthService().refresh(db, login.refresh_token, settings)
    assert refreshed.refresh_token != login.refresh_token
    with pytest.raises(ApiError) as error:
        AuthService().refresh(db, login.refresh_token, settings)
    assert error.value.code == "INVALID_REFRESH_TOKEN"
```

- [ ] **Bước 2: Chạy test và xác nhận RED**

Run: `cd backend; .venv/Scripts/python -m pytest tests/test_auth.py -k "persisted_session or rotates_token" -q`

Expected: FAIL vì service còn dùng `_active_sessions` trong RAM.

- [ ] **Bước 3: Triển khai tối thiểu session database**

Xóa `_active_sessions`. `login()` tạo `AuthSession`, `refresh()` khóa/truy vấn session, so sánh hash bằng `hmac.compare_digest`, kiểm tra thời hạn/trạng thái/user/token version, cập nhật hash mới và commit. `get_account_from_access_token()` tải session theo `sid` và từ chối phiên thu hồi/hết hạn.

- [ ] **Bước 4: Bổ sung test logout, nhiều thiết bị và đổi mật khẩu**

```python
def test_logout_revokes_only_current_session(db, settings, active_user):
    first = service.login(db, active_user.email, password, settings, False)
    second = service.login(db, active_user.email, password, settings, False)
    service.logout(db, first.refresh_token, None, settings)
    with pytest.raises(ApiError):
        service.get_account_from_access_token(db, first.access_token, settings)
    assert service.get_account_from_access_token(db, second.access_token, settings).id == active_user.id

def test_password_change_revokes_every_session(db, settings, active_user):
    first = service.login(db, active_user.email, password, settings, False)
    second = service.login(db, active_user.email, password, settings, True)
    service.change_password(db, active_user, password, "Changed@12345")
    for token in (first.access_token, second.access_token):
        with pytest.raises(ApiError):
            service.get_account_from_access_token(db, token, settings)
```

- [ ] **Bước 5: Chạy toàn bộ test service và xác nhận GREEN**

Run: `cd backend; .venv/Scripts/python -m pytest tests/test_auth.py -q`

Expected: PASS.

- [ ] **Bước 6: Commit**

```bash
git add backend/app/auth/service.py backend/tests/test_auth.py
git commit -m "feat(auth): persist and rotate login sessions"
```

### Task 3: Hợp đồng HTTP cookie và dependency xác thực thống nhất

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/v1/auth.py`
- Modify: `backend/app/core/deps.py`
- Modify: `backend/app/api/v1/me.py`
- Modify: `backend/app/api/v1/profile.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_auth.py`
- Test: `backend/tests/test_dashboard.py`

**Interfaces:**
- Produces: login/refresh/logout cookie contract; `get_current_user()` là dependency duy nhất trả `User`.

- [ ] **Bước 1: Viết API test thất bại cho cookie và refresh không cần bearer**

```python
def test_login_sets_httponly_cookie_and_refresh_rotates_it(client):
    login = client.post("/api/v1/auth/login", json={
        "email": "intern@itms.local", "password": "Intern@12345", "remember_me": False,
    })
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "Max-Age" not in login.headers["set-cookie"]
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != login.json()["access_token"]
```

- [ ] **Bước 2: Viết security test thất bại cho production override**

```python
def test_production_rejects_x_user_id_and_bearer_uuid(client, active_user, monkeypatch):
    monkeypatch.setenv("ITMS_ENVIRONMENT", "production")
    assert client.get("/api/v1/dashboard", headers={"X-User-Id": str(active_user.id)}).status_code == 401
    assert client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {active_user.id}"}).status_code == 401
```

- [ ] **Bước 3: Chạy test và xác nhận RED**

Run: `cd backend; .venv/Scripts/python -m pytest tests/test_auth.py tests/test_dashboard.py -k "httponly_cookie or production_rejects" -q`

Expected: FAIL vì refresh còn dùng bearer và production còn nhận UUID/header test.

- [ ] **Bước 4: Triển khai route và dependency tối thiểu**

Thêm `remember_me: bool = False` vào `LoginRequest`; đọc cookie qua `Cookie`, thiết lập/xóa cookie trên `Response`; thêm `Cache-Control: no-store`; chuyển `/me` và `/profile` sang `app.core.deps.get_current_user`; cấu hình `allow_credentials=True` cho CORS. `get_current_user` chỉ cho `X-User-Id` ngoài production và luôn yêu cầu JWT cho Bearer.

- [ ] **Bước 5: Chạy test mục tiêu và toàn bộ test backend**

Run: `cd backend; .venv/Scripts/python -m pytest tests/test_auth.py tests/test_dashboard.py -q`

Expected: PASS.

Run: `cd backend; .venv/Scripts/python -m pytest -q`

Expected: PASS; mọi fixture dùng `X-User-Id` phải đặt `ITMS_ENVIRONMENT=test`.

- [ ] **Bước 6: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/v1/auth.py backend/app/core/deps.py backend/app/api/v1/me.py backend/app/api/v1/profile.py backend/app/main.py backend/tests
git commit -m "fix(auth): unify protected API authentication"
```

### Task 4: AuthService Angular, bootstrap và interceptor single-flight

**Files:**
- Create: `frontend/src/app/core/auth/auth.interceptor.ts`
- Create: `frontend/src/app/core/auth/auth.interceptor.spec.ts`
- Create: `frontend/src/app/core/api/auth.service.spec.ts`
- Create: `frontend/tsconfig.spec.json`
- Modify: `frontend/src/app/core/api/auth.service.ts`
- Modify: `frontend/src/app/app.config.ts`
- Modify: `frontend/angular.json`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- Produces: `AuthService.accessToken`, `initialize()`, `refreshSession()`, `authInterceptor`.

- [ ] **Bước 1: Cấu hình Vitest chính thức của Angular và viết test RED cho state trong bộ nhớ**

Chạy `npm install --save-dev vitest jsdom`. Thêm target `test` dùng builder `@angular/build:unit-test` vào `angular.json`, thêm `tsconfig.spec.json` với type `vitest/globals`, và thêm script `"test": "ng test --watch=false"`. Test xác nhận `storeSession()` không ghi `itms_access_token`/`itms_authenticated_user` vào web storage và login gửi `remember_me`.

- [ ] **Bước 2: Viết test RED cho interceptor single-flight**

```typescript
it('shares one refresh request across concurrent 401 responses', () => {
  service.setAccessToken('expired');
  http.get('/api/v1/dashboard').subscribe();
  http.get('/api/v1/profile').subscribe();
  httpMock.expectOne('/api/v1/dashboard').flush({}, { status: 401, statusText: 'Unauthorized' });
  httpMock.expectOne('/api/v1/profile').flush({}, { status: 401, statusText: 'Unauthorized' });
  expect(httpMock.match('/api/v1/auth/refresh').length).toBe(1);
});
```

- [ ] **Bước 3: Chạy test và xác nhận RED**

Run: `cd frontend; npm test -- --include src/app/core/api/auth.service.spec.ts --include src/app/core/auth/auth.interceptor.spec.ts`

Expected: FAIL vì initializer/interceptor chưa tồn tại và token còn lưu sessionStorage.

- [ ] **Bước 4: Triển khai AuthService và interceptor tối thiểu**

`AuthService` giữ token/user bằng signal, gọi refresh với `withCredentials: true`, dùng một Observable `shareReplay(1)` trong thời gian refresh. Interceptor bỏ qua endpoint auth công khai, gắn Bearer, retry đúng một lần và chuyển login khi refresh thất bại. Đăng ký bằng `provideHttpClient(withInterceptors([authInterceptor]))` và `provideAppInitializer(() => inject(AuthService).initialize())`.

- [ ] **Bước 5: Chạy test mục tiêu và xác nhận GREEN**

Run: `cd frontend; npm test -- --include src/app/core/api/auth.service.spec.ts --include src/app/core/auth/auth.interceptor.spec.ts`

Expected: PASS.

- [ ] **Bước 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/angular.json frontend/tsconfig.spec.json frontend/src/app/app.config.ts frontend/src/app/core/api/auth.service.ts frontend/src/app/core/api/auth.service.spec.ts frontend/src/app/core/auth/auth.interceptor.ts frontend/src/app/core/auth/auth.interceptor.spec.ts
git commit -m "feat(auth): refresh Angular sessions automatically"
```

### Task 5: Loại bỏ header thủ công và bảo vệ điều hướng bằng state thật

**Files:**
- Modify: `frontend/src/app/core/guards/dashboard-role.guard.ts`
- Modify: `frontend/src/app/features/auth/login.component.ts`
- Modify: `frontend/src/app/features/dashboard/dashboard-shell.component.ts`
- Modify: `frontend/src/app/features/profile/profile.component.ts`
- Modify: `frontend/src/app/core/api/dashboard.service.ts`
- Modify: `frontend/src/app/core/api/internship.service.ts`
- Modify: `frontend/src/app/core/api/mentor.service.ts`
- Modify: `frontend/src/app/core/api/task.service.ts`
- Modify: `frontend/src/app/core/api/training.service.ts`
- Modify: `frontend/src/app/core/api/user-management.service.ts`
- Test: `frontend/src/app/core/guards/dashboard-role.guard.spec.ts`

**Interfaces:**
- Consumes: interceptor tự gắn Authorization; `AuthService.currentUser` đã được initializer khôi phục.

- [ ] **Bước 1: Viết guard test RED**

Test ba trường hợp: không có `currentUser` thì về `/login`; role khớp thì cho phép; role không khớp thì về `/login`. Test không thiết lập `sessionStorage`.

- [ ] **Bước 2: Chạy test và xác nhận RED**

Run: `cd frontend; npm test -- --include src/app/core/guards/dashboard-role.guard.spec.ts`

Expected: FAIL vì guard còn đọc `sessionStorage`.

- [ ] **Bước 3: Chuyển UI/guard sang AuthService và bỏ header thủ công**

Guard inject `AuthService`; login gửi `remember_me: rememberMe`; các API service bỏ `HttpHeaders`, `getHeaders()` và mọi truy cập `sessionStorage`. Dashboard/profile ánh xạ 401 thành thông báo hết phiên, 403 thành thiếu quyền và 5xx thành lỗi máy chủ.

- [ ] **Bước 4: Chạy test, lint và build**

Run: `cd frontend; npm test`

Expected: PASS.

Run: `cd frontend; npm run lint`

Expected: PASS.

Run: `cd frontend; npm run build`

Expected: PASS.

- [ ] **Bước 5: Commit**

```bash
git add frontend/src/app
git commit -m "fix(auth): remove stale browser authentication state"
```

### Task 6: Kiểm chứng hợp đồng và hoàn thiện tài liệu vận hành

**Files:**
- Modify: `README.md`
- Modify: `environment.local.example`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: toàn bộ luồng login → protected API → refresh → logout.

- [ ] **Bước 1: Chạy toàn bộ backend suite trong môi trường test**

Run: `cd backend; $env:ITMS_ENVIRONMENT='test'; .venv/Scripts/python -m pytest -q`

Expected: PASS, không tạo dữ liệu test tồn dư.

- [ ] **Bước 2: Chạy toàn bộ frontend quality gate**

Run: `cd frontend; npm test; npm run lint; npm run build; npm run format:check`

Expected: tất cả PASS.

- [ ] **Bước 3: Kiểm tra API contract cục bộ**

Khởi động backend với database đã migrate. Gửi login có `remember_me=false`, xác nhận `Set-Cookie` không có `Max-Age`; gọi `/me`; gọi `/auth/refresh` không có bearer; xác nhận cookie thay đổi; gọi logout; xác nhận access token cũ nhận 401. Không in giá trị token vào terminal.

- [ ] **Bước 4: Cập nhật README**

Ghi rõ biến môi trường mới, cookie policy, migration bắt buộc trước deploy và việc phiên cũ phải đăng nhập lại một lần.

- [ ] **Bước 5: Commit hoàn thiện**

```bash
git add README.md environment.local.example backend/tests/test_auth.py
git commit -m "docs(auth): document persistent session rollout"
```

- [ ] **Bước 6: Rà soát nhánh**

Run: `git diff --check develop...HEAD`

Expected: không có lỗi whitespace.

Run: `git status --short`

Expected: chỉ còn các file chưa theo dõi có sẵn từ trước, không có thay đổi auth chưa commit.
