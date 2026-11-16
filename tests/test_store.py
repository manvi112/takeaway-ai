from datetime import date

from app.api_schemas import JobStatus, MeetingOut
from app.schemas import ActionItem, MeetingResult
from app.store import configure_engine, get_job, save_job

RESULT = MeetingResult(
    summary="Budget discussed.",
    decisions=["Use PostgreSQL"],
    action_items=[
        ActionItem(
            task="Send the budget",
            owner="Ravi",
            due_date=date(2026, 10, 30),
            confidence=0.9,
            evidence="I'll send the budget by Friday.",
        )
    ],
)


def test_missing_job_returns_none():
    assert get_job("does-not-exist") is None


def test_saved_job_can_be_read_back():
    save_job(MeetingOut(id="a1", status=JobStatus.queued))

    job = get_job("a1")

    assert job.id == "a1"
    assert job.status == JobStatus.queued
    assert job.result is None


def test_saving_the_same_id_updates_the_job():
    save_job(MeetingOut(id="a1", status=JobStatus.queued))
    save_job(MeetingOut(id="a1", status=JobStatus.completed, result=RESULT))

    job = get_job("a1")

    assert job.status == JobStatus.completed
    assert job.result == RESULT


def test_failed_job_keeps_its_error():
    save_job(MeetingOut(id="a1", status=JobStatus.failed, error="bad"))

    job = get_job("a1")

    assert job.status == JobStatus.failed
    assert job.error == "bad"
    assert job.result is None


def test_job_survives_a_restart(tmp_path):
    save_job(MeetingOut(id="a1", status=JobStatus.completed, result=RESULT))

    configure_engine(f"sqlite:///{tmp_path / 'test.db'}")  # a new connection to the same file

    assert get_job("a1").result == RESULT
