"""指数 API（多资产分组）。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..common._utils import path_part
from ..converters import DAILY_COLUMNS, INDEX_CONSTITUENT_COLUMNS, collection


class IndexAPI:
    """指数数据 API。

    用法：``client.index.get_quote_history("sh000001")``
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def get_quote_history(self, symbol: str, *, exchange: str = "index", cache: bool = True) -> pd.DataFrame:
        """指数日线。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/daily",
            {"exchange": exchange},
            cache=cache,
        )
        return collection(payload, "bars", columns=DAILY_COLUMNS)

    def get_constituents(self, code: str, *, cache: bool = True) -> pd.DataFrame:
        """指数成分股（沪深300/上证50/中证500）。

        对应 baostock 的 query_hs300_stocks / query_sz50_stocks / query_zz500_stocks。
        code: hs300 / sz50 / zz500
        """
        payload = self._client._get(f"/index/{path_part(code)}/constituents", {}, cache=cache)
        return collection(payload, "data", columns=INDEX_CONSTITUENT_COLUMNS)

    def get_indices(self, *, cache: bool = True) -> pd.DataFrame:
        """已收录的指数列表。"""
        payload = self._client._get("/index", {}, cache=cache)
        return collection(payload, "data", columns=INDEX_CONSTITUENT_COLUMNS)
