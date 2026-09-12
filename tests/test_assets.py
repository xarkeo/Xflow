"""XFlow 资产 API 测试（财务指标 + 指数成分股）。"""

import pandas as pd
import pytest

from xflow.assets.index import IndexAPI
from xflow.assets.stock import StockAPI


class FakeClient:
    """模拟 XflowClient，mock _get 返回预设 payload。"""

    def __init__(self, payload):
        self._payload = payload
        self._calls = []

    def _get(self, path, params, *, cache=True):
        self._calls.append((path, params))
        return self._payload


# ── 财务指标 ──

FINANCIAL_INDICATOR_PAYLOAD = {
    "data": [
        {
            "symbol": "sh600519",
            "report_date": "2026-06-30",
            "report_year": 2026,
            "report_quarter": 2,
            "known_at": "2026-08-15",
            "roe": 16.75,
            "roe_diluted": 17.72,
            "roe_avg": 17.95,
            "roa": 20.06,
            "gross_margin": 89.56,
            "net_margin": 50.75,
            "revenue_yoy": 1.30,
            "profit_yoy": -1.95,
            "debt_ratio": 15.19,
            "current_ratio": 5.59,
            "quick_ratio": 4.27,
            "equity_multiplier": 1.24,
            "receivable_turn": 57047.09,
            "inventory_turn": 0.15,
            "asset_turn": 0.30,
            "ocf_to_revenue": 0.78,
            "eps": 35.57,
            "bps": 200.99,
            "ocf_per_share": 56.55,
        }
    ],
    "total": 1,
}


def test_get_financial_indicators():
    """get_financial_indicators 返回完整指标列。"""
    client = FakeClient(FINANCIAL_INDICATOR_PAYLOAD)
    api = StockAPI(client)

    df = api.get_financial_indicators("sh600519")

    # 请求路径正确
    assert client._calls[0][0] == "/securities/sh600519/financials/indicators"

    # 返回 DataFrame 且列完整
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    expected_cols = {
        "symbol", "report_date", "report_year", "report_quarter", "known_at",
        "roe", "roe_diluted", "roe_avg", "roa", "gross_margin", "net_margin",
        "revenue_yoy", "profit_yoy",
        "debt_ratio", "current_ratio", "quick_ratio", "equity_multiplier",
        "receivable_turn", "inventory_turn", "asset_turn",
        "ocf_to_revenue",
        "eps", "bps", "ocf_per_share",
    }
    assert expected_cols.issubset(set(df.columns))

    # 数据正确
    row = df.iloc[0]
    assert row["symbol"] == "sh600519"
    assert row["roe"] == 16.75
    assert row["gross_margin"] == 89.56
    assert row["revenue_yoy"] == 1.30
    assert row["debt_ratio"] == 15.19
    assert row["asset_turn"] == 0.30
    assert row["eps"] == 35.57


def test_get_financial_indicators_empty():
    """get_financial_indicators 空数据返回空 DataFrame（保留基准列）。"""
    client = FakeClient({"data": [], "total": 0})
    api = StockAPI(client)

    df = api.get_financial_indicators("sh600519")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert "roe" in df.columns
    assert "gross_margin" in df.columns


# ── 指数成分股 ──

INDEX_CONSTITUENT_PAYLOAD = {
    "data": [
        {
            "index_code": "hs300",
            "index_name": "沪深300",
            "symbol": "sh600000",
            "name": "浦发银行",
            "effective_date": "2026-09-12",
        },
        {
            "index_code": "hs300",
            "index_name": "沪深300",
            "symbol": "sh600009",
            "name": "上海机场",
            "effective_date": "2026-09-12",
        },
    ],
    "total": 2,
}


def test_get_index_constituents():
    """get_constituents 返回指数成分股。"""
    client = FakeClient(INDEX_CONSTITUENT_PAYLOAD)
    api = IndexAPI(client)

    df = api.get_constituents("hs300")

    # 请求路径正确
    assert client._calls[0][0] == "/index/hs300/constituents"

    # 返回 DataFrame 且列完整
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    expected_cols = {"index_code", "index_name", "symbol", "name", "effective_date"}
    assert expected_cols.issubset(set(df.columns))

    # 数据正确
    assert df.iloc[0]["symbol"] == "sh600000"
    assert df.iloc[0]["name"] == "浦发银行"
    assert df.iloc[1]["symbol"] == "sh600009"


