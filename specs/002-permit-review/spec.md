# Feature 002: reviewer decision and audit trail

Status: specified only; live-demo implementation must not be present at setup.

## User story
As a demo reviewer, I approve or deny a submitted fictional permit and can see the decision history.

## Acceptance requirements
- FR-201: POST /permits/{id}/decision accepts approved or denied and a 10-500 character reason.
- FR-202: Missing permit is 404; invalid payload is 422; a second decision is 409.
- FR-203: Status update and append-only decision event are committed atomically.
- FR-204: GET /permits/{id}/history returns ordered event IDs, timestamps and decision.
- FR-205: Invalid or conflicting requests must not create audit events.
- FR-206: Tests cover both decisions, rollback, conflicting updates, and privacy.

## Security boundary
This remains a loopback-only simulation. A caller-provided reviewer identity is not
authentication. A real reviewer authorization scheme is deliberately excluded from
the live task and requires security review before any external deployment.
