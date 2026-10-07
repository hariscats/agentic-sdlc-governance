from __future__ import annotations

import http.client
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from src.app import create_server, serve_in_background


@contextmanager
def api(database: Path) -> Iterator[Any]:
    server = create_server(database, port=0)
    serve_in_background(server)

    def call(method: str, path: str, body: Any = None) -> tuple[int, str]:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        payload = None if body is None else json.dumps(body)
        connection.request(method, path, payload, {"Content-Type": "application/json"})
        response = connection.getresponse()
        result = response.status, response.read().decode()
        connection.close()
        return result

    try:
        yield call
    finally:
        server.shutdown()
        server.server_close()


class PermitApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "permits.db"

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_submit_retrieve_persist(self) -> None:
        with api(self.database) as call:
            self.assertEqual(call("GET", "/health"), (200, '{"status": "ok"}'))
            status, text = call(
                "POST", "/permits", {"category": "event", "description": "  Fictional community event  "}
            )
            self.assertEqual(status, 201)
            permit = json.loads(text)
            self.assertEqual(permit["status"], "submitted")
            self.assertEqual(permit["description"], "Fictional community event")
            status, text = call("GET", f"/permits/{permit['id']}")
            self.assertEqual((status, json.loads(text)), (200, permit))
        with api(self.database) as call:
            status, text = call("GET", f"/permits/{permit['id']}")
            self.assertEqual((status, json.loads(text)), (200, permit))
            self.assertEqual(call("GET", "/permits/missing")[0], 404)
            self.assertEqual(call("GET", "/permits/'%20OR%201=1--")[0], 404)

    def test_invalid_input_does_not_echo_values(self) -> None:
        bodies: list[Any] = [
            {},
            [],
            {"category": "other", "description": "Fictional activity"},
            {"category": "event", "description": " " * 10},
            {"category": "event", "description": "short"},
            {"category": "event", "description": "x" * 501},
            {"category": "event", "description": 12345678901},
            {"category": "event", "description": "Line one\nline two"},
            {"category": "event", "description": "Fictional\x7factivity"},
            {"category": "event", "description": "Fictional\x85activity"},
            {"category": "event", "description": "Fictional activity", "status": "approved"},
        ]
        with api(self.database) as call:
            for body in bodies:
                with self.subTest(body=body):
                    status, text = call("POST", "/permits", body)
                    self.assertEqual(status, 422)
                    self.assertNotIn("input", text)
                    self.assertNotIn("Fictional", text)

    def test_malformed_json_and_unknown_routes(self) -> None:
        with api(self.database) as call:
            connection_status, text = call("GET", "/nowhere")
            self.assertEqual(connection_status, 404)
            self.assertEqual(call("POST", "/elsewhere", {})[0], 404)
        server = create_server(self.database, port=0)
        serve_in_background(server)
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
            connection.request("POST", "/permits", "{not json", {"Content-Type": "application/json"})
            response = connection.getresponse()
            self.assertEqual(response.status, 422)
            self.assertIn("json_invalid", response.read().decode())
            connection.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
