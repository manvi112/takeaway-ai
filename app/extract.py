import logging
import re
from collections.abc import Callable
from datetime import date

from pydantic import ValidationError

from app.chunking import chunk_transcript
from app.dates import fix_due_dates
from app.llm import generate
from app.merge import merge_results
from app.prompts import build_prompt, build_retry_prompt
from app.schemas import MeetingResult

logger = logging.getLogger(__name__)

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_CODE_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*\n?(.*?)\n?```\s*$", re.DOTALL)


class ExtractionError(Exception):
    """The model never produced a valid, grounded result within the allowed attempts."""


class _InvalidOutput(Exception):
    """One attempt failed. The message is fed back to the model on the next attempt."""


def _strip_code_fences(text: str) -> str:
    """Models sometimes wrap JSON in ```json fences even when told not to."""
    match = _CODE_FENCE.match(text)
    return match.group(1) if match else text


def _normalise(text: str) -> str:
    """Make quote comparison tolerant of case, curly quotes and whitespace differences."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip().casefold()


def _is_grounded(evidence: str, transcript: str) -> bool:
    return _normalise(evidence) in _normalise(transcript)


def _describe(error: ValidationError) -> str:
    """Short, readable error text. str(error) repeats the whole input, which is too noisy."""
    return "\n".join(
        f"- {'.'.join(str(part) for part in item['loc']) or 'response'}: {item['msg']}"
        for item in error.errors()
    )


def _parse(response: str, transcript: str) -> MeetingResult:
    try:
        result = MeetingResult.model_validate_json(_strip_code_fences(response))
    except ValidationError as error:
        raise _InvalidOutput(_describe(error)) from error

    ungrounded = [
        item.evidence for item in result.action_items if not _is_grounded(item.evidence, transcript)
    ]
    if ungrounded:
        quoted = "\n".join(f'- "{quote}"' for quote in ungrounded)
        raise _InvalidOutput(
            "These evidence quotes do not appear word for word in the transcript. "
            f"Copy them exactly or drop the action item:\n{quoted}"
        )
    return result


def extract(
    transcript: str,
    meeting_date: str,
    *,
    max_attempts: int = 3,
    llm: Callable[[str], str] = generate,
) -> MeetingResult:
    """Extract summary, decisions and action items.

    Invalid output (bad JSON, schema violations, evidence not in the transcript) is retried
    with the problems shown to the model. After max_attempts, raises ExtractionError.
    Errors from the llm call itself (network, rate limits) are not handled here.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    original_prompt = build_prompt(transcript, meeting_date)
    prompt = original_prompt
    problem = ""

    for attempt in range(1, max_attempts + 1):
        response = llm(prompt)
        try:
            result = _parse(response, transcript)
        except _InvalidOutput as invalid:
            problem = str(invalid)
            logger.warning("Attempt %d/%d rejected:\n%s", attempt, max_attempts, problem)
            prompt = build_retry_prompt(original_prompt, response, problem)
            continue
        logger.info("Attempt %d/%d accepted", attempt, max_attempts)
        return fix_due_dates(result, date.fromisoformat(meeting_date))

    raise ExtractionError(
        f"No valid result after {max_attempts} attempts. Last problem:\n{problem}"
    )


def extract_long(
    transcript: str,
    meeting_date: str,
    *,
    max_chars: int = 6000,
    overlap_lines: int = 3,
    max_attempts: int = 3,
    llm: Callable[[str], str] = generate,
) -> MeetingResult:
    """Extract from a transcript of any length.

    The transcript is split into overlapping chunks, each chunk goes through extract() (with
    its own retries), and the per-chunk results are merged into one MeetingResult.
    Raises ValueError for an empty transcript and ExtractionError if any chunk keeps failing.
    """
    chunks = chunk_transcript(transcript, max_chars=max_chars, overlap_lines=overlap_lines)
    if not chunks:
        raise ValueError("Transcript is empty")

    logger.info("Extracting from %d chunk(s)", len(chunks))
    results = [extract(chunk, meeting_date, max_attempts=max_attempts, llm=llm) for chunk in chunks]
    return merge_results(results)
