"""K线模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Bar:
    """K线数据。"""

    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
