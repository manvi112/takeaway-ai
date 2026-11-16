from app.schemas import ActionItem

MIN_QUOTE_CHARS = 10


def _norm(text: str) -> str:
    text = text.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return " ".join(text.split())


def find_match(item: ActionItem, expected: list[dict]) -> dict | None:
    quote = _norm(item.evidence)
    if len(quote) < MIN_QUOTE_CHARS:
        return None

    for entry in expected:
        for line in entry["evidence"]:
            if quote in _norm(line):
                return entry
    return None


def _same_owner(got: str | None, want: str | None) -> bool:
    return (got or "").strip().lower() == (want or "").strip().lower()


def score_meeting(items: list[ActionItem], expected: list[dict]) -> dict:
    """Compare one meeting's extracted items with its expected items."""
    matched: dict[int, ActionItem] = {}  # index of expected entry -> the item that found it
    invented: list[str] = []
    duplicates = 0

    for item in items:
        entry = find_match(item, expected)
        if entry is None:
            invented.append(item.evidence)
            continue
        index = next(i for i, e in enumerate(expected) if e is entry)
        if index in matched:
            duplicates += 1  # the same expected item found twice
        else:
            matched[index] = item

    owner_correct = sum(_same_owner(it.owner, expected[i]["owner"]) for i, it in matched.items())
    due_correct = sum(
        (it.due_date.isoformat() if it.due_date else None) == expected[i]["due_date"]
        for i, it in matched.items()
    )
    missed = [expected[i]["evidence"][0] for i in range(len(expected)) if i not in matched]

    return {
        "expected": len(expected),
        "found": len(matched),
        "invented": len(invented),
        "duplicates": duplicates,
        "owner_correct": owner_correct,
        "due_correct": due_correct,
        "missed": missed,
        "invented_quotes": invented,
    }
