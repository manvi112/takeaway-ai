from app.merge import merge_action_items, merge_decisions, merge_results
from app.schemas import ActionItem, MeetingResult


def make_item(task="Send the budget", evidence="I'll send the budget by Friday.", confidence=0.9):
    return ActionItem(task=task, owner="Ravi", confidence=confidence, evidence=evidence)


def test_empty_list_gives_empty_list():
    assert merge_action_items([]) == []


def test_same_evidence_becomes_one_item():
    first = make_item(task="Send the budget")
    second = make_item(task="Send the updated budget to finance")

    merged = merge_action_items([first, second])

    assert len(merged) == 1


def test_different_evidence_stays_separate():
    first = make_item(evidence="I'll send the budget by Friday.")
    second = make_item(task="Fix the login bug", evidence="I'll fix the login bug.")

    merged = merge_action_items([first, second])

    assert len(merged) == 2


def test_higher_confidence_item_survives():
    low = make_item(task="Low", confidence=0.6)
    high = make_item(task="High", confidence=0.95)

    merged = merge_action_items([low, high])

    assert [item.task for item in merged] == ["High"]


def test_first_item_wins_when_confidence_is_equal():
    first = make_item(task="First", confidence=0.8)
    second = make_item(task="Second", confidence=0.8)

    merged = merge_action_items([first, second])

    assert [item.task for item in merged] == ["First"]


def test_evidence_differing_only_in_case_and_spacing_is_a_duplicate():
    first = make_item(evidence="I'll send the budget by Friday.")
    second = make_item(evidence="i’ll  send the   BUDGET by friday.")

    assert len(merge_action_items([first, second])) == 1


def test_order_of_first_appearance_is_kept():
    a = make_item(task="A", evidence="line a")
    b = make_item(task="B", evidence="line b")
    a_again = make_item(task="A again", evidence="line a", confidence=0.5)

    merged = merge_action_items([a, b, a_again])

    assert [item.task for item in merged] == ["A", "B"]


def test_merge_decisions_removes_repeats_ignoring_case():
    decisions = ["Use PostgreSQL", "use postgresql ", "Ship on Friday"]

    assert merge_decisions(decisions) == ["Use PostgreSQL", "Ship on Friday"]


def test_merge_results_combines_all_parts():
    shared = make_item(evidence="shared line")
    first = MeetingResult(summary="A.", decisions=["X"], action_items=[shared])
    second = MeetingResult(summary="B.", decisions=["x", "Y"], action_items=[shared])

    merged = merge_results([first, second])

    assert merged.summary == "A. B."
    assert merged.decisions == ["X", "Y"]
    assert len(merged.action_items) == 1
