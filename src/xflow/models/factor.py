"""复权因子模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdjustmentFactor:
    """复权因子。"""

    symbol: str
    date: str
    hfq_factor: float
