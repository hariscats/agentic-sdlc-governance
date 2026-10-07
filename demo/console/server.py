"""Live demo console on http://127.0.0.1:8001, standard library only.

    make demo    # same as: python3 -m demo.console.server

Every event comes from .agent-audit/session.jsonl (real hook decisions) or
demo/events.jsonl (real test, gate and verification steps). /try never executes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable, Iterator
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Tuple

from demo import run
from guardrails import policy

HOST, PORT = "127.0.0.1", 8001
INDEX = Path(__file__).with_name("index.html")
SCENES = {1: "1", 2: "2", 3: "3"}
CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
MAX_BODY = 4096
Offsets = Dict[str, Tuple[int, int]]


class Rejected(Exception):
    def __init__(self, status: int, detail: Any) -> None:
        super().__init__(str(detail))
        self.status, self.detail = status, detail


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


def stream(
    files: dict[str, Path],
    offsets: Offsets,
    interval: float = 0.25,
    heartbeat: float = 15,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[str]:
    quiet = 0.0
    while True:
        batch = poll(files, offsets)
        for record in batch:
            yield f"data: {json.dumps(record)}\n\n"
        quiet = 0.0 if batch else quiet + interval
        if quiet >= heartbeat:
            quiet = 0.0
            yield ": keep-alive\n\n"
        sleep(interval)


def field(body: dict[str, Any], name: str, kind: type, required: bool) -> Any:
    if name not in body:
        if required:
            raise Rejected(HTTPStatus.UNPROCESSABLE_ENTITY, [{"location": [name], "type": "missing"}])
        return None
    if type(body[name]) is not kind:
        raise Rejected(HTTPStatus.UNPROCESSABLE_ENTITY, [{"location": [name], "type": "type"}])
    return body[name]


class Console:
    """Routes and state for one console; the HTTP handler only parses and replies."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files = sources(root)
        self.start = positions(self.files)
        self.process: subprocess.Popen[bytes] | None = None
        self.lock = threading.Lock()

    def attempt(self, body: dict[str, Any]) -> dict[str, str]:
        self.only(body, {"command"})
        command = field(body, "command", str, required=True)
        if not 1 <= len(command) <= 500:
            raise Rejected(HTTPStatus.UNPROCESSABLE_ENTITY, [{"location": ["command"], "type": "length"}])
        decision = policy.evaluate("bash", {"command": command}, self.root)
        return {"decision": decision.decision, "reason": decision.reason, "target": decision.target}

    def scene(self, number: str, body: dict[str, Any]) -> dict[str, int]:
        self.only(body, set())
        if not number.isdigit() or int(number) not in SCENES:
            raise Rejected(HTTPStatus.NOT_FOUND, "Unknown scene")
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise Rejected(HTTPStatus.CONFLICT, "A scene is already running")
            command = [sys.executable, "-m", "demo.run", "--scene", SCENES[int(number)], "--pace", "2"]
            self.process = subprocess.Popen(command, cwd=self.root)
        return {"scene": int(number)}

    def verify(self, body: dict[str, Any]) -> dict[str, str]:
        self.only(body, {"tampered"})
        tampered = field(body, "tampered", bool, required=False) or False
        return run.verify_step(tampered, self.root)

    @staticmethod
    def only(body: dict[str, Any], allowed: set[str]) -> None:
        extra = sorted(set(body) - allowed)
        if extra:
            errors = [{"location": [name], "type": "extra_forbidden"} for name in extra]
            raise Rejected(HTTPStatus.UNPROCESSABLE_ENTITY, errors)


def handler(console: Console) -> type[BaseHTTPRequestHandler]:
    class ConsoleHandler(BaseHTTPRequestHandler):
        server_version = "guardrails-console"
        sys_version = ""

        def log_message(self, format: str, *args: Any) -> None:
            """No access log: commands typed into the console must not be recorded."""

        def allowed_host(self) -> bool:
            port = self.server.server_address[1]
            return self.headers.get("Host") in {f"{HOST}:{port}", f"localhost:{port}"}

        def reply(self, status: int, payload: Any) -> None:
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if not self.allowed_host():
                self.reply(HTTPStatus.FORBIDDEN, {"detail": "Unknown host"})
            elif self.path == "/":
                data = INDEX.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Security-Policy", CSP)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            elif self.path == "/events":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    for message in stream(console.files, dict(console.start)):
                        self.wfile.write(message.encode())
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the browser closed the stream
            else:
                self.reply(HTTPStatus.NOT_FOUND, {"detail": "Not Found"})

        def do_POST(self) -> None:
            media = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if not self.allowed_host():
                self.reply(HTTPStatus.FORBIDDEN, {"detail": "Unknown host"})
                return
            if media != "application/json":
                self.reply(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"detail": "Send JSON"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= MAX_BODY:
                    raise Rejected(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Body too large")
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise Rejected(HTTPStatus.UNPROCESSABLE_ENTITY, [{"location": [], "type": "object"}])
                if self.path == "/try":
                    result: Any = console.attempt(body)
                elif self.path.startswith("/scene/"):
                    result = console.scene(self.path.removeprefix("/scene/"), body)
                elif self.path == "/verify":
                    result = console.verify(body)
                else:
                    raise Rejected(HTTPStatus.NOT_FOUND, "Not Found")
            except Rejected as rejection:
                self.reply(rejection.status, {"detail": rejection.detail})
            except ValueError:
                self.reply(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Invalid JSON"})
            else:
                self.reply(HTTPStatus.OK, result)

    return ConsoleHandler


def create_server(root: Path = run.ROOT, host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), handler(Console(root)))
    server.daemon_threads = True  # open event streams must not block shutdown
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Live guardrails console")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)
    server = create_server()
    url = f"http://{HOST}:{PORT}/"
    print(f"Guardrails console on {url} (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
