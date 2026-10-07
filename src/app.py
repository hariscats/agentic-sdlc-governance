"""Permit intake API for spec:001, on the standard library only.

    python3 -m src.app            # http://127.0.0.1:8000, loopback only

POST /permits submits a fictional permit, GET /permits/{id} retrieves it, GET /health
reports ok. Request values are SQL parameters, never SQL syntax, and validation
errors never echo the submitted input.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import closing
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

CATEGORIES = ("building", "event", "environmental")
FIELDS = ("category", "description")
MAX_BODY = 64 * 1024


class Invalid(ValueError):
    """Validation errors as (location, type) pairs; the input itself is never included."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("Invalid request")
        self.errors = errors


def validate(body: Any) -> dict[str, str]:
    if not isinstance(body, dict):
        raise Invalid([{"location": ["body"], "type": "object_type"}])
    errors = [
        {"location": ["body", name], "type": "extra_forbidden"}
        for name in sorted(set(body) - set(FIELDS), key=str)
    ]
    category = body.get("category")
    if "category" not in body:
        errors.append({"location": ["body", "category"], "type": "missing"})
    elif category not in CATEGORIES:
        errors.append({"location": ["body", "category"], "type": "literal_error"})
    description = body.get("description")
    if "description" not in body:
        errors.append({"location": ["body", "description"], "type": "missing"})
    elif not isinstance(description, str):
        errors.append({"location": ["body", "description"], "type": "string_type"})
    else:
        description = description.strip()
        if len(body["description"]) > 500 or len(description) < 10:
            errors.append({"location": ["body", "description"], "type": "string_length"})
        elif not description.isprintable():
            errors.append({"location": ["body", "description"], "type": "value_error"})
    if errors:
        raise Invalid(errors)
    return {"category": category, "description": description}


class PermitStore:
    """SQLite storage. Every operation opens and closes its own connection."""

    def __init__(self, database: Path) -> None:
        self.database = database
        database.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS permits "
                "(id TEXT PRIMARY KEY, category TEXT NOT NULL, description TEXT NOT NULL, "
                "created_at TEXT NOT NULL)"
            )
            connection.commit()

    def submit(self, submission: dict[str, str]) -> dict[str, str]:
        permit = {
            **submission,
            "id": str(uuid.uuid4()),
            "status": "submitted",
            "created_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        }
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "INSERT INTO permits VALUES (?, ?, ?, ?)",
                (permit["id"], permit["category"], permit["description"], permit["created_at"]),
            )
            connection.commit()
        return permit

    def retrieve(self, permit_id: str) -> dict[str, str] | None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM permits WHERE id = ?", (permit_id,)).fetchone()
        if row is None:
            return None
        return {**dict(row), "status": "submitted"}


def handler(store: PermitStore) -> type[BaseHTTPRequestHandler]:
    class PermitHandler(BaseHTTPRequestHandler):
        server_version = "permit-intake"
        sys_version = ""

        def log_message(self, format: str, *args: Any) -> None:
            """Never log requests: paths and bodies may carry submitted content."""

        def reply(self, status: int, payload: Any) -> None:
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/health":
                self.reply(HTTPStatus.OK, {"status": "ok"})
            elif path.startswith("/permits/") and path.count("/") == 2:
                permit = store.retrieve(unquote(path.removeprefix("/permits/")))
                if permit is None:
                    self.reply(HTTPStatus.NOT_FOUND, {"detail": "Permit not found"})
                else:
                    self.reply(HTTPStatus.OK, permit)
            else:
                self.reply(HTTPStatus.NOT_FOUND, {"detail": "Not Found"})

        def do_POST(self) -> None:
            if self.path.split("?", 1)[0] != "/permits":
                self.reply(HTTPStatus.NOT_FOUND, {"detail": "Not Found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 <= length <= MAX_BODY:
                self.reply(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"detail": "Body too large"})
                return
            try:
                body = json.loads(self.rfile.read(length) or b"null")
                submission = validate(body)
            except ValueError as error:
                errors = error.errors if isinstance(error, Invalid) else [
                    {"location": ["body"], "type": "json_invalid"}
                ]
                self.reply(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": errors})
                return
            self.reply(HTTPStatus.CREATED, store.submit(submission))

    return PermitHandler


def create_server(
    database: Path | None = None, host: str = "127.0.0.1", port: int = 8000
) -> ThreadingHTTPServer:
    path = database or Path(os.environ.get("PERMIT_DB", ".demo-state/permits.db"))
    server = ThreadingHTTPServer((host, port), handler(PermitStore(path)))
    server.daemon_threads = True
    return server


def serve_in_background(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    app = create_server()
    print("Permit intake on http://127.0.0.1:8000 (synthetic data only; Ctrl+C to stop)")
    try:
        app.serve_forever()
    except KeyboardInterrupt:
        pass
