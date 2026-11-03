# Shared tasks with multiple interns

Status: complete

## Accepted behavior

- One create operation produces one task assigned to all selected internship members.
- Each intern can have multiple tasks; each task can have multiple interns.
- All assigned interns see the same task ID and its full assignee list.
- Internship filtering and multi-select remain on the same row.
- Existing tasks keep their IDs and submissions/comments, each remaining a separate task in GROUP mode.
- Unauthorized recipients reject the entire create operation.
- Creation offers two exclusive modes: GROUP (one shared submission/review) and INDIVIDUAL (each member's own submission/review).
- Individual task completion requires all assigned members to complete; accepted individual work is locked independently.
- Assigned interns see all assignee names but only their own submission/review in INDIVIDUAL mode.

## Implementation

- [x] Add and backfill the task/member association table; migrate backend consumers.
- [x] Submit the entire recipient array once and display assignees in list/detail for both roles.
- [x] Confirm shared versus individual submission/review behavior with the user: support both via a radio group.
- [x] Add assignment mode, individual submissions/statuses and targeted mentor review.
- [x] Verify migration, permissions, search/filtering, dashboard counts, and shared-task behavior.
- [x] Run frontend tests, lint, build and relevant backend tests; refresh local servers.

## Verification

- Backend: 200 tests passed; Ruff checks and formatting passed.
- Frontend: 52 tests passed; lint, formatting and production build passed (existing bundle size warning).
- Local migrations 0010/0011 preserved all 10 task IDs, 10 assignment pairs, 3 submission IDs and 6 comment IDs.
- Frontend, backend, database health and proxied task detail verified locally.

Historical tasks with similar text will not be automatically merged because they may have different submissions or reviews.
