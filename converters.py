"""JSON-to-DataFrame conversion helpers with stable baseline schemas."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

SECURITY_COLUMNS = (
    "id",
    "symbol",
    "name",
    "exchange",
    "status",
    "created_at",
    "updated_at",
)
DAILY_COLUMNS = (
    "id",
    "security_id",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "source",
)
ACTION_COLUMNS = (
    "id",
    "security_id",
    "action_date",
    "action_type",
    "ex_date",
    "record_date",
    "payment_date",
    "cash_dividend",
    "stock_dividend",
    "split_ratio",
    "source",
)
QUOTE_COLUMNS = (
    "symbol",
    "exchange",
    "trade_date",
    "trade_time",
    "open",
    "high",
    "low",
    "price",
    "close",
    "volume",
    "amount",
    "source",
)
CALENDAR_COLUMNS = ("date", "exchange", "is_trading_day")


def to_frame(
    records: Iterable[Mapping[str, Any]] | Mapping[str, Any] | None,
    *,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    """Convert API records to a DataFrame with ordered known columns.

    Unknown fields are retained after the endpoint's documented baseline
    fields, so additions on the service do not silently disappear.
    """
    if records is None:
        rows: list[Mapping[str, Any]] = []
    elif isinstance(records, Mapping):
        rows = [records]
    else:
        rows = list(records)

    frame = pd.DataFrame.from_records(rows)
    extras = [column for column in frame.columns if column not in columns]
    return frame.reindex(columns=[*columns, *extras])


def collection(payload: Mapping[str, Any], key: str, *, columns: tuple[str, ...]) -> pd.DataFrame:
    """Extract an API collection field and convert it to a DataFrame."""
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise TypeError(f"Expected API field {key!r} to be a list, got {type(value).__name__}.")
    if not all(isinstance(item, Mapping) for item in value):
        raise TypeError(f"Expected every item in API field {key!r} to be an object.")
    return to_frame(value, columns=columns)
