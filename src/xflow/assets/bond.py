"""债券 API（多资产分组）。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..common._utils import path_part
from ..converters import DAILY_COLUMNS, collection


class BondAPI:
    """债券数据 API。

    用法：``client.bond.get_quote_history("sh010107")``
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def get_quote_history(self, symbol: str, *, exchange: str = "bond", cache: bool = True) -> pd.DataFrame:
        """债券日线。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/daily",
            {"exchange": exchange},
            cache=cache,
        )
        return collection(payload, "bars", columns=DAILY_COLUMNS)
