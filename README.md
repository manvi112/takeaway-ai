# Takeaway

Meeting transcripts in, owned and verifiable action items out.

Takeaway takes a meeting transcript and returns a summary, the decisions made, and action items
with an owner, a due date and the exact quote that supports each one. Every quote is checked
against the transcript, so an item the model made up is rejected instead of shown to the user.

> Status: the extraction pipeline, API, storage, tests and evaluation are done.

## Run it

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env        # then add your GEMINI_API_KEY
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs, or from a terminal:

```bash
curl -X POST http://127.0.0.1:8000/meetings \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Ravi: I'\''ll send the budget by Friday.", "meeting_date": "2026-10-27"}'
# -> {"id": "...", "status": "queued"}

curl http://127.0.0.1:8000/meetings/<id>
```

Run the extractor on a file without the API:

```bash
uv run python -m scripts.extract_file data/samples/standup_01.txt --date 2026-10-27
```

## Test it

```bash
uv run pytest -q
uv run ruff check
```

Tests never call the real model; the LLM is replaced by a fake.

## Evaluation

`data/eval/` holds 5 synthetic meetings, each with a transcript and an `.expected.json` of the
action items that should be found (27 in total). The traps are deliberate: ideas ("maybe we
could..."), deferred items ("let's park it"), vague meetings ("catch up soon"), corrected
deadlines, and tasks with no owner. Labelling rules are in `data/eval/README.md`.

```bash
uv run python -m scripts.evaluate              # all meetings (calls the real model)
uv run python -m scripts.evaluate --only planning_01
```

For each meeting the scorer matches extracted items to expected ones by their evidence quote,
then reports how many were found, how many were invented (matched nothing expected), and
whether the owner and due date were right.

Model: `gemini-3.5-flash-lite`. Results:

| Run | Found | Invented | Owner correct | Due date correct | Avg latency |
|---|---|---|---|---|---|
| v1 prompt | 23 / 27 (85%) | 0 | 23 / 23 | 21 / 23 | 4.9 s |
| + rules for vague deadlines and "next <weekday>" | 24 / 27 (89%) | 0 | 24 / 24 | 23 / 24 | 4.7 s |
| + dates resolved in code (one borderline label removed, 26 items) | 25 / 26 (96%) | 0 | 25 / 25 | 25 / 25 | 5.5 s |
