"""XFlow 内部工具。"""

from __future__ import annotations

from datetime import date, datetime
from urllib.parse import quote


def path_part(value: str) -> str:
    """URL 路径片段转义。"""
    return quote(nonempty_string(value, "symbol"), safe="")


def exchange(value: str) -> str:
    """校验并返回交易所代码。"""
    return nonempty_string(value, "exchange")


def nonempty_string(value: str, name: str) -> str:
    """校验非空字符串。"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def positive_int(value: int, name: str) -> int:
    """校验正整数。"""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def date_value(value: date | datetime | str | None) -> str | None:
    """日期转 ISO 字符串。"""
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
