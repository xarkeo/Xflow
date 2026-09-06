"""XFlow 门面：XflowClient（同步）+ AsyncXflowClient（异步）。

用户唯一入口，组合各层（认证/传输/重试/节流/缓存/分页）和多资产 API。
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from datetime import date, datetime
from json import dumps
from threading import RLock
from typing import Any

import httpx
import pandas as pd

from .assets import (
    AsyncBondAPI,
    AsyncFundAPI,
    AsyncFuturesAPI,
    AsyncIndexAPI,
    AsyncStockAPI,
    BondAPI,
    FundAPI,
    FuturesAPI,
    IndexAPI,
    StockAPI,
)
from .common import ConfigurationError
from .common._utils import date_value, exchange, nonempty_string, path_part, positive_int
from .common.auth import Auth
from .common.cache import CacheInfo, TTLCache
from .common.pagination import collect_pages, iterate_pages, with_page_attrs
from .common.retry import RetryPolicy
from .common.throttle import Throttler
from .common.transport import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, Transport
from .converters import (
    ACTION_COLUMNS,
    BLOCK_COLUMNS,
    BLOCK_MEMBER_COLUMNS,
    CALENDAR_COLUMNS,
    DAILY_COLUMNS,
    QUOTE_COLUMNS,
    SECURITY_COLUMNS,
    collection,
    to_frame,
)

__all__ = [
    "XflowClient",
    "AsyncXflowClient",
]


class XflowClient:
    """XFlow 数据 API 客户端（同步）。

    用法：:

        client = XflowClient("xar_xxx")
        # 多资产分组
        client.stock.get_quote_history("sh600519")
        client.fund.get_quote_history("510300")
        # 兼容旧接口
        client.daily("sh600519", exchange="sh")
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        cache_ttl: float = 0.0,
        enable_throttle: bool = True,
        retry_attempts: int = 3,
        raw_data: bool = False,
        disk_cache_dir: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if cache_ttl < 0:
            raise ConfigurationError("cache_ttl must be greater than or equal to zero.")

        self._auth = Auth(token)
        self._transport = Transport(base_url, timeout, http_client)
        self._retry = RetryPolicy(attempts=retry_attempts)
        self._throttle = Throttler(enabled=enable_throttle)
        self._cache = TTLCache(disk_dir=disk_cache_dir)
        self._cache_ttl = cache_ttl
        self._raw_data = raw_data
        self._closed = False
        self._state_lock = RLock()

        # 多资产分组
        self.stock = StockAPI(self)
        self.fund = FundAPI(self)
        self.index = IndexAPI(self)
        self.bond = BondAPI(self)
        self.futures = FuturesAPI(self)

    def __enter__(self) -> XflowClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """关闭连接池。"""
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            self._transport.close()

    def clear_cache(self) -> None:
        """清空缓存。"""
        self._cache.clear()

    def cache_info(self) -> CacheInfo:
        """缓存计数。"""
        return self._cache.info()

    # ════════════════════════════════════════════════════════════
    # 兼容旧接口（保留）
    # ════════════════════════════════════════════════════════════

    def security(self, symbol: str, *, exchange: str, cache: bool = True) -> pd.DataFrame:
        """单个证券。"""
        payload = self._get(
            f"/securities/{path_part(symbol)}",
            {"exchange": nonempty_string(exchange, "exchange")},
            cache=cache,
        )
        return to_frame(payload, columns=SECURITY_COLUMNS)

    def securities(
        self,
        *,
        exchange: str,
        page: int = 1,
        page_size: int = 100,
        cache: bool = True,
    ) -> pd.DataFrame:
        """证券列表。"""
        payload = self._get(
            "/securities",
            {"exchange": nonempty_string(exchange, "exchange"), "page": positive_int(page, "page"), "page_size": positive_int(page_size, "page_size")},
            cache=cache,
        )
        return with_page_attrs(collection(payload, "data", columns=SECURITY_COLUMNS), payload)

    def daily(
        self,
        symbol: str,
        *,
        exch: str = "",
        page: int = 1,
        page_size: int = 100,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
        cache: bool = True,
    ) -> pd.DataFrame:
        """日线（兼容旧接口）。"""
        payload = self._get(
            f"/securities/{path_part(symbol)}/daily",
            {
                "exchange": exchange(exch) if exch else "",
                "page": positive_int(page, "page"),
                "page_size": positive_int(page_size, "page_size"),
                "start": date_value(start_date),
                "end": date_value(end_date),
            },
            cache=cache,
        )
        return with_page_attrs(collection(payload, "data", columns=DAILY_COLUMNS), payload)

    def latest_daily(self, symbol: str, *, exchange: str, cache: bool = True) -> pd.DataFrame:
        """最新日线。"""
        payload = self._get(
            f"/securities/{path_part(symbol)}/daily/latest",
            {"exchange": nonempty_string(exchange, "exchange")},
            cache=cache,
        )
        return to_frame(payload, columns=DAILY_COLUMNS)

    def actions(
        self,
        symbol: str,
        *,
        exchange: str,
        page: int = 1,
        page_size: int = 100,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
        cache: bool = True,
    ) -> pd.DataFrame:
        """公司行为。"""
        payload = self._get(
            f"/securities/{path_part(symbol)}/actions",
            _page_params(exchange, page, page_size, start_date, end_date),
            cache=cache,
        )
        return with_page_attrs(collection(payload, "actions", columns=ACTION_COLUMNS), payload)

    def iter_daily(
        self,
        symbol: str,
        *,
        exchange: str,
        page_size: int = 100,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
        max_pages: int = 100,
        cache: bool = True,
    ) -> Iterator[pd.DataFrame]:
        """惰性逐页迭代日线。"""
        yield from iterate_pages(
            lambda page: self.daily(symbol, exch=exchange, page=page, page_size=page_size, start_date=start_date, end_date=end_date, cache=cache),
            page_size=page_size,
            max_pages=max_pages,
        )

    def daily_all(
        self,
        symbol: str,
        *,
        exchange: str,
        page_size: int = 100,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
        max_pages: int = 100,
        cache: bool = True,
    ) -> pd.DataFrame:
        """收集所有日线页。"""
        return collect_pages(
            self.iter_daily(symbol, exchange=exchange, page_size=page_size, start_date=start_date, end_date=end_date, max_pages=max_pages, cache=cache),
            columns=DAILY_COLUMNS,
            max_pages=max_pages,
        )

    def iter_actions(
        self,
        symbol: str,
        *,
        exchange: str,
        page_size: int = 100,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
        max_pages: int = 100,
        cache: bool = True,
    ) -> Iterator[pd.DataFrame]:
        """惰性逐页迭代公司行为。"""
        yield from iterate_pages(
            lambda page: self.actions(symbol, exchange=exchange, page=page, page_size=page_size, start_date=start_date, end_date=end_date, cache=cache),
            page_size=page_size,
            max_pages=max_pages,
        )

    def actions_all(
        self,
        symbol: str,
        *,
        exchange: str,
        page_size: int = 100,
        start_date: date | datetime | str | None = None,
        end_date: date | datetime | str | None = None,
        max_pages: int = 100,
        cache: bool = True,
    ) -> pd.DataFrame:
        """收集所有公司行为页。"""
        return collect_pages(
            self.iter_actions(symbol, exchange=exchange, page_size=page_size, start_date=start_date, end_date=end_date, max_pages=max_pages, cache=cache),
            columns=ACTION_COLUMNS,
            max_pages=max_pages,
        )

    def quotes(self, symbols: Sequence[str]) -> pd.DataFrame:
        """实时行情。"""
        normalized = [exchange(symbol) for symbol in symbols]
        if not normalized:
            raise ValueError("symbols must contain at least one symbol.")
        payload = self._request("POST", "/quotes", json={"symbols": normalized})
        return collection(payload, "quotes", columns=QUOTE_COLUMNS)

    def calendar(self, year: int, *, cache: bool = True) -> pd.DataFrame:
        """交易日历（兼容旧接口）。"""
        payload = self._get("/calendar", {"year": positive_int(year, "year")}, cache=cache)
        return collection(payload, "calendars", columns=CALENDAR_COLUMNS)

    # ── 通用（跨资产）──
    def get_trading_days(self, year: int, *, cache: bool = True) -> pd.DataFrame:
        """交易日历（XFin /calendar/trading-days）。"""
        payload = self._get("/calendar/trading-days", {"year": positive_int(year, "year")}, cache=cache)
        return collection(payload, "data", columns=CALENDAR_COLUMNS)

    def is_trading_day(self, date: str, *, cache: bool = True) -> bool:
        """是否交易日。"""
        payload = self._get("/calendar/is-trading-day", {"date": date}, cache=cache)
        return bool(payload.get("is_trading_day", False))

    def get_blocks(self, *, cache: bool = True) -> pd.DataFrame:
        """板块列表。"""
        payload = self._get("/blocks", {}, cache=cache)
        return collection(payload, "data", columns=BLOCK_COLUMNS)

    def get_block_members(self, code: str, *, cache: bool = True) -> pd.DataFrame:
        """板块成员。"""
        payload = self._get(f"/blocks/{path_part(code)}/members", {}, cache=cache)
        return collection(payload, "data", columns=BLOCK_MEMBER_COLUMNS)

    # 别名
    trade_cal = get_trading_days  # tushare
    get_members = get_block_members  # efinance

    # ════════════════════════════════════════════════════════════
    # 内部请求管线
    # ════════════════════════════════════════════════════════════

    def _get(self, path: str, params: Mapping[str, Any], *, cache: bool) -> dict[str, Any]:
        clean_params = {key: value for key, value in params.items() if value is not None}
        if not cache or self._cache_ttl <= 0:
            return self._request("GET", path, params=clean_params)
        return self._cache.get_or_set(
            self._cache_key(path, clean_params),
            self._cache_ttl,
            lambda: self._request("GET", path, params=clean_params),
        )

    def _cache_key(self, path: str, params: Mapping[str, Any]) -> str:
        serialized = dumps({"path": path, "params": params}, sort_keys=True, default=str)
        scope = self._auth.cache_scope()
        return f"{scope}:{serialized}"

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        with self._state_lock:
            if self._closed:
                raise ConfigurationError("This XflowClient is closed.")
        # 节流（预防服务端 429）
        self._throttle.throttle()
        # 认证注入
        headers = self._auth.apply({"Accept": "application/json"})
        # 重试执行
        return self._retry.execute(
            lambda: self._transport.request(method, path, headers=headers, **kwargs)
        )


