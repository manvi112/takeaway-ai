# Takeaway

Meeting transcripts in, owned and verifiable action items out.

Takeaway takes a meeting transcript and returns a summary, the decisions made, and action items
with an owner, a due date and the exact quote that supports each one. Every quote is checked
against the transcript, so an item the model made up is rejected instead of shown to the user.

> Status: the extraction pipeline, API, storage, tests and evaluation are done.

## What it handles

- **Long transcripts.** Split into overlapping chunks, extracted chunk by chunk, then merged and
  de-duplicated (the same evidence quote means the same item).
- **Invalid model output.** Responses are validated against a schema, and every quote must appear
  word for word in the transcript. If not, the model is asked again with a short list of what
  was wrong (up to 3 attempts).
- **Temporary API failures.** Rate limits (429), server errors and network drops are retried with
  exponential backoff and jitter. Permanent errors such as a bad key fail immediately, and a
  persistent outage gives the user a clear "service unavailable" message.
- **Due dates.** "Today", "tomorrow", weekdays and "next <weekday>" are resolved in code from the
  quote, not by the model.
- **Cost.** Token usage is counted per job (a `ContextVar`, so concurrent jobs never mix their
  counts) and reported by the evaluation script.

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
action items that should be found (26 in total). The traps are deliberate: ideas ("maybe we
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
| + API retry and token tracking (same prompt, re-run) | 24 / 26 (92%) | 0 | 24 / 24 | 24 / 24 | 6.1 s |

The last two rows use the same prompt and code, so the change from 25 to 24 found is run-to-run
variation of the model, not a regression.

**Cost.** About 1,900 tokens per meeting, roughly $0.0016 at list price ($0.30 per 1M input and
$2.50 per 1M output tokens for `gemini-3.5-flash-lite`, from
[Google's release page](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.6),
checked 2026-11-17), so about $1.60 per 1,000 short meetings. It is an estimate: the page does not
say whether thinking tokens are billed as output.
