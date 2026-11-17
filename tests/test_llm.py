import pytest
from google.genai import errors

from app import llm
from app.llm import MAX_DELAY, MAX_RETRIES, LLMUnavailableError, generate


def api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"message": "test"}})


def fake_gemini(monkeypatch, outcomes: list):
    """Replace the real API call. Each call pops the next outcome: an exception is raised,
    anything else is returned. Returns the list of calls made."""
    calls = []

    def fake(prompt):
        calls.append(prompt)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(llm, "_call_gemini", fake)
    return calls


def test_success_on_first_try_never_sleeps(monkeypatch):
    fake_gemini(monkeypatch, ["ok"])
    sleeps = []

    assert generate("hi", sleep=sleeps.append) == "ok"
    assert sleeps == []


def test_retries_temporary_errors_then_succeeds(monkeypatch):
    calls = fake_gemini(monkeypatch, [api_error(429), api_error(503), "ok"])
    sleeps = []

    assert generate("hi", sleep=sleeps.append) == "ok"
    assert len(calls) == 3
    assert len(sleeps) == 2


def test_gives_up_after_max_retries(monkeypatch):
    calls = fake_gemini(monkeypatch, [api_error(429)] * (MAX_RETRIES + 1))
    sleeps = []

    with pytest.raises(LLMUnavailableError):
        generate("hi", sleep=sleeps.append)

    assert len(calls) == MAX_RETRIES + 1
    assert len(sleeps) == MAX_RETRIES


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_permanent_errors_are_not_retried(monkeypatch, code):
    calls = fake_gemini(monkeypatch, [api_error(code), "never reached"])
    sleeps = []

    with pytest.raises(errors.APIError):
        generate("hi", sleep=sleeps.append)

    assert len(calls) == 1
    assert sleeps == []


def test_network_errors_are_retried(monkeypatch):
    calls = fake_gemini(monkeypatch, [ConnectionError("reset"), "ok"])

    assert generate("hi", sleep=lambda seconds: None) == "ok"
    assert len(calls) == 2


def test_other_bugs_are_not_retried(monkeypatch):
    calls = fake_gemini(monkeypatch, [ValueError("bug"), "never reached"])

    with pytest.raises(ValueError):
        generate("hi", sleep=lambda seconds: None)

    assert len(calls) == 1


def test_backoff_grows_and_is_capped():
    first = llm._backoff_seconds(0)
    third = llm._backoff_seconds(2)

    assert 1.0 <= first <= 1.5  # 1s plus up to 50% jitter
    assert 4.0 <= third <= 6.0
    assert llm._backoff_seconds(20) <= MAX_DELAY
