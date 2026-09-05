"""证券模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Security:
    """证券信息。"""

    symbol: str
    name: str
    exchange: str = ""
    status: str = ""
    created_at: str = ""
    updated_at: str = ""
