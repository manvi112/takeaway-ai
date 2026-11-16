from fastapi.testclient import TestClient

from app.extract import ExtractionError
from app.main import app
from app.schemas import MeetingResult

client = TestClient(app)
BODY = {"transcript": "Hello world", "meeting_date": "2026-10-27"}
FAKE_RESULT = MeetingResult(summary="s", decisions=[], action_items=[])


def submit() -> str:
    return client.post("/meetings", json=BODY).json()["id"]


def test_job_completes(monkeypatch):
    monkeypatch.setattr("app.jobs.extract_long", lambda transcript, meeting_date: FAKE_RESULT)

    meeting_id = submit()

    response = client.get(f"/meetings/{meeting_id}").json()
    assert response["status"] == "completed"
    assert response["result"]["summary"] == "s"


def test_job_fails_when_extraction_fails(monkeypatch):
    def fail(transcript, meeting_date):
        raise ExtractionError("model kept returning invalid JSON")

    monkeypatch.setattr("app.jobs.extract_long", fail)

    meeting_id = submit()

    response = client.get(f"/meetings/{meeting_id}").json()
    assert response["status"] == "failed"
    assert response["result"] is None
    assert response["error"] == "The model did not return a valid result."


def test_unexpected_crash_does_not_leak_details(monkeypatch):
    def crash(transcript, meeting_date):
        raise RuntimeError("secret key abc123")

    monkeypatch.setattr("app.jobs.extract_long", crash)

    meeting_id = submit()

    response = client.get(f"/meetings/{meeting_id}").json()
    assert response["status"] == "failed"
    assert response["result"] is None
    assert "abc123" not in response["error"]
    assert response["error"] == "Internal error while processing this meeting."
