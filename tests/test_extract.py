import copy
import json
from datetime import date

import pytest

from app.extract import ExtractionError, extract, extract_long

TRANSCRIPT = "Ravi said, I'll send the updated budget by Friday."

VALID_DATA = {
    "summary": "Ravi agreed to send the updated budget by Friday.",
    "decisions": [],
    "action_items": [
        {
            "task": "Send the updated budget",
            "owner": "Ravi",
            "due_date": "2026-10-30",
            "confidence": 1.0,
            "evidence": "I'll send the updated budget by Friday.",
        }
    ],
}
VALID_RESPONSE = json.dumps(VALID_DATA)


def make_fake_llm(responses):
    calls = []

    def fake(prompt):
        calls.append(prompt)
        return responses[min(len(calls) - 1, len(responses) - 1)]

    fake.calls = calls
    return fake


def test_valid_response_first_try():
    fake = make_fake_llm([VALID_RESPONSE])

    result = extract(TRANSCRIPT, "2026-10-27", llm=fake)

    assert result.action_items[0].owner == "Ravi"
    assert result.action_items[0].due_date == date(2026, 10, 30)
    assert len(fake.calls) == 1


def test_retries_after_invalid_json():
    fake = make_fake_llm(["this is not json", VALID_RESPONSE])

    result = extract(TRANSCRIPT, "2026-10-27", llm=fake)

    assert result.action_items[0].owner == "Ravi"
    assert len(fake.calls) == 2
    assert "Problems found" in fake.calls[1]


def test_gives_up_after_max_attempts():
    fake = make_fake_llm(["this is not json"])

    with pytest.raises(ExtractionError):
        extract(TRANSCRIPT, "2026-10-27", max_attempts=3, llm=fake)

    assert len(fake.calls) == 3


def test_retries_when_evidence_is_not_in_transcript():
    invented = copy.deepcopy(VALID_DATA)
    invented["action_items"][0]["evidence"] = "Ravi will fly to Mars"
    fake = make_fake_llm([json.dumps(invented), VALID_RESPONSE])

    extract(TRANSCRIPT, "2026-10-27", llm=fake)

    assert len(fake.calls) == 2
    assert "Ravi will fly to Mars" in fake.calls[1]


def test_curly_apostrophe_in_evidence_is_accepted():
    curly = copy.deepcopy(VALID_DATA)
    curly["action_items"][0]["evidence"] = "I\u2019ll send the updated budget by Friday."
    fake = make_fake_llm([json.dumps(curly)])

    extract(TRANSCRIPT, "2026-10-27", llm=fake)

    assert len(fake.calls) == 1


LONG_TRANSCRIPT = (
    "Priya: Can you send the budget?\n"
    "Ravi: I'll send the updated budget by Friday.\n"
    "Amit: I'll fix the login bug.\n"
    "Priya: Great."
)
# With max_chars=100 and overlap_lines=1 this splits into two chunks, and the Ravi line is in both.


def make_response(summary, decisions, items):
    return json.dumps({"summary": summary, "decisions": decisions, "action_items": items})


def make_item(task, owner, evidence):
    return {
        "task": task,
        "owner": owner,
        "due_date": None,
        "confidence": 0.9,
        "evidence": evidence,
    }


def test_extract_long_merges_chunks_and_removes_overlap_duplicates():
    budget = make_item("Send the budget", "Ravi", "I'll send the updated budget by Friday.")
    login = make_item("Fix the login bug", "Amit", "I'll fix the login bug.")
    fake = make_fake_llm(
        [
            make_response("Budget discussed.", ["Use PostgreSQL"], [budget]),
            make_response("Login bug claimed.", ["use postgresql"], [budget, login]),
        ]
    )

    result = extract_long(LONG_TRANSCRIPT, "2026-10-27", max_chars=100, overlap_lines=1, llm=fake)

    assert len(fake.calls) == 2
    assert [item.task for item in result.action_items] == ["Send the budget", "Fix the login bug"]
    assert result.decisions == ["Use PostgreSQL"]
    assert result.summary == "Budget discussed. Login bug claimed."


def test_extract_long_retries_only_the_failing_chunk():
    budget = make_item("Send the budget", "Ravi", "I'll send the updated budget by Friday.")
    good_1 = make_response("One.", [], [budget])
    good_2 = make_response("Two.", [], [])
    fake = make_fake_llm([good_1, "not json", good_2])

    result = extract_long(LONG_TRANSCRIPT, "2026-10-27", max_chars=100, overlap_lines=1, llm=fake)

    assert len(fake.calls) == 3
    assert result.summary == "One. Two."


def test_extract_long_rejects_empty_transcript():
    with pytest.raises(ValueError):
        extract_long("   \n\n", "2026-10-27", llm=make_fake_llm([VALID_RESPONSE]))
