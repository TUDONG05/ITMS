# Vercel-Safe Authentication Sessions

**Date:** 2026-10-04
**Status:** Approved for implementation planning
**Branch:** `fix/vercel-auth-session`

## 1. Purpose

Replace the process-local authentication session registry with persistent,
database-backed sessions that remain valid across Vercel cold starts and
function instances. Add secure refresh-token rotation and make the Angular
client recover transparently when its short-lived access token expires.

The completed flow must:

- keep a signed-in user active across page reloads and Vercel instance changes;
- use a 15-minute access token and a refresh token that JavaScript cannot read;
- revoke one device session on logout and every session after a password change;
- reject test-only identity headers in production;
- prevent stale browser state from presenting an authenticated dashboard;
- preserve the existing user roles and authenticated API response shapes where
  compatibility is possible.

## 2. Scope

### In scope

- A new persistent authentication-session table and Alembic migration.
- Login, refresh, logout, password-change, and current-user authentication.
- One shared FastAPI authentication dependency for protected endpoints.
- Angular authentication bootstrap, in-memory access-token storage, route
  guarding, an HTTP interceptor, and explicit authentication errors.
- Backend and frontend regression tests for session lifecycle and retry logic.

### Out of scope

- OAuth or third-party identity providers.
- A user-facing screen for listing or remotely revoking devices.
- Changing user roles, password rules, or password-reset delivery.
- Moving authentication to an external identity service.
- Cross-domain frontend/API hosting; the current same-origin `/api` routing is
  retained.

## 3. Chosen Architecture

Authentication uses two credentials with different responsibilities:

1. A short-lived signed JWT access token authorizes normal API requests.
2. A high-entropy opaque refresh token identifies a persistent database
   session and is sent only as an HttpOnly cookie.

The database, not a Python process, is the source of truth for active sessions.
Every protected request validates the JWT and confirms that its session and user
are still active. This makes logout immediately effective while remaining safe
when Vercel routes consecutive requests to different function instances.

## 4. Data Model

Add model `AuthSession` mapped to table `phien_dang_nhap`:

| Column | Type | Rules |
| --- | --- | --- |
| `id` | UUID | Primary key; also used as JWT `sid` |
| `user_id` | UUID | FK to `nguoi_dung.id`, `ON DELETE CASCADE`, indexed |
| `refresh_token_hash` | String(64) | SHA-256 hexadecimal hash, unique and indexed |
| `remember_me` | Boolean | Determines persistent-cookie behavior |
| `expires_at` | Timestamp with timezone | Server-side refresh-session expiry |
| `last_used_at` | Timestamp with timezone | Updated after successful rotation |
| `revoked_at` | Timestamp with timezone, nullable | Non-null sessions are invalid |
| `created_at` | Timestamp with timezone | Creation time |

No existing data requires backfilling. Tokens issued before deployment have no
database session and will require one new login after rollout.

### Refresh-token representation

The browser receives `<session-uuid>.<secret>`, where `secret` contains at least
32 random bytes encoded with URL-safe Base64. Only `SHA-256(full-token)` is
stored. The UUID permits reuse detection: if the session exists but the hash no
longer matches after rotation, the session is revoked and the request is denied.

## 5. Token and Cookie Policy

### Access token

- Lifetime: `ITMS_ACCESS_TOKEN_TTL_SECONDS`, default 900 seconds.
- Claims: `sub`, `sid`, `tv`, `iat`, `exp`, `iss`, and `aud`.
- Stored only in Angular memory.
- Sent as `Authorization: Bearer <token>`.

### Refresh session

- Without â€œRemember meâ€: server expiry defaults to 12 hours and the cookie has
  no `Max-Age` or `Expires`, making it a browser-session cookie.
- With â€œRemember meâ€: server and cookie expiry default to 30 days.
- New settings:
  - `ITMS_SESSION_REFRESH_TTL_SECONDS=43200`
  - `ITMS_REMEMBERED_REFRESH_TTL_SECONDS=2592000`

### Cookie

- Name: `itms_refresh_token`.
- `HttpOnly=true`.
- `SameSite=Lax`.
- `Secure=true` in production and false for local HTTP development/tests.
- `Path=/api/v1/auth`.
- The server clears the cookie using the same path and attributes.

Browser session restoration can restore a session cookie in some browsers. The
12-hour server expiry therefore provides an independent upper bound.

## 6. API Contract

### `POST /api/v1/auth/login`

Request:

```json
{
  "email": "admin@itms.local",
  "password": "...",
  "remember_me": false
}
```

`remember_me` defaults to `false` for backward compatibility. A successful
response retains the existing `LoginResponse` body and also sets the refresh
cookie. Invalid credentials remain `401 INVALID_CREDENTIALS`.

### `POST /api/v1/auth/refresh`

- Requires the refresh cookie; no bearer token is required.
- Validates the session, user status, expiry, token hash, and `token_version`.
- Rotates the refresh secret in the same transaction.
- Returns the existing `LoginResponse` shape and replaces the cookie.
- Missing, expired, revoked, or reused credentials return
  `401 INVALID_REFRESH_TOKEN` and clear the cookie.

### `POST /api/v1/auth/logout`

- Idempotent.
- Revokes the session named by the refresh cookie.
- If the cookie is missing, a valid bearer token may identify the session.
- Always clears the cookie and returns the existing success message.

