import os
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal["building", "event", "environmental"]
    description: str = Field(min_length=10, max_length=500)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10 or not value.isprintable():
            raise ValueError("Use 10-500 printable characters")
        return value


class Permit(Submission):
    id: UUID
    status: Literal["submitted"] = "submitted"
    created_at: datetime


def create_app(database: Path | None = None) -> FastAPI:
    db_path = database or Path(os.environ.get("PERMIT_DB", ".demo-state/permits.db"))

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS permits "
                "(id TEXT PRIMARY KEY, category TEXT NOT NULL, description TEXT NOT NULL, "
                "created_at TEXT NOT NULL)"
            )
            connection.commit()
        yield

    app = FastAPI(title="Governed Permit Intake (synthetic data only)", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not reflect raw input, exception context, or potential PII.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/permits", status_code=201, response_model=Permit)
    def submit(body: Submission) -> Permit:
        permit = Permit(**body.model_dump(), id=uuid4(), created_at=datetime.now(UTC))
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                "INSERT INTO permits VALUES (?, ?, ?, ?)",
                (
                    str(permit.id),
                    permit.category,
                    permit.description,
                    permit.created_at.isoformat(),
                ),
            )
            connection.commit()
        return permit

    @app.get("/permits/{permit_id}", response_model=Permit)
    def retrieve(permit_id: str) -> Permit:
        with closing(sqlite3.connect(db_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM permits WHERE id = ?", (permit_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Permit not found")
        return Permit.model_validate(dict(row))

    return app


app = create_app()
