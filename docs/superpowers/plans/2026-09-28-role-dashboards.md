# Role-based Dashboards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver live, authenticated dashboards for Admin, Mentor, and Intern.

**Architecture:** FastAPI derives the role and membership scope from `current_user` and returns compact aggregates. The Angular shell consumes this response and replaces its demo cards, rows, and chart totals with real role-scoped content.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Pydantic, pytest; Angular 22, TypeScript, RxJS, ng-zorro-antd.

**Spec:** `docs/superpowers/specs/2026-09-28-role-dashboards-design.md`

## Global Constraints

- Role and data scope come only from `current_user`.
- `internship_id` is an Admin-only optional UUID filter.
- Valid empty accounts return zero metrics, null progress, and empty arrays.
- The dashboard must not disclose out-of-scope domain records.
- No cache, analytics store, reporting CRUD, chart package, or unrelated pages.

## Review Focus

- Other Interns' tasks cannot alter an Intern's counts or recent items.
- Another Mentor's Interns cannot appear in the current Mentor's aggregates.
- Unknown and malformed Admin internship filters return `404` and `422`.
- A user with no membership gets a successful empty response.
- HTTP failure clears old values and supplies a retry action.

---

## File Structure

- `backend/app/schemas/dashboard.py`: dashboard DTOs.
- `backend/app/services/dashboard.py`: aggregate queries, role scoping, response assembly.
- `backend/app/api/v1/dashboard.py`: authenticated endpoint.
- `backend/app/api/v1/router.py`: route registration.
- `backend/tests/test_dashboard.py`: API behavior and isolation tests.
- `frontend/src/app/core/api/dashboard.service.ts`: typed authenticated client.
- `frontend/src/app/features/dashboard/dashboard-shell.component.ts`: live overview UI.
- `frontend/src/styles.scss`: overview filter and state styles.

### Task 1: Dashboard DTO contract

**Files:** Create `backend/app/schemas/dashboard.py`; create `backend/tests/test_dashboard.py`.

**Interfaces:** `DashboardRead(role, metrics, task_breakdown, progress, recent_items)`; each metric has `key`, `label`, and `value`; task breakdown defaults all six statuses and overdue count to zero.

- [ ] **Step 1: Write the failing test.**

```python
def test_empty_intern_dashboard_schema_serializes() -> None:
    payload = DashboardRead(role=UserRole.INTERN, metrics=[DashboardMetricRead(key="assigned_tasks", label="Task được giao", value=0)], task_breakdown=DashboardTaskBreakdownRead(), progress=None, recent_items=[])
    assert payload.model_dump(mode="json")["role"] == "INTERN"
```

- [ ] **Step 2: Verify RED.** Run `cd backend; pytest tests/test_dashboard.py::test_empty_intern_dashboard_schema_serializes -q`; expect import failure for `app.schemas.dashboard`.
- [ ] **Step 3: Implement minimal models.** Define `DashboardMetricRead`, `DashboardTaskBreakdownRead(todo, in_progress, submitted, revision_required, completed, overdue)`, `DashboardProgressRead`, `DashboardRecentItemRead`, and `DashboardRead` using `BaseSchema` and `UserRole`.
- [ ] **Step 4: Verify GREEN.** Run the same pytest command; expect PASS.
- [ ] **Step 5: Commit.** Run `git add backend/app/schemas/dashboard.py backend/tests/test_dashboard.py; git commit -m "feat: define dashboard response contract"`.

### Task 2: Secured API aggregates

**Files:** Create `backend/app/services/dashboard.py`, `backend/app/api/v1/dashboard.py`; modify `backend/app/api/v1/router.py` and `backend/tests/test_dashboard.py`.

**Interfaces:** `DashboardService.build(db: Session, current_user: User, internship_id: UUID | None) -> DashboardRead`; `GET /api/v1/dashboard`.

