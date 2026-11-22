import pytest

from market_intel.tools import llm_rate_limit


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def fake_clock(monkeypatch):
    clock = FakeClock()

    monkeypatch.setattr(llm_rate_limit, "monotonic", clock.monotonic)
    monkeypatch.setattr(llm_rate_limit, "sleep", clock.sleep)
    monkeypatch.setattr(llm_rate_limit, "_last_request_at", None)

    return clock


def test_requests_are_spaced_by_five_seconds(fake_clock):
    first = llm_rate_limit.invoke_with_rate_limit(lambda: "first")
    second = llm_rate_limit.invoke_with_rate_limit(lambda: "second")

    assert first == "first"
    assert second == "second"
    assert fake_clock.sleeps == [5.0]


def test_rate_limit_error_uses_suggested_retry_delay(fake_clock):
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise RuntimeError("429 Too Many Requests. Please retry in 7.5s")

        return "success"

    result = llm_rate_limit.invoke_with_rate_limit(operation)

    assert result == "success"
    assert attempts == 2
    assert fake_clock.sleeps == [7.5]


def test_non_rate_limit_errors_are_not_retried(fake_clock):
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("Invalid API configuration")

    with pytest.raises(RuntimeError, match="Invalid API configuration"):
        llm_rate_limit.invoke_with_rate_limit(operation)

    assert attempts == 1


def test_rate_limit_retries_are_bounded(fake_clock):
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    with pytest.raises(RuntimeError, match="RESOURCE_EXHAUSTED"):
        llm_rate_limit.invoke_with_rate_limit(operation)

    assert attempts == 3
    assert fake_clock.sleeps == [10.0, 10.0]
