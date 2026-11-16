import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_API_KEY", "")
    with TestClient(app) as test_client:
        yield test_client


def test_health_never_returns_a_key(client, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "unit-test-key-value-not-real")
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["llm_configured"] is True
    assert "unit-test-key-value-not-real" not in response.text


def test_private_links_are_refused(client):
    local = client.post("/api/shelf/link", json={"url": "http://127.0.0.1/secret"})
    assert local.status_code == 400
    file_url = client.post("/api/shelf/link", json={"url": "file:///C:/Windows/win.ini"})
    assert file_url.status_code == 400


def test_generate_without_a_key_is_refused(client):
    upload = client.post(
        "/api/shelf/upload",
        files={"files": ("notes.txt", b"Attention decides what enters that trace. " * 4, "text/plain")},
    )
    assert upload.status_code == 200
    item_id = upload.json()["items"][0]["id"]
    created = client.post("/api/courses", json={"item_ids": [item_id], "depth": "guided"})
    assert created.status_code == 400
    assert "LLM_API_KEY" in created.json()["detail"]


def test_sample_path_teaches_in_order_without_leaking_answers(client):
    created = client.post("/api/courses/sample")
    assert created.status_code == 200
    course = client.get(f"/api/courses/{created.json()['id']}").json()
    assert course["sample"] is True
    assert course["status"] == "ready"
    assert [chapter["title"] for chapter in course["chapters"]] == ["Encoding", "Storage", "Retrieval"]
    assert course["chapters"][0]["unlocked"] is True
    assert course["chapters"][1]["unlocked"] is False
    assert course["chapters"][1]["lesson_md"] == ""
    assert course["chapters"][1]["questions"] == []

    first = course["chapters"][0]
    hidden = first["questions"][0]
    assert hidden["explanation"] == ""
    assert hidden["correct_id"] == ""
    assert hidden["quote"] == ""

    blocked = client.post(
        f"/api/courses/{course['id']}/chapters/{course['chapters'][1]['id']}/quiz",
        json={"option_id": "a"},
    )
    assert blocked.status_code == 400

    for _ in range(2):
        answer = client.post(
            f"/api/courses/{course['id']}/chapters/{first['id']}/quiz",
            json={"option_id": "a"},
        )
        assert answer.status_code == 200
        assert answer.json()["correct"] is True
        assert "Attention decides" in answer.json()["quote"] or "Elaborative encoding" in answer.json()["quote"]

    again = client.get(f"/api/courses/{course['id']}").json()
    assert again["chapters"][0]["quiz_answered"] is True
    assert again["chapters"][1]["unlocked"] is True
    revealed = again["chapters"][0]["questions"][0]
    assert revealed["explanation"]
    assert revealed["correct_id"] == "a"
