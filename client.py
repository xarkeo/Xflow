"""Synchronous, pandas-first client for the Xarkeo API."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from json import dumps
from threading import RLock
from typing import Any
from urllib.parse import quote

import httpx
import pandas as pd

from .cache import CacheInfo, TTLCache
from .converters import (
    ACTION_COLUMNS,
    CALENDAR_COLUMNS,
    DAILY_COLUMNS,
    QUOTE_COLUMNS,
    SECURITY_COLUMNS,
    collection,
    to_frame,
)
from .exceptions import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    NotFoundError,
    PaginationError,
    RateLimitError,
    TransportError,
    ValidationError,
)

DEFAULT_BASE_URL = "https://api.xarkeo.com/api/v1"
DEFAULT_TIMEOUT = httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0)


@dataclass(frozen=True)
class _PageState:
    page: int | None
    page_size: int | None
    total: int | None
    has_next: bool | None


class XarkeoClient:
    """A reusable synchronous client for the Xarkeo market-data API.

    Args:
        token: Xarkeo personal access token. The SDK sends it only in the
            ``X-PAT`` request header and never includes it in errors.
        base_url: API root. The production default is normally appropriate;
            this parameter supports compatible deployments and tests.
        timeout: HTTPX timeout configuration or timeout seconds.
        cache_ttl: In-process TTL for idempotent GET payloads. ``0`` disables
            caching. Quotes are never cached.
        http_client: Existing HTTPX client whose lifecycle remains caller-owned.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        cache_ttl: float = 0.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not token or not token.strip():
            raise ConfigurationError("A non-empty Xarkeo API token is required.")
        if not isinstance(base_url, str) or not base_url.strip():
            raise ConfigurationError("base_url must be a non-empty URL.")
        if cache_ttl < 0:
            raise ConfigurationError("cache_ttl must be greater than or equal to zero.")

        self._token = token.strip()
        self._cache_ttl = cache_ttl
        self._cache = TTLCache()
        self._owns_http_client = http_client is None
        self._closed = False
        self._state_lock = RLock()
        self._http = http_client or httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers={"Accept": "application/json", "X-PAT": self._token},
            timeout=timeout,
            http2=True,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )

    def __enter__(self) -> XarkeoClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the internally owned connection pool."""
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            if self._owns_http_client:
                self._http.close()

    def clear_cache(self) -> None:
        """Remove all in-process cached GET payloads."""
        self._cache.clear()

    def cache_info(self) -> CacheInfo:
        """Return in-process cache counters."""
        return self._cache.info()

    def security(self, symbol: str, *, exchange: str, cache: bool = True) -> pd.DataFrame:
        """Return one security as a one-row DataFrame."""
        payload = self._get(
            f"/securities/{_path_part(symbol)}",
            {"exchange": _exchange(exchange)},
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
        """Return one page of securities."""
        payload = self._get(
            "/securities",
            {
                "exchange": _exchange(exchange),
                "page": _positive_int(page, "page"),
                "page_size": _positive_int(page_size, "page_size"),
            },
            cache=cache,
        )
        frame = collection(payload, "securities", columns=SECURITY_COLUMNS)
        return _with_page_attrs(frame, payload)

    def daily(
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
        """Return one page of daily bars, optionally filtered by inclusive dates."""
        payload = self._get(
            f"/securities/{_path_part(symbol)}/daily",
            _page_params(exchange, page, page_size, start_date, end_date),
            cache=cache,
        )
        return _with_page_attrs(collection(payload, "bars", columns=DAILY_COLUMNS), payload)

    def latest_daily(self, symbol: str, *, exchange: str, cache: bool = True) -> pd.DataFrame:
        """Return the latest daily bar as a one-row DataFrame."""
        payload = self._get(
            f"/securities/{_path_part(symbol)}/daily/latest",
            {"exchange": _exchange(exchange)},
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
        """Return one page of corporate actions, optionally filtered by dates."""
        payload = self._get(
            f"/securities/{_path_part(symbol)}/actions",
            _page_params(exchange, page, page_size, start_date, end_date),
            cache=cache,
        )
        return _with_page_attrs(collection(payload, "actions", columns=ACTION_COLUMNS), payload)

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
        """Yield bounded pages of daily bars."""
        yield from self._iterate_pages(
            lambda page: self.daily(
                symbol,
                exchange=exchange,
                page=page,
                page_size=page_size,
                start_date=start_date,
                end_date=end_date,
                cache=cache,
            ),
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
        """Collect bounded daily-bar pages into one DataFrame."""
        return self._collect_pages(
            self.iter_daily(
                symbol,
                exchange=exchange,
                page_size=page_size,
                start_date=start_date,
                end_date=end_date,
                max_pages=max_pages,
                cache=cache,
            ),
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
        """Yield bounded pages of corporate actions."""
        yield from self._iterate_pages(
            lambda page: self.actions(
                symbol,
                exchange=exchange,
                page=page,
                page_size=page_size,
                start_date=start_date,
                end_date=end_date,
                cache=cache,
            ),
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
        """Collect bounded corporate-action pages into one DataFrame."""
        return self._collect_pages(
            self.iter_actions(
                symbol,
                exchange=exchange,
                page_size=page_size,
                start_date=start_date,
                end_date=end_date,
                max_pages=max_pages,
                cache=cache,
            ),
            columns=ACTION_COLUMNS,
            max_pages=max_pages,
        )

    def quotes(self, symbols: Sequence[str]) -> pd.DataFrame:
        """Return current quotes for exchange-qualified symbols."""
        normalized = [_nonempty_string(symbol, "symbols item") for symbol in symbols]
        if not normalized:
            raise ValueError("symbols must contain at least one symbol.")
        payload = self._request("POST", "/quotes", json={"symbols": normalized})
        return collection(payload, "quotes", columns=QUOTE_COLUMNS)

    def calendar(self, year: int, *, cache: bool = True) -> pd.DataFrame:
        """Return a trading calendar for one year."""
        payload = self._get("/calendar", {"year": _positive_int(year, "year")}, cache=cache)
        return collection(payload, "calendars", columns=CALENDAR_COLUMNS)

    def _iterate_pages(
        self,
        fetch: Callable[[int], pd.DataFrame],
        *,
        page_size: int,
        max_pages: int,
    ) -> Iterator[pd.DataFrame]:
        validated_page_size = _positive_int(page_size, "page_size")
        validated_max_pages = _positive_int(max_pages, "max_pages")
        for expected_page in range(1, validated_max_pages + 1):
            frame = fetch(expected_page)
            state = _page_state(frame.attrs)
            if state.page is not None and state.page != expected_page:
                raise PaginationError(
                    f"Expected API page {expected_page}, but response declared page {state.page}."
                )
            yield frame
            if frame.empty or state.has_next is False:
                return
            if state.total is not None and expected_page * validated_page_size >= state.total:
                return
            if state.total is None and len(frame) < validated_page_size:
                return

    @staticmethod
    def _collect_pages(
        pages: Iterator[pd.DataFrame],
        *,
        columns: tuple[str, ...],
        max_pages: int,
    ) -> pd.DataFrame:
        frames = list(pages)
        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
        last = _page_state(frames[-1].attrs) if frames else _PageState(None, None, None, None)
        stopped_reason = "max_pages"
        if frames and frames[-1].empty:
            stopped_reason = "empty_page"
        elif last.has_next is False:
            stopped_reason = "total_reached" if last.total is not None else "short_page"
        elif last.total is not None and len(combined) >= last.total:
            stopped_reason = "total_reached"
        elif frames and last.total is None and len(frames[-1]) < (last.page_size or 0):
            stopped_reason = "short_page"
        combined.attrs = {
            "pages_fetched": len(frames),
            "rows_fetched": len(combined),
            "total": last.total,
            "complete": stopped_reason != "max_pages",
            "stopped_reason": stopped_reason,
        }
        return combined

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
        scope = sha256(self._token.encode("utf-8")).hexdigest()[:16]
        return f"{scope}:{serialized}"

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        with self._state_lock:
            if self._closed:
                raise ConfigurationError("This XarkeoClient is closed.")
        try:
            response = self._http.request(
                method,
                path,
                headers={"Accept": "application/json", "X-PAT": self._token},
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise TransportError("Unable to communicate with the Xarkeo API.") from exc
        if response.is_error:
            self._raise_api_error(response)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiError(
                "The Xarkeo API returned invalid JSON.",
                status_code=response.status_code,
                headers=response.headers,
            ) from exc
        if not isinstance(payload, dict):
            raise ApiError(
                "The Xarkeo API returned a JSON value other than an object.",
                status_code=response.status_code,
                response_data=payload,
                headers=response.headers,
            )
        return payload

    @staticmethod
    def _raise_api_error(response: httpx.Response) -> None:
        try:
            payload: Any = response.json()
        except ValueError:
            payload = response.text
        message = _api_message(payload, response.status_code)
        kwargs = {
            "status_code": response.status_code,
            "response_data": payload,
            "headers": response.headers,
        }
        if response.status_code in (401, 403):
            raise AuthenticationError(message, **kwargs)
        if response.status_code == 404:
            raise NotFoundError(message, **kwargs)
        if response.status_code == 422:
            raise ValidationError(message, **kwargs)
        if response.status_code == 429:
            raise RateLimitError(message, retry_after=_retry_after(response), **kwargs)
        raise ApiError(message, **kwargs)


def _page_params(
    exchange: str,
    page: int,
    page_size: int,
    start_date: date | datetime | str | None,
    end_date: date | datetime | str | None,
) -> dict[str, object]:
    return {
        "exchange": _exchange(exchange),
        "page": _positive_int(page, "page"),
        "page_size": _positive_int(page_size, "page_size"),
        "start_date": _date_value(start_date),
        "end_date": _date_value(end_date),
    }


def _with_page_attrs(frame: pd.DataFrame, payload: Mapping[str, Any]) -> pd.DataFrame:
    state = _payload_page_state(payload)
    frame.attrs = {
        "page": state.page,
        "page_size": state.page_size,
        "total": state.total,
        "has_next": state.has_next,
    }
    return frame


def _payload_page_state(payload: Mapping[str, Any]) -> _PageState:
    page = _metadata_positive_int(payload.get("page"))
    page_size = _metadata_positive_int(payload.get("page_size"))
    total = _metadata_nonnegative_int(payload.get("total"))
    if page is None or page_size is None or total is None:
        has_next = None
    else:
        has_next = page * page_size < total
    return _PageState(page, page_size, total, has_next)


def _page_state(attrs: Mapping[object, Any]) -> _PageState:
    return _PageState(
        _metadata_positive_int(attrs.get("page")),
        _metadata_positive_int(attrs.get("page_size")),
        _metadata_nonnegative_int(attrs.get("total")),
        attrs.get("has_next") if isinstance(attrs.get("has_next"), bool) else None,
    )


def _api_message(payload: Any, status_code: int) -> str:
    if isinstance(payload, Mapping):
        for key in ("message", "detail", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    return f"Xarkeo API returned HTTP {status_code}."


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    try:
        return max(0.0, float(value)) if value is not None else None
    except ValueError:
        return None


def _path_part(value: str) -> str:
    return quote(_nonempty_string(value, "symbol"), safe="")


def _exchange(value: str) -> str:
    return _nonempty_string(value, "exchange")


def _nonempty_string(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def _metadata_positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _metadata_nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _date_value(value: date | datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("Date strings must use ISO format YYYY-MM-DD.") from exc
    raise TypeError("Dates must be ISO strings, datetime.date, datetime.datetime, or None.")
