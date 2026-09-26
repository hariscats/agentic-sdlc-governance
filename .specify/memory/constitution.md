# Governed Permit Intake Constitution

**Version**: 1.0.0 | **Authored**: 2026-09-26 | **Ratification**: pending independent review

## I. Security by default
Use parameterized SQL, allowlisted input categories, bounded printable descriptions,
and synthetic data. The sample is unauthenticated and binds to loopback only.
It must not be deployed as a real public service without authentication, authorization,
rate limiting, retention policy, and an explicit threat review.

## II. Test first
Specify behavior, write a failing test, implement, and converge. Unit and API tests
must cover negative cases. Coverage must reach 80% across application and governance.
Bootstrap test/code authored together is disclosed, not represented as proven TDD.

## III. Traceability
Source PRs reference spec:NNN and existing Txxx tasks. Task completion means observed
passing behavior, not necessarily human approval or merge. Track these states separately.

## IV. Least privilege
Workflow top-level permissions are contents: read or empty. Elevate only the job
that needs a permission. No cloud credentials, no PR-head execution with write tokens,
no pull_request_target checkout of untrusted code.

## V. Accessibility
The static dashboard uses semantic headings, text equivalents for SVG charts,
visible focus and sufficient contrast. Section 508 mapping is illustrative; independent
assistive-technology assessment remains required. No external browser calls.

## VI. Privacy
No PII in logs. Validation errors omit raw inputs. Hooks retain argument hashes,
not prompts or raw arguments. Never commit demo secrets; generate them at runtime.

## VII. Agent boundaries
Agents may implement approved source/tests/tasks but may not change governance,
workflows, hooks, scripts, dependency manifests, or this constitution. Instructions
are not a sandbox. Human review and server-side gates enforce the merge boundary.

## VIII. Human control and truthful evidence
No self-approval or gate bypass. Production requires independent approval and verified
provenance. Unsupported controls are BLOCKED, not PASS. Local simulation is labelled.

## Amendments
Amendments require architecture-owner approval via PR, a version bump, rationale,
and impact analysis. A solo owner cannot demonstrate independent approval.
