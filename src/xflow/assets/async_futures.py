"""异步期货 API（多资产分组）。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..common._utils import path_part
from ..converters import DAILY_COLUMNS, collection


class AsyncFuturesAPI:
    """异步期货数据 API。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def get_quote_history(self, symbol: str, *, exch: str = "", cache: bool = True) -> pd.DataFrame:
        """期货日线。"""
        payload = await self._client._get(
            f"/securities/{path_part(symbol)}/daily",
            {"exchange": exch},
            cache=cache,
        )
        return collection(payload, "data", columns=DAILY_COLUMNS)
