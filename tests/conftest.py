import pytest

from app.schemas import MeetingResult
from app.store import configure_engine, init_db

STUB_RESULT = MeetingResult(summary="stub", decisions=[], action_items=[])


@pytest.fixture(autouse=True)
def isolate_tests(monkeypatch, tmp_path):
    """Every test gets its own empty database and can never reach the real model.

    Tests that need a specific model behaviour override this with their own monkeypatch.
    """
    configure_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    monkeypatch.setattr("app.jobs.extract_long", lambda transcript, meeting_date: STUB_RESULT)