def test_get_indices():
    """get_indices 返回指数列表。"""
    payload = {
        "data": [
            {"index_code": "hs300", "index_name": "沪深300", "effective_date": "2026-09-12"},
            {"index_code": "sz50", "index_name": "上证50", "effective_date": "2026-09-12"},
            {"index_code": "zz500", "index_name": "中证500", "effective_date": "2026-09-12"},
        ],
        "total": 3,
    }
    client = FakeClient(payload)
    api = IndexAPI(client)

    df = api.get_indices()

    assert client._calls[0][0] == "/index"
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert set(df["index_code"]) == {"hs300", "sz50", "zz500"}


# ── 周期 K 线 ──

PERIOD_BAR_PAYLOAD = {
    "data": [
        {"symbol": "sh600519", "date": "2026-09-07", "open": 1324.0, "high": 1333.6,
         "low": 1263.01, "close": 1275.16, "volume": 1000, "amount": 1.2e9},
        {"symbol": "sh600519", "date": "2026-08-31", "open": 1297.99, "high": 1338.86,
         "low": 1286.0, "close": 1330.0, "volume": 2000, "amount": 2.3e9},
    ],
    "total": 2,
}


def test_get_quote_history_period():
    """get_quote_history 支持 frequency 周期 K 线。"""
    client = FakeClient(PERIOD_BAR_PAYLOAD)
    api = StockAPI(client)

    df = api.get_quote_history("sh600519", frequency="w")

    # 请求路径为 /period，且带 period 参数
    path, params = client._calls[0]
    assert path == "/securities/sh600519/period"
    assert params["period"] == "w"

    # 返回 DataFrame
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert df.iloc[0]["date"] == "2026-09-07"
    assert df.iloc[0]["close"] == 1275.16


def test_get_quote_history_daily_default():
    """get_quote_history 默认 frequency=d 走日线接口。"""
    client = FakeClient(PERIOD_BAR_PAYLOAD)
    api = StockAPI(client)

    df = api.get_quote_history("sh600519")

    # 默认走 /daily 接口
    path, _ = client._calls[0]
    assert path == "/securities/sh600519/daily"
    assert isinstance(df, pd.DataFrame)


# ── 龙虎榜 ──

BILLBOARD_PAYLOAD = {
    "data": [
        {"trade_date": "2024-06-07", "symbol": "sz300817", "name": "双飞集团",
         "close_price": 20.02, "change_rate": 20.02, "turnover_rate": 30.0,
         "buy_amount": 1.2e8, "sell_amount": 5.8e7, "net_amount": 6.2e7,
         "accum_amount": 1.8e8, "explanation": "日涨幅达到15%的前5只证券"},
        {"trade_date": "2024-06-07", "symbol": "sh600724", "name": "宁波富达",
         "close_price": 10.0, "change_rate": 10.0, "turnover_rate": 15.0,
         "buy_amount": 8.0e7, "sell_amount": 2.4e7, "net_amount": 5.6e7,
         "accum_amount": 1.0e8, "explanation": "连续三个交易日涨幅偏离值累计达到20%"},
    ],
    "total": 2,
}


def test_get_billboard():
    """get_billboard 返回指定日期龙虎榜。"""
    client = FakeClient(BILLBOARD_PAYLOAD)
    api = StockAPI(client)

    df = api.get_billboard("2024-06-07")

    # 请求路径正确
    path, params = client._calls[0]
    assert path == "/billboard"
    assert params["date"] == "2024-06-07"

    # 返回 DataFrame 且列完整
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    expected_cols = {
        "trade_date", "symbol", "name", "close_price", "change_rate",
        "turnover_rate", "buy_amount", "sell_amount", "net_amount",
        "accum_amount", "explanation",
    }
    assert expected_cols.issubset(set(df.columns))

    # 数据正确
    assert df.iloc[0]["symbol"] == "sz300817"
    assert df.iloc[0]["name"] == "双飞集团"
    assert df.iloc[0]["net_amount"] == 6.2e7


def test_get_billboard_by_symbol():
    """get_billboard_by_symbol 返回指定股票历史龙虎榜。"""
    client = FakeClient(BILLBOARD_PAYLOAD)
    api = StockAPI(client)

    df = api.get_billboard_by_symbol("sz300817", limit=10)

    path, params = client._calls[0]
    assert path == "/securities/sz300817/billboard"
    assert params["limit"] == 10
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
