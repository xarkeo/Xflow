"""Process-local configuration and convenience query functions."""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import date, datetime
from threading import RLock

import pandas as pd

from .client import XarkeoClient
from .exceptions import ConfigurationError

_lock = RLock()
_token: str | None = None
_default_client: XarkeoClient | None = None


def set_token(token: str) -> None:
    """Set the process-wide token used by module-level query functions."""
    global _default_client, _token
    if not isinstance(token, str) or not token.strip():
        raise ConfigurationError("A non-empty Xarkeo API token is required.")
    with _lock:
        previous = _default_client
        _token = token.strip()
        _default_client = None
    if previous is not None:
        previous.close()


def get_token() -> str | None:
    """Return the process token or ``XARKEO_TOKEN`` when available."""
    with _lock:
        return _token or _environment_token()


def close() -> None:
    """Close the module-level default client, if created."""
    global _default_client
    with _lock:
        client = _default_client
        _default_client = None
    if client is not None:
        client.close()


def _client() -> XarkeoClient:
    global _default_client
    token = get_token()
    if token is None:
        raise ConfigurationError(
            "No Xarkeo token is configured. Set XARKEO_TOKEN or call xarkeo.set_token(...)."
        )
    with _lock:
        if _default_client is None:
            _default_client = XarkeoClient(token)
        return _default_client


def _environment_token() -> str | None:
    value = os.environ.get("XARKEO_TOKEN")
    return value.strip() if value and value.strip() else None


def security(symbol: str, *, exchange: str, cache: bool = True) -> pd.DataFrame:
    return _client().security(symbol, exchange=exchange, cache=cache)


def securities(
    *, exchange: str, page: int = 1, page_size: int = 100, cache: bool = True
) -> pd.DataFrame:
    return _client().securities(exchange=exchange, page=page, page_size=page_size, cache=cache)


def daily(
    symbol: str,
    *,
    exchange: str,
    page: int = 1,
    page_size: int = 100,
    start_date: date | datetime | str | None = None,
    end_date: date | datetime | str | None = None,
    cache: bool = True,
) -> pd.DataFrame:
    return _client().daily(
        symbol,
        exchange=exchange,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        cache=cache,
    )


def latest_daily(symbol: str, *, exchange: str, cache: bool = True) -> pd.DataFrame:
    return _client().latest_daily(symbol, exchange=exchange, cache=cache)


def actions(
    symbol: str,
    *,
    exchange: str,
    page: int = 1,
    page_size: int = 100,
    start_date: date | datetime | str | None = None,
    end_date: date | datetime | str | None = None,
    cache: bool = True,
) -> pd.DataFrame:
    return _client().actions(
        symbol,
        exchange=exchange,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        cache=cache,
    )


def quotes(symbols: Sequence[str]) -> pd.DataFrame:
    return _client().quotes(symbols)


def calendar(year: int, *, cache: bool = True) -> pd.DataFrame:
    return _client().calendar(year, cache=cache)
