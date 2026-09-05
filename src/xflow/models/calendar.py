"""交易日历模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradingDay:
    """交易日。"""

    date: str
    is_trading: bool
    holiday_name: str = ""
