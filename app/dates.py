"""Work out due dates from the words in a quote, in code instead of asking the model.

Language models are unreliable at calendar arithmetic, so wherever the evidence quote contains
a clear date phrase, the date computed here replaces the model's guess.
"""

import re
from datetime import date, timedelta

from app.schemas import MeetingResult

_WEEKDAYS = {
    name: index
    for index, name in enumerate(
        ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    )
}

_PHRASE = re.compile(
    r"\b(?:(?P<next>next)\s+)?(?P<weekday>" + "|".join(_WEEKDAYS) + r")\b"
    r"|\b(?P<relative>today|tomorrow)\b",
    re.IGNORECASE,
)


def _weekday_date(meeting_date: date, weekday: int, *, next_week: bool) -> date:
    if next_week:
        # "next Wednesday": that weekday in the following Monday-to-Sunday week.
        monday_next_week = meeting_date - timedelta(days=meeting_date.weekday()) + timedelta(days=7)
        return monday_next_week + timedelta(days=weekday)
    # Bare weekday: the first such weekday after the meeting date (never the same day).
    days_ahead = (weekday - meeting_date.weekday()) % 7 or 7
    return meeting_date + timedelta(days=days_ahead)


def resolve_due_date(evidence: str, meeting_date: date) -> date | None:
    """Return the date the quote refers to, or None if it has no single clear date phrase.

    Understands "today", "tomorrow", a bare weekday ("by Friday") and "next <weekday>".
    A quote with two different date phrases is ambiguous, so it also returns None.
    """
    found: set[date] = set()
    for match in _PHRASE.finditer(evidence):
        if match["relative"]:
            offset = 0 if match["relative"].lower() == "today" else 1
            found.add(meeting_date + timedelta(days=offset))
        else:
            weekday = _WEEKDAYS[match["weekday"].lower()]
            found.add(_weekday_date(meeting_date, weekday, next_week=bool(match["next"])))
    return found.pop() if len(found) == 1 else None


def fix_due_dates(result: MeetingResult, meeting_date: date) -> MeetingResult:
    """Replace each item's due date with the one computed from its quote, where there is one."""
    fixed = []
    for item in result.action_items:
        resolved = resolve_due_date(item.evidence, meeting_date)
        fixed.append(item.model_copy(update={"due_date": resolved}) if resolved else item)
    return result.model_copy(update={"action_items": fixed})
