from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200


def test_create_meeting():
    response = client.post(
        "/meetings", json={"transcript": "Hello world", "meeting_date": "2023-01-01"}
    )
    assert response.status_code == 202
    assert "id" in response.json()
    assert response.json()["status"] == "queued"


def test_get_meeting():
    created = client.post(
        "/meetings", json={"transcript": "Hello world", "meeting_date": "2023-01-01"}
    )

    meeting_id = created.json()["id"]
    response = client.get(f"/meetings/{meeting_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["result"]["summary"] == "stub"


def test_get_meeting_not_found():
    response = client.get("/meetings/nonexistent_id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"


def test_create_meeting_invalid_transcript():
    response = client.post("/meetings", json={"transcript": "", "meeting_date": "2023-01-01"})
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["type"] == "string_too_short"
    assert error["loc"] == ["body", "transcript"]
