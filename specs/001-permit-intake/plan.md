# Plan

Python 3.12, FastAPI/Pydantic schemas, SQLite with parameterized statements.
One application factory accepts a database path for test isolation.
Lifespan creates the schema; each operation closes its connection.
Use a generic validation error handler with no input echo.
Map FR-001..007 to tests/test_app.py and task IDs below.
