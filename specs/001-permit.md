# spec:001: submit and retrieve a fictional permit

The demo's only feature. A PR that changes `src/` must cite `spec:001` in its title or body.

## Requirements

- FR-001: `POST /permits` accepts the category `building`, `event` or `environmental`.
- FR-002: The description is trimmed and must be 10-500 printable characters. Unknown fields are rejected.
- FR-003: A successful submission returns 201 with a UUID, a UTC timestamp and the status `submitted`.
- FR-004: `GET /permits/{id}` returns the stored permit. Unknown IDs return 404.
- FR-005: Permits persist across restarts. SQL inputs are parameters and cannot change query structure.
- FR-006: Invalid input returns 422 without echoing it back. Request bodies are never logged.
- FR-007: `GET /health` returns `{"status": "ok"}`.

## Boundaries

Loopback-only and unauthenticated. Synthetic descriptions only: no names, contact details or real data.