class AsyncXflowClient:
    """XFlow 数据 API 客户端（异步）。

    用法：::

        client = AsyncXflowClient("xar_xxx")
        await client.stock.get_quote_history("sh600519")
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        cache_ttl: float = 0.0,
        enable_throttle: bool = True,
        retry_attempts: int = 3,
        raw_data: bool = False,
        disk_cache_dir: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if cache_ttl < 0:
            raise ConfigurationError("cache_ttl must be greater than or equal to zero.")

        self._auth = Auth(token)
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={"Accept": "application/json"},
            timeout=timeout,
            http2=_http2_available(),
        )
        self._cache_ttl = cache_ttl
        self._cache = TTLCache(disk_dir=disk_cache_dir)
        self._raw_data = raw_data
        self._closed = False

        # 多资产分组（异步）
        self.stock = AsyncStockAPI(self)
        self.fund = AsyncFundAPI(self)
        self.index = AsyncIndexAPI(self)
        self.bond = AsyncBondAPI(self)
        self.futures = AsyncFuturesAPI(self)

    async def close(self) -> None:
        if self._owns_http_client and not self._closed:
            await self._http.aclose()
            self._closed = True

    async def _get(self, path: str, params: Mapping[str, Any], *, cache: bool) -> dict[str, Any]:
        """异步 GET（带缓存）。"""
        clean_params = {key: value for key, value in params.items() if value is not None}
        if not cache or self._cache_ttl <= 0:
            return await self._request("GET", path, params=clean_params)
        return self._cache.get_or_set(
            self._cache_key(path, clean_params),
            self._cache_ttl,
            lambda: self._request("GET", path, params=clean_params),
        )

    def _cache_key(self, path: str, params: Mapping[str, Any]) -> str:
        from json import dumps

        serialized = dumps({"path": path, "params": params}, sort_keys=True, default=str)
        scope = self._auth.cache_scope()
        return f"{scope}:{serialized}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if self._closed:
            raise ConfigurationError("This AsyncXflowClient is closed.")
        headers = self._auth.apply({"Accept": "application/json"})
        response = await self._http.request(method, path, headers=headers, **kwargs)
        if response.is_error:
            Transport._raise_api_error(response)
        return response.json()


def _page_params(
    exch: str,
    page: int,
    page_size: int,
    start_date: date | datetime | str | None,
    end_date: date | datetime | str | None,
) -> dict[str, object]:
    return {
        "exchange": exchange(exch) if exch else "",
        "page": positive_int(page, "page"),
        "page_size": positive_int(page_size, "page_size"),
        "start_date": date_value(start_date),
        "end_date": date_value(end_date),
    }


def _http2_available() -> bool:
    """检查 h2 包是否可用（http2 需要）。"""
    try:
        import h2  # noqa: F401

        return True
    except ImportError:
        return False
