import threading
from types import SimpleNamespace

from app.usage import UsageTracker, record_usage, track_usage
from scripts.evaluate import INPUT_PRICE_PER_M, OUTPUT_PRICE_PER_M, estimate_cost


def response(input_tokens, output_tokens):
    usage = SimpleNamespace(total_input_tokens=input_tokens, total_output_tokens=output_tokens)
    return SimpleNamespace(usage=usage)


def test_tracker_adds_usage_from_a_response():
    with track_usage() as usage:
        record_usage(response(100, 20))
        record_usage(response(50, 5))

    assert (usage.input_tokens, usage.output_tokens, usage.calls) == (150, 25, 2)


def test_no_active_tracker_does_nothing():
    record_usage(response(100, 20))  # must not raise


def test_response_without_usage_does_not_crash():
    with track_usage() as usage:
        record_usage(SimpleNamespace(usage=None))
        record_usage(SimpleNamespace())

    assert (usage.input_tokens, usage.output_tokens, usage.calls) == (0, 0, 0)


def test_none_token_fields_count_as_zero():
    with track_usage() as usage:
        record_usage(response(None, 7))

    assert (usage.input_tokens, usage.output_tokens, usage.calls) == (0, 7, 1)


def test_two_threads_do_not_mix_counts():
    results = {}

    def work(name, input_tokens):
        with track_usage() as usage:
            for _ in range(100):
                record_usage(response(input_tokens, 1))
            results[name] = usage

    threads = [
        threading.Thread(target=work, args=("a", 10)),
        threading.Thread(target=work, args=("b", 1000)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results["a"].input_tokens == 1_000
    assert results["b"].input_tokens == 100_000
    assert results["a"].calls == results["b"].calls == 100


def test_tracker_is_removed_after_the_with_block():
    with track_usage():
        pass
    record_usage(response(100, 20))  # nothing active, must not raise or count anywhere

    with track_usage() as usage:
        pass
    assert usage.calls == 0


def test_nested_trackers_restore_the_outer_one():
    with track_usage() as outer:
        with track_usage() as inner:
            record_usage(response(1, 1))
        record_usage(response(10, 10))

    assert inner.input_tokens == 1
    assert outer.input_tokens == 10


def test_estimate_cost_uses_price_per_million_tokens():
    usage = UsageTracker(input_tokens=1_000_000, output_tokens=1_000_000, calls=2)

    assert estimate_cost(usage) == INPUT_PRICE_PER_M + OUTPUT_PRICE_PER_M
    assert estimate_cost(UsageTracker()) == 0
