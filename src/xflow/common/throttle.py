"""XFlow 节流层：客户端侧主动控速（预防服务端 429）。

参考 CCXT Throttler：漏桶（leakyBucket）算法。
注意：节流是"预防"服务端限流，不是"执行"限流。限流执行在服务端。
"""

from __future__ import annotations

import threading
import time


class Throttler:
    """客户端侧节流器（漏桶算法）。

    每次请求前调用 throttle()，若距上次请求不足 rate_limit_ms 则等待。
    enable_throttle 关闭后不节流（用户自己负责限流）。
    """

    def __init__(self, enabled: bool = True, rate_limit_ms: float = 200.0) -> None:
        self._enabled = enabled
        self._rate_limit_ms = max(0.0, rate_limit_ms)
        self._last_request = 0.0
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_rate_limit_ms(self, ms: float) -> None:
        self._rate_limit_ms = max(0.0, ms)

    def throttle(self) -> None:
        """请求前调用：若未到允许间隔则等待。"""
        if not self._enabled or self._rate_limit_ms <= 0:
            return
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            wait = (self._rate_limit_ms / 1000.0) - elapsed
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
