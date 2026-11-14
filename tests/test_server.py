"""The HTTP door of the app (server/main.py), on fake data: no network, no model."""
import os

os.environ["ATLAS_FAKE"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from server.main import app  # noqa: E402

client = TestClient(app)


def test_status_and_questions():
    assert client.get("/api/status").json()["fake"] is True
    qs = client.get("/api/questions").json()
    assert len(qs) == 20 and {"id", "split", "question", "question_it", "expected"} <= set(qs[0])


def test_answer_is_scored_against_the_gold():
    q = next(x for x in client.get("/api/questions").json() if x["id"] == "CQ10")
    r = client.post("/api/answer", json={"question": q["question"], "mode": "B", "cq": "CQ10"}).json()
    assert "answer" in r and "score" in r


def test_unknown_mode_is_refused():
    assert client.post("/api/answer", json={"question": "x", "mode": "Z"}).status_code == 400
