# Clarifications

The user delegated placeholder choices. Defaults are explicit:
SQLite persistence; no PII fields; three allowlisted categories; no update/delete API;
missing and malformed lookup IDs return 404; invalid submissions return 422;
clock is UTC; concurrent writes use SQLite transactions; no production exposure.
These are demo design choices, not agency requirements.
