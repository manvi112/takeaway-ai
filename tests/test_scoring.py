from app.schemas import ActionItem
from scripts.scoring import find_match

EXPECTED = [
    {
        "owner": "Ravi",
        "due_date": "2026-10-30",
        "evidence": ["Ravi: I'll send the updated budget to the finance team by Friday."],
    },
    {
        "owner": None,
        "due_date": None,
        "evidence": ["Priya: Someone should email the client about our progress."],
    },
    {
        "owner": "Dev",
        "due_date": "2026-11-04",
        "evidence": [
            "Meera: Dev, can you freeze the schema by Friday?",
            "Dev: Friday is tight, I'll do it by Wednesday instead.",
        ],
    },
]


def make(evidence: str) -> ActionItem:
    return ActionItem(task="x", owner=None, due_date=None, confidence=0.9, evidence=evidence)


def test_match_exact_quote():
    item = make("Ravi: I'll send the updated budget to the finance team by Friday.")
    assert find_match(item, EXPECTED) is EXPECTED[0]


def test_match_when_model_drops_speaker_name():
    item = make("I'll send the updated budget to the finance team by Friday.")
    assert find_match(item, EXPECTED) is EXPECTED[0]


def test_no_match_for_an_idea():
    item = make("Maybe we could try a new monitoring tool for the backend.")
    assert find_match(item, EXPECTED) is None


def test_match_ignores_case_curly_quotes_and_extra_spaces():
    item = make("RAVI: I’ll send the  updated budget\nto the finance team by Friday.")
    assert find_match(item, EXPECTED) is EXPECTED[0]


def test_match_on_second_accepted_line():
    item = make("Dev: Friday is tight, I'll do it by Wednesday instead.")
    assert find_match(item, EXPECTED) is EXPECTED[2]


def test_too_short_quote_never_matches():
    assert find_match(make("Friday"), EXPECTED) is None


def test_score_meeting_counts_found_invented_and_missed():
    from datetime import date

    from scripts.scoring import score_meeting

    items = [
        ActionItem(
            task="send budget", owner="Ravi", due_date=date(2026, 10, 30), confidence=0.9,
            evidence="I'll send the updated budget to the finance team by Friday.",
        ),
        ActionItem(
            task="email client", owner="Priya", due_date=None, confidence=0.8,
            evidence="Someone should email the client about our progress.",
        ),
        ActionItem(
            task="try tool", owner=None, due_date=None, confidence=0.5,
            evidence="Maybe we could try a new monitoring tool for the backend.",
        ),
    ]
    score = score_meeting(items, EXPECTED)

    assert score["found"] == 2
    assert score["invented"] == 1
    assert score["owner_correct"] == 1  # Ravi right, Priya wrong (expected None)
    assert score["due_correct"] == 2
    assert score["missed"] == ["Meera: Dev, can you freeze the schema by Friday?"]
