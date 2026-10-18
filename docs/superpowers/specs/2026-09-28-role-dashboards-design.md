# Role-based Dashboards Design

## Goal

Replace the dashboard's hard-coded overview with live, role-scoped operational data for Admin, Mentor, and Intern. Each authenticated user sees only the aggregate data and recent work they are authorized to view.

## Scope

- A single authenticated `GET /api/v1/dashboard` endpoint returns the caller's dashboard model. The server derives scope from `current_user.role`; the client never sends or selects a role.
- The response has a shared envelope: `role`, `metrics`, `task_breakdown`, `recent_items`, and `progress`. It contains only fields displayed by the dashboard, not full domain records.
- Admin receives system-wide figures and can optionally filter by an existing internship (`internship_id`). The filter is rejected for Mentor and Intern to avoid an ambiguous or privilege-escalating UI.
- Mentor receives data only for internship members whose `mentor_id` is the caller. Intern receives data only for members whose `intern_id` is the caller.
- The frontend keeps the existing dashboard route and shell, but uses a dashboard API service, renders real cards/panels, and supports loading, empty, and recoverable-error states.
- Existing navigation remains intact; dashboard links point to the matching existing or placeholder section without inventing unrelated CRUD views.

## Role content

### Admin

Metrics: active Interns, active Mentors, open/ongoing internships, pending internship requests, total task count, and published evaluation count. The task breakdown covers `TODO`, `IN_PROGRESS`, `SUBMITTED`, `REVISION_REQUIRED`, `COMPLETED`, and overdue open tasks. Recent items are the most recently created internships and the most urgent open tasks.

### Mentor

Metrics: Interns assigned to the mentor, active assignments, tasks in the mentor's cohort, submitted tasks awaiting review, and evaluations needing attention. The task breakdown and recent list contain only the mentor's assigned Interns; the list prioritizes submissions and overdue tasks. Progress is the average roadmap-item completion for that cohort, or `null` when no tracked learning items exist.

### Intern

Metrics: the caller's active internship membership, assigned tasks, tasks in progress, submitted/revision-required tasks, completed quizzes versus available quizzes, and the latest published evaluation score. The recent list contains the caller's nearest-deadline tasks. Progress is completed learning items divided by assigned learning items, or `null` when no roadmap is assigned.

## Backend design

- Add `app/api/v1/dashboard.py`, `app/schemas/dashboard.py`, and a narrowly scoped aggregation service. Register the router in `app/api/v1/router.py`.
- Use the existing FastAPI `get_current_user` dependency. Query membership IDs first, then use those IDs to scope tasks, quiz attempts, evaluations, roadmap progress, and requests. Admin may query globally or by an internship's member IDs.
- Return zero counts and empty lists where data does not exist. Do not fail a dashboard merely because a user has no active membership, mentor assignment, roadmap, quiz attempt, or evaluation.
- Validate an Admin `internship_id` as a UUID and return `404` for a valid-but-missing internship. Do not expose membership, task, quiz, or evaluation identifiers outside the permitted scope.
- Keep aggregation query count bounded by using grouped counts and a small, ordered recent-items query rather than loading each member's records in Python.

## Frontend design

- Add `DashboardService` and typed response interfaces under `frontend/src/app/core/api/`.
- Refactor `DashboardShellComponent` to load the overview on initialization and when the role route changes. Remove the static metric/row/chart content that represents dashboard data; retain static labels and navigation metadata.
- Render metric cards from server-provided labels/counts, a task-status breakdown, a role-appropriate recent-items panel, and a progress panel. Admin gets an internship filter populated from the existing internship service; Mentor and Intern do not render this control.
- Render a skeleton/spinner while loading, a clear retry action on API failure, and zero-state copy for empty datasets. Do not substitute demo numbers after a failed request.
- The route guard remains a client-side navigation safeguard. API authorization remains the security boundary.

## Error handling and security

- Missing/invalid authentication continues to return `401`; inactive users are denied by the existing dependency.
- The endpoint must return `403` only for deliberately forbidden role/filter combinations; normal zero-data accounts return `200` with empty/zero values.
- Role filtering must be proven with tests using records that belong to a different Mentor and Intern, so aggregate counts cannot leak through joins or unfiltered global queries.

## Tests and verification

- Backend API tests cover Admin global metrics, Admin internship filter, Mentor isolation, Intern isolation, zero-data response, and invalid/unknown internship filters.
- Frontend tests, if the repository test setup supports them, cover data-driven rendering and error/retry behavior. The mandatory frontend verification is a production Angular build.
- Run the full backend pytest suite and frontend `npm run build` before completion.

## Non-goals

- No new analytics database, caching layer, exports, charts library, reporting CRUD, or changes to domain permissions outside dashboard aggregation.
- No attempt to implement the navigation targets whose own use cases are not yet built.
