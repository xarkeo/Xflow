"""基金 API（多资产分组）。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..common._utils import path_part
from ..converters import DAILY_COLUMNS, collection


class FundAPI:
    """基金数据 API。

    用法：``client.fund.get_quote_history("510300")``
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def get_quote_history(self, symbol: str, *, exchange: str = "fund", cache: bool = True) -> pd.DataFrame:
        """基金日线。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/daily",
            {"exchange": exchange},
            cache=cache,
        )
        return collection(payload, "bars", columns=DAILY_COLUMNS)

    def get_nav_history(self, symbol: str, *, cache: bool = True) -> pd.DataFrame:
        """基金净值历史（占位，待 XFin 支持）。"""
        raise NotImplementedError("基金净值历史接口待 XFin 支持")
