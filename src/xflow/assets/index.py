"""指数 API（多资产分组）。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..common._utils import path_part
from ..converters import DAILY_COLUMNS, collection


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
