"""异步股票 API（多资产分组）。

与 StockAPI 对应，但方法为 async def，内部 await 异步请求。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from ..common._utils import date_value, exchange, path_part, positive_int
from ..converters import (
    BILLBOARD_COLUMNS,
    DAILY_COLUMNS,
    FINANCIAL_INDICATOR_COLUMNS,
    SECURITY_COLUMNS,
    collection,
    to_frame,
)


class AsyncStockAPI:
    """异步股票数据 API。

    用法：``await client.stock.get_quote_history("sh600519")``
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    async def get_securities(self, *, page: int = 1, page_size: int = 100, cache: bool = True) -> pd.DataFrame:
        """证券列表。"""
        payload = await self._client._get(
            "/securities",
            {"page": positive_int(page, "page"), "page_size": positive_int(page_size, "page_size")},
            cache=cache,
        )
        return collection(payload, "data", columns=SECURITY_COLUMNS)

    async def get_quote_history(
        self,
        symbol: str,
        *,
        exch: str = "",
        beg: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
        frequency: str = "d",
        page: int = 1,
        page_size: int = 100,
        cache: bool = True,
    ) -> pd.DataFrame:
        """K 线（frequency: d=日线, w=周线, m=月线, q=季线, y=年线）。"""
        # 周期 K 线走 /period 接口
        if frequency in ("w", "m", "q", "y"):
            payload = await self._client._get(
                f"/securities/{path_part(symbol)}/period",
                {
                    "period": frequency,
                    "page": positive_int(page, "page"),
                    "page_size": positive_int(page_size, "page_size"),
                    "start": date_value(beg),
                    "end": date_value(end),
                },
                cache=cache,
            )
            return collection(payload, "data", columns=DAILY_COLUMNS)

        payload = await self._client._get(
            f"/securities/{path_part(symbol)}/daily",
            {
                "exchange": exchange(exch) if exch else "",
                "page": positive_int(page, "page"),
                "page_size": positive_int(page_size, "page_size"),
                "start": date_value(beg),
                "end": date_value(end),
            },
            cache=cache,
        )
        return collection(payload, "data", columns=DAILY_COLUMNS)

    async def get_latest_quote(self, symbol: str, *, exch: str = "", cache: bool = True) -> pd.DataFrame:
        """最新日线。"""
        payload = await self._client._get(
            f"/securities/{path_part(symbol)}/daily/latest",
            {"exchange": exchange(exch) if exch else ""},
            cache=cache,
        )
        return to_frame(payload, columns=DAILY_COLUMNS)

    async def get_financial_indicators(self, symbol: str, *, cache: bool = True) -> pd.DataFrame:
        """财务指标（盈利能力/成长/偿债/营运/收益质量/每股）。"""
        payload = await self._client._get(
            f"/securities/{path_part(symbol)}/financials/indicators", {}, cache=cache
        )
        return collection(payload, "data", columns=FINANCIAL_INDICATOR_COLUMNS)

    async def get_billboard(self, date: str, *, cache: bool = True) -> pd.DataFrame:
        """指定日期的龙虎榜。"""
        payload = await self._client._get("/billboard", {"date": date}, cache=cache)
        return collection(payload, "data", columns=BILLBOARD_COLUMNS)

    async def get_billboard_by_symbol(self, symbol: str, *, limit: int = 20, cache: bool = True) -> pd.DataFrame:
        """指定股票的历史龙虎榜。"""
        payload = await self._client._get(
            f"/securities/{path_part(symbol)}/billboard", {"limit": limit}, cache=cache
        )
        return collection(payload, "data", columns=BILLBOARD_COLUMNS)

    # 别名
    stock_zh_a_hist = get_quote_history
    get_hist_data = get_quote_history
    get_realtime_quotes = get_latest_quote
    get_stock_basics = get_securities