### `POST /api/v1/auth/change-password`

- Requires a valid access token and active session.
- Updates the password and increments `token_version`.
- Revokes every active session for the user.
- Clears the current refresh cookie.
- The user must sign in again.

### Protected API endpoints

All protected endpoints use one shared authentication dependency that:

1. requires a Bearer JWT;
2. validates signature, issuer, audience, and expiry;
3. loads the user and session from PostgreSQL;
4. checks user status, session status/expiry, session ownership, and
   `token_version`.

Bearer UUID credentials are removed in every environment. `X-User-Id` is
accepted only when `ITMS_ENVIRONMENT` is `development` or `test`; production
always rejects it.

## 7. Backend Components

- `app/models/auth.py`: `AuthSession` model.
- Alembic revision `0003_auth_sessions`: creates/drops the table and indexes.
- `app/core/settings.py`: refresh TTL and cookie settings.
- `app/core/security.py`: access-token and opaque refresh-token primitives.
- `app/auth/service.py`: persistent session creation, rotation, validation,
  revocation, and password-wide revocation.
- `app/api/v1/auth.py`: cookie transport and the revised endpoint contracts.
- `app/core/deps.py`: the single protected-resource dependency, delegating to
  the authentication service.

The service layer owns token and session policy. API routes only translate HTTP
headers/cookies and set or clear cookies.

## 8. Angular Components and Data Flow

### State

`AuthService` holds the access token and authenticated user in signals. It does
not persist the access token or trust a serialized user in web storage.

### Application bootstrap

A `provideAppInitializer` initializer calls `/auth/refresh` before protected
routing settles. Success restores the in-memory access token and user. A 401 is
treated as an anonymous session without presenting a global application error.

### HTTP interceptor

A functional interceptor:

- excludes login, refresh, forgot-password, and reset-password from bearer
  injection;
- attaches the in-memory access token to protected API requests;
- on the first `401`, enters a shared single-flight refresh operation;
- retries each queued request once with the new access token;
- never retries the refresh request itself;
- on refresh failure, clears authentication state and navigates to `/login`.

The single-flight rule prevents several simultaneous dashboard requests from
rotating the same refresh token concurrently.

### Routing and UI

- `dashboardRoleGuard` checks the initialized `currentUser` signal and role.
- Login forwards the checkbox value as `remember_me`.
- Logout calls the backend before clearing local state; local cleanup still
  occurs if the network request fails.
- Dashboard/profile distinguish `401`, `403`, connectivity, and server errors.

## 9. Error Handling and Security

- Authentication responses use the existing structured `ApiError` envelope.
- Refresh failures do not disclose whether a user or session exists.
- Refresh secrets never appear in JSON, logs, local storage, or session storage.
- Password changes revoke all sessions in one transaction.
- Refresh rotation is transactional so a successful response corresponds to
  exactly one current token hash.
- Production rejects identity override headers before resolving a user.
- Same-origin routing, `SameSite=Lax`, and POST-only refresh/logout limit CSRF;
  CORS remains restricted to configured origins.
- Login and refresh responses send `Cache-Control: no-store`.

## 10. Migration and Rollout

1. Apply Alembic migration `0003_auth_sessions` to the production database.
2. Deploy backend and frontend together because the refresh contract changes.
3. Existing sessions become invalid once; users sign in again.
4. Confirm production environment and cookie security settings.
5. Verify login, dashboard load, reload recovery, expiry refresh, logout, and
   password-change revocation on the production deployment.

No destructive data migration is required. Rollback drops only
`phien_dang_nhap`; existing users and business data remain unchanged.

## 11. Testing Strategy

### Backend

- Login creates a persisted session and correct cookie type.
- Remembered login uses a 30-day persistent cookie.
- Access JWT works from a new `AuthService` instance, simulating a Vercel cold
  start.
- Refresh rotates the secret and rejects reuse of the old token.
- Expired and revoked sessions return `INVALID_REFRESH_TOKEN`.
- Logout revokes only the current session.
- Password change revokes all user sessions and increments `token_version`.
- Deleted, locked, or inactive users cannot refresh or access resources.
- Production rejects `X-User-Id` and every Bearer UUID.
- Development/test permits `X-User-Id` only for test support.

### Frontend

- Bootstrap restores an authenticated user from the cookie flow.
- Login forwards `remember_me`.
- Interceptor attaches access tokens.
- One 401 triggers refresh and one retry.
- Concurrent 401 responses share one refresh request.
- Refresh failure clears state and redirects to login.
- Guard rejects absent and role-mismatched users.
- Logout clears local state even when its HTTP request fails.

### Full verification

- Run the complete backend pytest suite.
- Run Angular unit tests, lint, and production build.
- Exercise the API contract with login, refresh, protected request, and logout
  requests without exposing token values in output.

## 12. Acceptance Criteria

- A valid session survives process restart and Vercel instance changes.
- An expired access token refreshes without visible interruption.
- Closing a non-remembered browser session normally removes its refresh cookie;
  remembered sessions survive for at most 30 days.
- Logout and password change enforce the specified revocation behavior.
- No production endpoint authenticates a raw user UUID or `X-User-Id`.
- The Angular application never displays a protected dashboard solely from stale
  browser storage.
- All new and existing automated tests pass.
