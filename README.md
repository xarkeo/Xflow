# XFlow

Pandas-first Python access to the Xarkeo market data API.

## Install

```bash
python -m pip install xflow
```

## Configure a token

Use an environment variable:

```bash
export XARKEO_TOKEN='xar_your_token'
```

Or pass it to the client:

```python
from xflow import XflowClient as xk

client = xk("xar_your_token")
```

The SDK never writes your token to disk.

## Query data

### 多资产分组（推荐）

```python
from xflow import XflowClient as xk

client = xk("xar_your_token")

# 股票
bars = client.stock.get_quote_history("sh600519", beg="2024-01-01", end="2024-12-31")
securities = client.stock.get_securities()

# 基金 / 指数 / 债券 / 期货
fund_bars = client.fund.get_quote_history("510300")
index_bars = client.index.get_quote_history("sh000001")
bond_bars = client.bond.get_quote_history("sh010107")
futures_bars = client.futures.get_quote_history("CU1811")
```

### 兼容旧接口

```python
latest = client.latest_daily("sh600519", exch="sh")
bars = client.daily("sh600519", exch="sh", start_date="2024-01-01")
quotes = client.quotes(["sh600519", "sz000001"])
calendar = client.calendar(2024)
```

### 分页

```python
# 惰性逐页迭代
for page in client.stock.iter_daily("sh600519", page_size=100):
    process(page)

# 收集所有页
all_bars = client.stock.daily_all("sh600519", page_size=100)
```

### 异步

```python
import asyncio
from xflow import AsyncXflowClient as axk

async def main():
    client = axk("xar_your_token")
    bars = await client.stock.get_quote_history("sh600519")
    await client.close()

asyncio.run(main())
```

## 目录结构

采用标准 **src-layout**（`src/xflow/`），包名 `xflow` 与项目名一致：

```text
XFlow/
├── README.md
├── pyproject.toml
└── src/
    └── xflow/          # 包（import xflow）
        ├── __init__.py      # 公共 API 出口
        ├── client.py        # 门面：XflowClient / AsyncXflowClient
        ├── common/          # 通用层（认证/传输/重试/节流/缓存/分页/异常/配置/日志）
        ├── models/          # 数据模型（证券/K线/复权因子/交易日历/板块）
        ├── assets/          # 多资产 API（股票/基金/指数/债券/期货）
        └── converters.py    # 转换层（JSON → DataFrame / 模型）
```
```

All query functions return `pandas.DataFrame`. Single-resource endpoints return one row; empty collections retain stable baseline columns.

## Available functions

### 多资产分组（推荐）

| 函数 | 说明 |
| --- | --- |
| `client.stock.get_quote_history(symbol, ...)` | 股票日线 K 线 |
| `client.stock.get_securities(...)` | 证券列表 |
| `client.stock.get_latest_quote(symbol)` | 最新行情 |
| `client.fund.get_quote_history(symbol)` | 基金日线 |
| `client.index.get_quote_history(symbol)` | 指数日线 |
| `client.bond.get_quote_history(symbol)` | 债券日线 |
| `client.futures.get_quote_history(symbol)` | 期货日线 |

### 兼容旧接口

| 函数 | 说明 |
| --- | --- |
| `client.security(symbol, exch=...)` | 单个证券 |
| `client.securities(exch=..., page=..., page_size=...)` | 证券分页 |
| `client.daily(symbol, exch=..., ...)` | 日线分页 |
| `client.latest_daily(symbol, exch=...)` | 最新日线 |
| `client.actions(symbol, exch=..., ...)` | 公司行为分页 |
| `client.quotes(symbols)` | 实时行情 |
| `client.calendar(year)` | 交易日历 |

## Load history safely

Use an explicit client to stream or collect bounded pages:

```python
from xflow import XflowClient as xk

with xk("xar_your_token") as client:
    for page in client.stock.iter_daily(
        "sh600519",
        page_size=500,
        max_pages=100,
    ):
        process(page)

    history = client.stock.daily_all(
        "sh600519",
        page_size=500,
        max_pages=100,
    )
```

Pagination information is available in `DataFrame.attrs`:

```python
page.attrs
# {"page": 1, "page_size": 500, "total": 5250, "has_next": True}
```

## Errors

```python
from xflow import AuthenticationError, RateLimitError, XarkeoError

try:
    data = client.calendar(2026)
except AuthenticationError:
    print("Set XARKEO_TOKEN or pass token to XflowClient(...).")
except RateLimitError as exc:
    print(exc.retry_after)
except XarkeoError as exc:
    print(exc)
```

## Advanced client options

`XflowClient` supports a timeout, an in-process GET cache, client-side throttling, retry, and a custom compatible API root for tests or private deployments:

```python
from xflow import XflowClient as xk

client = xk(
    "xar_your_token",
    cache_ttl=30,          # 缓存 TTL（秒）
    timeout=15,            # 超时
    enable_throttle=True,  # 客户端节流（预防 429）
    retry_attempts=3,      # 重试次数
    raw_data=False,        # 返回原始 dict 或 DataFrame
)
```

Caching is disabled by default and never applies to `quotes()`.

## Documentation

- [Getting started](docs/getting-started.md)
- [API reference](docs/api-reference.md)
- [Pagination and caching](docs/performance.md)
- [Errors and FAQ](docs/errors-and-faq.md)
- [Migration from v0.5](MIGRATION.md)

## License

MIT. See [LICENSE](LICENSE).
