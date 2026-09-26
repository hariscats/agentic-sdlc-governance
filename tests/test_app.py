from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app import create_app


def test_submit_retrieve_persist(tmp_path: Path) -> None:
    database = tmp_path / "permits.db"
    with TestClient(create_app(database)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post(
            "/permits", json={"category": "event", "description": "  Fictional community event  "}
        )
        assert response.status_code == 201
        permit = response.json()
        assert permit["status"] == "submitted"
        assert permit["description"] == "Fictional community event"
        assert client.get(f"/permits/{permit['id']}").json() == permit
    with TestClient(create_app(database)) as client:
        assert client.get(f"/permits/{permit['id']}").json() == permit
        assert client.get("/permits/missing").status_code == 404
        assert client.get("/permits/'%20OR%201=1--").status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"category": "other", "description": "Fictional activity"},
        {"category": "event", "description": " " * 10},
        {"category": "event", "description": "short"},
        {"category": "event", "description": "x" * 501},
        {"category": "event", "description": "Line one\nline two"},
        {"category": "event", "description": "Fictional\x7factivity"},
        {"category": "event", "description": "Fictional\x85activity"},
        {"category": "event", "description": "Fictional activity", "status": "approved"},
    ],
)
def test_invalid_input_does_not_echo_values(tmp_path: Path, body: dict[str, str]) -> None:
    with TestClient(create_app(tmp_path / "test.db")) as client:
        response = client.post("/permits", json=body)
        assert response.status_code == 422
        assert "input" not in response.text


def test_feature_002_is_not_implemented(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "test.db")) as client:
        assert client.post("/permits/example/decision", json={}).status_code == 404
