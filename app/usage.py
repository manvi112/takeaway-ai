from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class UsageTracker:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.calls += 1


# Holds the tracker of the job running in this thread, or None if nobody is tracking.
_current: ContextVar[UsageTracker | None] = ContextVar("usage_tracker", default=None)


@contextmanager
def track_usage() -> Iterator[UsageTracker]:
    tracker = UsageTracker()
    token = _current.set(tracker)
    try:
        yield tracker
    finally:
        _current.reset(token)  # restores the previous tracker, so nesting works


def record_usage(response) -> None:
    """Add this response's token counts to the active tracker, if there is one."""
    tracker = _current.get()
    if tracker is None:
        return
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    tracker.add(
        getattr(usage, "total_input_tokens", None) or 0,
        getattr(usage, "total_output_tokens", None) or 0,
    )