- [ ] **Step 1: Write failing Admin tests.** Seed two internships with one task each; assert an Admin filtered request has `total_tasks == 1`, and an unknown UUID returns `404`.
- [ ] **Step 2: Verify RED.** Run `cd backend; pytest tests/test_dashboard.py -k admin_dashboard -q`; expect route-not-found failure.
- [ ] **Step 3: Implement Admin endpoint.** Add `APIRouter(prefix="/dashboard", tags=["dashboard"])` with `get_current_user` and optional `Query` UUID filter. Register router. First query matching membership IDs, validate a selected Admin internship, then use grouped SQL counts for task statuses, overdue open tasks, requests, quiz attempts, evaluations, learning progress, and a limited ordered recent-items query.
- [ ] **Step 4: Verify GREEN.** Run `cd backend; pytest tests/test_dashboard.py -k admin_dashboard -q`; expect PASS.
- [ ] **Step 5: Write failing scope tests.** Seed two Mentors and two Interns. Assert each Mentor gets one assigned Intern/cohort task and each Intern gets only their titled task; test zero-data response and a non-Admin filter returning `403`.
- [ ] **Step 6: Verify RED.** Run `cd backend; pytest tests/test_dashboard.py -k "mentor_dashboard or intern_dashboard or empty_dashboard" -q`; expect scope/metric failures.
- [ ] **Step 7: Implement scopes.** For Mentor select `InternshipMember.id` by `mentor_id`; for Intern select by `intern_id`; for Admin select all or selected internship members. Every task, progress, quiz, evaluation, request, and recent-items query must use that membership subquery. Return valid zero/empty DTOs when it yields no rows.
- [ ] **Step 8: Verify GREEN and commit.** Run `cd backend; pytest tests/test_dashboard.py -q`; expect PASS. Then run `git add backend/app/api/v1/dashboard.py backend/app/api/v1/router.py backend/app/services/dashboard.py backend/tests/test_dashboard.py; git commit -m "feat: add role scoped dashboard API"`.

### Task 3: Typed Angular client

**Files:** Create `frontend/src/app/core/api/dashboard.service.ts`; modify `frontend/src/app/features/dashboard/dashboard-shell.component.ts`.

**Interfaces:** `DashboardService.getDashboard(internshipId?: string): Observable<DashboardRead>` with interfaces exactly matching Task 1.

- [ ] **Step 1: Write failing compile use.** Import and inject `DashboardService`, declare `overview = signal<DashboardRead | null>(null)`, and call `this.dashboardService.getDashboard().subscribe(data => this.overview.set(data))`.
- [ ] **Step 2: Verify RED.** Run `cd frontend; npm run build`; expect missing service/type errors.
- [ ] **Step 3: Implement client.** Use `HttpParams` only when an ID is supplied; send the existing bearer token in a private `getHeaders()` method, then call `GET /api/v1/dashboard`.
- [ ] **Step 4: Verify GREEN and commit.** Run `cd frontend; npm run build`; expect PASS. Then run `git add frontend/src/app/core/api/dashboard.service.ts frontend/src/app/features/dashboard/dashboard-shell.component.ts; git commit -m "feat: add dashboard API client"`.

### Task 4: Live role-aware overview

**Files:** Modify `frontend/src/app/features/dashboard/dashboard-shell.component.ts` and `frontend/src/styles.scss`.

**Interfaces:** consumes `DashboardRead`, `DashboardService`, `InternshipService`; renders metric cards, task breakdown, recent items, progress, Admin filter, loading/empty/error states.

- [ ] **Step 1: Write failing compile assertion.** Reference `overview()?.metrics` in the overview template before defining `overview`, `isDashboardLoading`, and `dashboardError` signals.
- [ ] **Step 2: Verify RED.** Run `cd frontend; npm run build`; expect missing property failure.
- [ ] **Step 3: Implement minimal UI.** Implement `loadDashboard(internshipId?)`: set loading, clear error, call client; on success set response; on error clear response and set Vietnamese retry text. Call after route role resolution. Remove all hard-coded data values. Use an Admin-only select populated by `InternshipService.getInternships()`, reloading on selection. Render loading, retry, empty list copy, metrics, status counts, latest items, and progress using existing ng-zorro components; add responsive styles only for new filter/state elements.
- [ ] **Step 4: Verify GREEN.** Run `cd frontend; npm run build`; expect PASS.
- [ ] **Step 5: Full verification and commit.** Run `cd backend; pytest -q`, then `cd ../frontend; npm run build`, then `git diff develop...HEAD --check`. Expect all checks PASS/no whitespace errors. Commit with `git add frontend/src/app/features/dashboard/dashboard-shell.component.ts frontend/src/styles.scss; git commit -m "feat: render role based dashboard overview"`.
