import copy
import json
from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import MeetingResult

VALID = {
    "summary": "The team agreed to ship the beta on 30 Oct.",
    "decisions": ["Ship the beta on 30 Oct"],
    "action_items": [
        {
            "task": "Send the revised budget",
            "owner": "Ravi",
            "due_date": "2026-10-30",
            "confidence": 0.9,
            "evidence": "Ravi, can you send the revised budget by Friday?",
        }
    ],
}


def payload(**changes) -> dict:
    data = copy.deepcopy(VALID)
    data.update(changes)
    return data


def parse(data: dict) -> MeetingResult:
    return MeetingResult.model_validate_json(json.dumps(data))


def first_error(exc: pytest.ExceptionInfo[ValidationError]) -> dict:
    return exc.value.errors()[0]


def test_valid_result_parses():
    result = parse(VALID)
    item = result.action_items[0]
    assert item.owner == "Ravi"
    assert item.due_date == date(2026, 10, 30)


def test_meeting_with_no_decisions_or_actions_is_valid():
    result = parse(payload(decisions=[], action_items=[]))
    assert result.action_items == []


def test_missing_required_field_is_rejected():
    data = payload()
    del data["summary"]
    with pytest.raises(ValidationError) as exc:
        parse(data)
    assert first_error(exc)["type"] == "missing"
    assert first_error(exc)["loc"] == ("summary",)


def test_confidence_above_one_is_rejected():
    data = payload()
    data["action_items"][0]["confidence"] = 1.7
    with pytest.raises(ValidationError) as exc:
        parse(data)
    assert first_error(exc)["loc"] == ("action_items", 0, "confidence")


def test_truncated_json_is_rejected():
    with pytest.raises(ValidationError) as exc:
        MeetingResult.model_validate_json('{"summary": "abc", "decisi')
    assert first_error(exc)["type"] == "json_invalid"


@pytest.mark.parametrize("bad_date", ["this Friday", "31/12/2026", 1700000000])
def test_non_iso_due_date_is_rejected(bad_date):
    data = payload()
    data["action_items"][0]["due_date"] = bad_date
    with pytest.raises(ValidationError):
        parse(data)


@pytest.mark.parametrize("placeholder", ["", "  ", "Unknown", "N/A", "unassigned", "TBD"])
def test_placeholder_owner_becomes_none(placeholder):
    data = payload()
    data["action_items"][0]["owner"] = placeholder
    assert parse(data).action_items[0].owner is None


def test_unexpected_field_is_rejected():
    with pytest.raises(ValidationError) as exc:
        parse(payload(id=1))
    assert first_error(exc)["type"] == "extra_forbidden"
