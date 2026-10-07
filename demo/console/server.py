"""Live demo console: FastAPI and server-sent events on http://127.0.0.1:8001.

    make demo    # same as: uv run --frozen python -m demo.console.server

Every event comes from .agent-audit/session.jsonl (real hook decisions) or
demo/events.jsonl (real test, gate and verification steps). /try never executes.
"""

import argparse
import asyncio
import json
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from demo import run
from guardrails import policy

HOST, PORT = "127.0.0.1", 8001
ALLOWED_HOSTS = {f"{HOST}:{PORT}", f"localhost:{PORT}"}
INDEX = Path(__file__).with_name("index.html")
SCENES = {1: "1", 2: "2", 3: "3"}
CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
Offsets = dict[str, tuple[int, int]]


class Attempt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = Field(min_length=1, max_length=500)


class Verification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tampered: bool = False


class LocalOnly:
    """Refuse other Host headers (DNS rebinding) and non-JSON POSTs (cross-site forms)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            media = headers.get("content-type", "").split(";")[0].strip().lower()
            refusal = None
            if headers.get("host") not in ALLOWED_HOSTS:
                refusal = JSONResponse({"detail": "Unknown host"}, status_code=403)
            elif scope["method"] == "POST" and media != "application/json":
                refusal = JSONResponse({"detail": "Send JSON"}, status_code=415)
            if refusal is not None:
                await refusal(scope, receive, send)
                return
        await self.app(scope, receive, send)


def sources(root: Path) -> dict[str, Path]:
    return {
        "audit": root / ".agent-audit" / "session.jsonl",
        "demo": root / "demo" / "events.jsonl",
    }


def positions(files: dict[str, Path]) -> Offsets:
    """(inode, size) of each file now, so a stream replays only this session."""
    result: Offsets = {}
    for source, path in files.items():
        try:
            stat = path.stat()
        except FileNotFoundError:
            result[source] = (0, 0)
        else:
            result[source] = (stat.st_ino, stat.st_size)
    return result


def poll(files: dict[str, Path], offsets: Offsets) -> list[dict[str, Any]]:
    """Return complete new JSON lines from each file and advance the offsets in place."""
    events: list[dict[str, Any]] = []
    for source, path in files.items():
        inode, position = offsets[source]
        try:
            stat = path.stat()
            if stat.st_ino != inode or stat.st_size < position:
                inode, position = stat.st_ino, 0  # replaced or truncated by `make reset`
            with path.open("rb") as stream:
                stream.seek(position)
                chunk = stream.read()
        except FileNotFoundError:
            offsets[source] = (0, 0)
            continue
        complete, newline, _ = chunk.rpartition(b"\n")
        if newline:
            position += len(complete) + 1
            for line in complete.split(b"\n"):
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict):
                    events.append({"source": source, **record})
        offsets[source] = (inode, position)
    return events


async def stream(
    files: dict[str, Path], offsets: Offsets, interval: float = 0.25, heartbeat: float = 15
) -> AsyncIterator[str]:
    quiet = 0.0
    while True:
        batch = poll(files, offsets)
        for record in batch:
            yield f"data: {json.dumps(record)}\n\n"
        quiet = 0.0 if batch else quiet + interval
        if quiet >= heartbeat:
            quiet = 0.0
            yield ": keep-alive\n\n"
        await asyncio.sleep(interval)


def create_app(root: Path = run.ROOT) -> FastAPI:
    files = sources(root)
    start = positions(files)
    scenes: dict[str, subprocess.Popen[bytes]] = {}
    app = FastAPI(title="Guardrails console", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(LocalOnly)

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        headers = {"Content-Security-Policy": CSP, "Cache-Control": "no-store"}
        return HTMLResponse(INDEX.read_text(), headers=headers)

    @app.get("/events")
    def events() -> StreamingResponse:
        return StreamingResponse(
            stream(files, dict(start)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/try")
    def attempt(body: Attempt) -> dict[str, str]:
        decision = policy.evaluate("bash", {"command": body.command}, root)
        return {"decision": decision.decision, "reason": decision.reason, "target": decision.target}

    @app.post("/scene/{number}")
    def scene(number: int) -> dict[str, int]:
        if number not in SCENES:
            raise HTTPException(status_code=404, detail="Unknown scene")
        running = scenes.get("current")
        if running is not None and running.poll() is None:
            raise HTTPException(status_code=409, detail="A scene is already running")
        command = [sys.executable, "-m", "demo.run", "--scene", SCENES[number], "--pace", "2"]
        scenes["current"] = subprocess.Popen(command, cwd=root)
        return {"scene": number}

    @app.post("/verify")
    def verify(body: Verification) -> dict[str, str]:
        return run.verify_step(body.tampered, root)

    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Live guardrails console")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)
    url = f"http://{HOST}:{PORT}/"
    server = uvicorn.Server(uvicorn.Config(create_app(), host=HOST, port=PORT, log_level="warning"))

    def open_when_ready() -> None:
        while not server.started and not server.should_exit:
            time.sleep(0.1)
        if server.started:
            webbrowser.open(url)

    if not args.no_browser:
        threading.Thread(target=open_when_ready, daemon=True).start()
    print(f"Guardrails console on {url} (Ctrl+C to stop)", flush=True)
    server.run()


if __name__ == "__main__":
    main()
