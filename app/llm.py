import logging
import random
import time
from collections.abc import Callable

from google import genai
from google.genai import errors

from app.config import get_settings
from app.usage import record_usage

logger = logging.getLogger(__name__)

MAX_RETRIES = 3  # so up to 4 tries in total
BASE_DELAY = 1.0  # seconds; doubles after every failed try
MAX_DELAY = 30.0  # no single wait is longer than this


class LLMUnavailableError(Exception):
    """The model API stayed unavailable (rate limited, overloaded, unreachable) after retries."""


def _is_retryable(exc: Exception) -> bool:
    """True for temporary problems that may go away. Permanent ones (bad key, bad request) fail."""
    if isinstance(exc, errors.APIError):
        code = exc.code or 0
        return code == 429 or code >= 500
    if isinstance(exc, TimeoutError | ConnectionError):
        return True
    # Network-level failures raised by the HTTP library underneath the SDK (timeouts, resets).
    return type(exc).__module__.split(".")[0] in {"httpx", "httpx2"}


def _backoff_seconds(attempt: int) -> float:
    """Wait before retry number `attempt` (0, 1, 2, ...): 1s, 2s, 4s, ... plus a little jitter."""
    delay = BASE_DELAY * 2**attempt
    delay += random.uniform(0, delay / 2)  # jitter, so parallel jobs don't retry in lockstep
    return min(delay, MAX_DELAY)


def _call_gemini(prompt: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

    with genai.Client(api_key=settings.gemini_api_key) as client:
        interaction = client.interactions.create(
            model=settings.gemini_model,
            input=prompt,
        )
        record_usage(interaction)
        return interaction.output_text


def generate(prompt: str, *, sleep: Callable[[float], None] = time.sleep) -> str:
    """Send the prompt to the model and return its text.

    Temporary API failures are retried with exponential backoff. If they last, raises
    LLMUnavailableError. Permanent failures (bad key, bad request) are raised immediately.
    `sleep` can be replaced in tests so they do not really wait.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            return _call_gemini(prompt)
        except Exception as exc:
            if not _is_retryable(exc):
                raise
            if attempt == MAX_RETRIES:
                raise LLMUnavailableError(
                    f"Model API still failing after {MAX_RETRIES} retries"
                ) from exc
            wait = _backoff_seconds(attempt)
            logger.warning(
                "Model API call failed (%s); retry %d/%d in %.1fs",
                type(exc).__name__, attempt + 1, MAX_RETRIES, wait,
            )
            sleep(wait)
    raise AssertionError("unreachable")  # the loop always returns or raises
