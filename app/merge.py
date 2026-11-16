"""Combine the results of several chunks into one, removing duplicates."""

import re

from app.schemas import ActionItem, MeetingResult

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def _norm(text: str) -> str:
    """Lowercase, unify curly quotes and collapse whitespace so tiny differences don't matter."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip().casefold()


def merge_action_items(items: list[ActionItem]) -> list[ActionItem]:
    """Keep one item per evidence quote. If two items quote the same line, they are the same
    commitment seen twice (for example in the overlap between two chunks), so keep the one
    with the higher confidence. The order of first appearance is preserved."""
    merged: list[ActionItem] = []

    for item in items:
        duplicate_index = None
        for index, kept in enumerate(merged):
            if _norm(item.evidence) == _norm(kept.evidence):
                duplicate_index = index
                break

        if duplicate_index is None:
            merged.append(item)
        elif item.confidence > merged[duplicate_index].confidence:
            merged[duplicate_index] = item

    return merged


def merge_decisions(decisions: list[str]) -> list[str]:
    """Remove repeated decisions (ignoring case and spacing), keeping the first wording."""
    seen: set[str] = set()
    unique: list[str] = []
    for decision in decisions:
        key = _norm(decision)
        if key not in seen:
            seen.add(key)
            unique.append(decision)
    return unique


def merge_results(results: list[MeetingResult]) -> MeetingResult:
    """Combine the results of several chunks into one MeetingResult.

    Action items and decisions are de-duplicated. The summaries are simply joined in order,
    which is a known limitation: a later version can condense them with one more model call.
    """
    return MeetingResult(
        summary=" ".join(result.summary.strip() for result in results),
        decisions=merge_decisions([d for result in results for d in result.decisions]),
        action_items=merge_action_items(
            [item for result in results for item in result.action_items]
        ),
    )
