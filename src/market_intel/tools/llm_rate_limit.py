
"""Shared rate limiting and bounded retries for language-model requests."""

import re
import threading
from collections.abc import Callable
from time import monotonic, sleep

MIN_REQUEST_INTERVAL_SECONDS = 5.0
MAX_RATE_LIMIT_RETRIES = 2
FALLBACK_RETRY_DELAY_SECONDS = 10.0

_lock = threading.Lock()
_last_request_at: float | None = None


def _is_rate_limit_error(exc: Exception) -> bool:
    """Identify temporary API rate-limit and quota errors."""

    message = str(exc).lower()

    indicators = (
        "429",
        "resource_exhausted",
        "rate limit",
        "quota exceeded",
    )

    return any(indicator in message for indicator in indicators)


def _get_retry_delay(exc: Exception) -> float:
    """Extract Google's suggested retry delay when available."""

    message = str(exc)

    patterns = (
        r"retry\s+in\s+(\d+(?:\.\d+)?)\s*s",
        r"""retryDelay["']?\s*[:=]\s*["']?(\d+(?:\.\d+)?)s""",
    )

    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)

        if match:
            return float(match.group(1))

    return FALLBACK_RETRY_DELAY_SECONDS


def invoke_with_rate_limit[T](operation: Callable[[], T]) -> T:
    """Execute a model request with shared pacing and bounded 429 retries.

    All model requests in this process share one lock and request timestamp.
    """

    global _last_request_at

    with _lock:
        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            now = monotonic()

            if _last_request_at is not None:
                elapsed = now - _last_request_at
                remaining = MIN_REQUEST_INTERVAL_SECONDS - elapsed

                if remaining > 0:
                    sleep(remaining)

            _last_request_at = monotonic()

            try:
                return operation()

            except Exception as exc:
                if (
                    not _is_rate_limit_error(exc)
                    or attempt >= MAX_RATE_LIMIT_RETRIES
                ):
                    raise

                retry_delay = _get_retry_delay(exc)

                sleep(retry_delay)

    raise RuntimeError("Unexpected rate-limit controller failure.")
