"""股票 API（多资产分组）。

函数命名与开源库（efinance/akshare/tushare）兼容。
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

import pandas as pd

from ..common._utils import date_value, exchange, path_part, positive_int
from ..common.pagination import collect_pages, iterate_pages, with_page_attrs
from ..converters import (
    ADJUSTMENT_FACTOR_COLUMNS,
    BILLBOARD_COLUMNS,
    DAILY_COLUMNS,
    FINANCIAL_INDICATOR_COLUMNS,
    MINUTE_COLUMNS,
    SECURITY_COLUMNS,
    collection,
    to_frame,
)


class StockAPI:
    """股票数据 API。

    用法：``client.stock.get_quote_history("sh600519")``
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    # ── 证券 ──
    def get_securities(self, *, page: int = 1, page_size: int = 100, cache: bool = True) -> pd.DataFrame:
        """证券列表。"""
        payload = self._client._get(
            "/securities",
            {"page": positive_int(page, "page"), "page_size": positive_int(page_size, "page_size")},
            cache=cache,
        )
        return collection(payload, "data", columns=SECURITY_COLUMNS)

    def get_security(self, symbol: str, *, exch: str = "", cache: bool = True) -> pd.DataFrame:
        """单个证券。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}",
            {"exchange": exchange(exch) if exch else ""},
            cache=cache,
        )
        return to_frame(payload, columns=SECURITY_COLUMNS)

    # ── 日线 K 线（核心）──
    def get_quote_history(
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
        """K 线（与 efinance/akshare 兼容）。

        frequency: d=日线, w=周线, m=月线, q=季线, y=年线（默认日线）。
        XFin daily 接口参数：start/end（日期过滤）。
        """
        # 周期 K 线走 /period 接口
        if frequency in ("w", "m", "q", "y"):
            payload = self._client._get(
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
            return with_page_attrs(collection(payload, "data", columns=DAILY_COLUMNS), payload)

        payload = self._client._get(
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
        return with_page_attrs(collection(payload, "data", columns=DAILY_COLUMNS), payload)

    def get_latest_quote(self, symbol: str, *, exch: str = "", cache: bool = True) -> pd.DataFrame:
        """最新日线。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/daily/latest",
            {"exchange": exchange(exch) if exch else ""},
            cache=cache,
        )
        return to_frame(payload, columns=DAILY_COLUMNS)

    # ── 复权因子 ──
    def get_adjustment_factors(
        self,
        symbol: str,
        *,
        beg: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
        cache: bool = True,
    ) -> pd.DataFrame:
        """复权因子。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/adjustment-factors",
            {"start": date_value(beg), "end": date_value(end)},
            cache=cache,
        )
        return collection(payload, "data", columns=ADJUSTMENT_FACTOR_COLUMNS)

    # ── 前复权日线 ──
    def get_qfq(
        self,
        symbol: str,
        *,
        beg: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
        cache: bool = True,
    ) -> pd.DataFrame:
        """前复权日线（v_stock_qfq 视图）。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/daily/qfq",
            {"start": date_value(beg), "end": date_value(end)},
            cache=cache,
        )
        return collection(payload, "data", columns=DAILY_COLUMNS)

    # ── 分钟线 ──
    def get_minute(
        self,
        symbol: str,
        *,
        beg: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
        cache: bool = True,
    ) -> pd.DataFrame:
        """分钟线。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/minute",
            {"start": date_value(beg), "end": date_value(end)},
            cache=cache,
        )
        return collection(payload, "data", columns=MINUTE_COLUMNS)

    # ── 财务 / 特征 / 筹码 ──
    def get_financials(self, symbol: str, *, cache: bool = True) -> pd.DataFrame:
        """财务报表。"""
        payload = self._client._get(f"/securities/{path_part(symbol)}/financials", {}, cache=cache)
        return collection(payload, "data", columns=("symbol", "report_date"))

    def get_financial_indicators(self, symbol: str, *, cache: bool = True) -> pd.DataFrame:
        """财务指标（盈利能力/成长/偿债/营运/收益质量/每股）。

        对应 baostock 的季频财务指标（query_profit_data / query_growth_data 等）。
        """
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/financials/indicators", {}, cache=cache
        )
        return collection(payload, "data", columns=FINANCIAL_INDICATOR_COLUMNS)

    def get_features(self, symbol: str, *, cache: bool = True) -> pd.DataFrame:
        """特征快照。"""
        payload = self._client._get(f"/securities/{path_part(symbol)}/features", {}, cache=cache)
        return collection(payload, "data", columns=("symbol", "date"))

    def get_chip(self, symbol: str, *, cache: bool = True) -> pd.DataFrame:
        """筹码分布快照。"""
        payload = self._client._get(f"/securities/{path_part(symbol)}/chip", {}, cache=cache)
        return collection(payload, "data", columns=("symbol", "date"))

    # ── 龙虎榜 ──
    def get_billboard(self, date: str, *, cache: bool = True) -> pd.DataFrame:
        """指定日期的龙虎榜（对应 efinance get_billboard_data）。

        date: YYYY-MM-DD
        """
        payload = self._client._get("/billboard", {"date": date}, cache=cache)
        return collection(payload, "data", columns=BILLBOARD_COLUMNS)

    def get_billboard_by_symbol(self, symbol: str, *, limit: int = 20, cache: bool = True) -> pd.DataFrame:
        """指定股票的历史龙虎榜。"""
        payload = self._client._get(
            f"/securities/{path_part(symbol)}/billboard", {"limit": limit}, cache=cache
        )
        return collection(payload, "data", columns=BILLBOARD_COLUMNS)

    def iter_daily(
        self,
        symbol: str,
        *,
        exch: str = "",
        page_size: int = 100,
        beg: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
        max_pages: int = 100,
        cache: bool = True,
    ) -> Iterator[pd.DataFrame]:
        """惰性逐页迭代日线。"""
        yield from iterate_pages(
            lambda page: self.get_quote_history(
                symbol, exch=exch, page=page, page_size=page_size, beg=beg, end=end, cache=cache
            ),
            page_size=page_size,
            max_pages=max_pages,
        )

    def daily_all(
        self,
        symbol: str,
        *,
        exch: str = "",
        page_size: int = 100,
        beg: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
        max_pages: int = 100,
        cache: bool = True,
    ) -> pd.DataFrame:
        """收集所有日线页为一个 DataFrame。"""
        return collect_pages(
            self.iter_daily(symbol, exch=exch, page_size=page_size, beg=beg, end=end, max_pages=max_pages, cache=cache),
            columns=DAILY_COLUMNS,
            max_pages=max_pages,
        )

    # ── 别名（兼容 akshare/tushare/efinance）──
    stock_zh_a_hist = get_quote_history  # akshare
    get_hist_data = get_quote_history  # tushare
    get_realtime_quotes = get_latest_quote  # efinance
    get_base_info = get_securities  # efinance
    get_stock_basics = get_securities  # tushare
    stock_info_a_code_name = get_securities  # akshare
    get_h_data = get_adjustment_factors  # tushare 复权数据
