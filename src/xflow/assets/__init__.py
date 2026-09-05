"""XFlow 多资产 API（按资产类别分组）。"""

from .async_bond import AsyncBondAPI
from .async_fund import AsyncFundAPI
from .async_futures import AsyncFuturesAPI
from .async_index import AsyncIndexAPI
from .async_stock import AsyncStockAPI
from .bond import BondAPI
from .fund import FundAPI
from .futures import FuturesAPI
from .index import IndexAPI
from .stock import StockAPI

__all__ = [
    "StockAPI",
    "FundAPI",
    "IndexAPI",
    "BondAPI",
    "FuturesAPI",
    "AsyncStockAPI",
    "AsyncFundAPI",
    "AsyncIndexAPI",
    "AsyncBondAPI",
    "AsyncFuturesAPI",
]
