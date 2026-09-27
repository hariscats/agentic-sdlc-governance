# Feature 001: submit and retrieve a permit

Status: implementation available; independent approval and merge pending.

## User story
As a demo applicant, I submit a fictional permit and retrieve its assigned ID/status.

## Acceptance requirements
- FR-001: POST /permits accepts category building, event, or environmental.
- FR-002: Description is trimmed, 10-500 printable characters; unknown fields are rejected.
- FR-003: A successful submission returns 201 with UUID, UTC timestamp, and submitted status.
- FR-004: GET /permits/{id} returns the stored object; absent IDs return 404.
- FR-005: Records persist across app restarts. SQL inputs cannot change query structure.
- FR-006: Validation returns 422 without reflecting input; no request body logging.
- FR-007: /health returns status ok. No decision endpoint exists during setup.

## Success criteria
All acceptance tests pass, application/governance coverage >=80%, no SQL interpolation,
and corresponding spec/task references are checked on source PRs.

## Boundaries
Localhost-only demo, synthetic descriptions, no applicant names or contact information.
Authentication and a production deployment are not part of Feature 001.
