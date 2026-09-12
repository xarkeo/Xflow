"""异步指数 API（多资产分组）。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..common._utils import path_part
from ..converters import DAILY_COLUMNS, INDEX_CONSTITUENT_COLUMNS, collection


class AsyncIndexAPI:
    """异步指数数据 API。"""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def get_quote_history(self, symbol: str, *, exch: str = "", cache: bool = True) -> pd.DataFrame:
        """指数日线。"""
        payload = await self._client._get(
            f"/securities/{path_part(symbol)}/daily",
            {"exchange": exch},
            cache=cache,
        )
        return collection(payload, "data", columns=DAILY_COLUMNS)

    async def get_constituents(self, code: str, *, cache: bool = True) -> pd.DataFrame:
        """指数成分股（沪深300/上证50/中证500）。"""
        payload = await self._client._get(f"/index/{path_part(code)}/constituents", {}, cache=cache)
        return collection(payload, "data", columns=INDEX_CONSTITUENT_COLUMNS)

    async def get_indices(self, *, cache: bool = True) -> pd.DataFrame:
        """已收录的指数列表。"""
        payload = await self._client._get("/index", {}, cache=cache)
        return collection(payload, "data", columns=INDEX_CONSTITUENT_COLUMNS)
