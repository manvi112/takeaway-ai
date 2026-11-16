from datetime import date

from app.dates import fix_due_dates, resolve_due_date
from app.schemas import ActionItem, MeetingResult

THURSDAY = date(2026, 11, 5)


def test_today_and_tomorrow():
    assert resolve_due_date("I'll rotate the credentials today.", THURSDAY) == THURSDAY
    assert resolve_due_date("I'll fix it tomorrow.", THURSDAY) == date(2026, 11, 6)


def test_bare_weekday_is_first_one_after_the_meeting():
    assert resolve_due_date("I'll send it by Friday.", THURSDAY) == date(2026, 11, 6)
    assert resolve_due_date("I'll send it by Wednesday.", THURSDAY) == date(2026, 11, 11)


def test_same_weekday_means_a_week_later():
    assert resolve_due_date("Let's do it on Thursday.", THURSDAY) == date(2026, 11, 12)


def test_next_weekday_is_in_the_following_week():
    assert resolve_due_date("By next Wednesday.", THURSDAY) == date(2026, 11, 11)
    assert resolve_due_date("By next Friday.", THURSDAY) == date(2026, 11, 13)
    assert resolve_due_date("By next Monday.", date(2026, 11, 2)) == date(2026, 11, 9)


def test_is_case_insensitive():
    assert resolve_due_date("by FRIDAY", THURSDAY) == date(2026, 11, 6)


def test_no_date_phrase_gives_none():
    assert resolve_due_date("I'll do it soon.", THURSDAY) is None
    assert resolve_due_date("I'll review it next week.", THURSDAY) is None


def test_two_different_dates_in_one_quote_is_ambiguous():
    quote = "Friday is tight, I'll do it by Wednesday instead."
    assert resolve_due_date(quote, date(2026, 11, 2)) is None


def test_fix_due_dates_overrides_model_but_keeps_it_when_unsure():
    def item(evidence, due):
        return ActionItem(task="t", owner=None, due_date=due, confidence=1.0, evidence=evidence)

    result = MeetingResult(
        summary="s",
        decisions=[],
        action_items=[
            item("I'll do the API docs by next Wednesday.", date(2026, 11, 18)),  # model is wrong
            item("Sure, I'll do that.", date(2026, 11, 9)),  # no phrase, keep model's date
            item("I'll tidy up soon.", None),
        ],
    )
    fixed = fix_due_dates(result, THURSDAY)

    assert [i.due_date for i in fixed.action_items] == [date(2026, 11, 11), date(2026, 11, 9), None]
    assert result.action_items[0].due_date == date(2026, 11, 18)  # original untouched
