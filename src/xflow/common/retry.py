"""XFlow 重试层：429/5xx 指数退避重试，尊重 Retry-After。"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from .errors import RateLimitError, TransportError

T = TypeVar("T")

DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_WAIT_SECONDS = 1.0
DEFAULT_RETRY_CODES = (429, 500, 502, 503, 504)


class RetryPolicy:
    """重试策略：429 尊重 Retry-After，5xx 指数退避 + 抖动。"""

    def __init__(
        self,
        attempts: int = DEFAULT_RETRY_ATTEMPTS,
        wait_seconds: float = DEFAULT_RETRY_WAIT_SECONDS,
        retry_codes: tuple[int, ...] = DEFAULT_RETRY_CODES,
    ) -> None:
        self._attempts = max(1, attempts)
        self._wait = max(0.0, wait_seconds)
        self._retry_codes = retry_codes

    def execute(self, fn: Callable[[], T]) -> T:
        """执行 fn，遇可重试错误按策略重试。"""
        last_error: Exception | None = None
        for attempt in range(self._attempts):
            try:
                return fn()
            except RateLimitError as exc:
                last_error = exc
                if attempt >= self._attempts - 1:
                    raise
                wait = exc.retry_after if exc.retry_after is not None else self._backoff(attempt)
                time.sleep(wait)
            except TransportError as exc:
                last_error = exc
                if attempt >= self._attempts - 1:
                    raise
                time.sleep(self._backoff(attempt))
        raise last_error  # pragma: no cover

    def _backoff(self, attempt: int) -> float:
        """指数退避 + 抖动。"""
        base = self._wait * (2**attempt)
        return base * (0.5 + random.random() * 0.5)
