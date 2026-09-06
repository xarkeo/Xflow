# XFlow

[![PyPI version](https://img.shields.io/pypi/v/xflow.svg)](https://pypi.org/project/xflow/)
[![Python versions](https://img.shields.io/pypi/pyversions/xflow.svg)](https://pypi.org/project/xflow/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Pandas-first Python access to the Xarkeo market data API.**

XFlow 是 [Xarkeo](https://xarkeo.com) 官方出品的 Python 客户端，让你用几行代码就能获取 A 股、基金、指数、债券、期货等市场数据，并以 `pandas.DataFrame` 直接使用。

---

## 🚀 快速开始

### 1. 安装

```bash
python -m pip install xflow
```

### 2. 获取 Token（免费）

XFlow 是 Xarkeo 数据服务的客户端，**使用数据需要注册获取 Token**：

👉 **[免费注册获取 Token → https://xarkeo.com/register](https://xarkeo.com/register)**

注册后你会得到一个形如 `xar_xxx` 的 Token，用于访问行情数据。

### 3. 配置 Token

使用环境变量：

```bash
export XARKEO_TOKEN='xar_your_token'
```

或直接传给客户端：

```python
from xflow import XflowClient as xk

client = xk("xar_your_token")
```

> SDK 永远不会把 Token 写入磁盘。

### 4. 查询数据

```python
from xflow import XflowClient as xk

client = xk("xar_your_token")

# 股票日线 K 线
bars = client.stock.get_quote_history("sh600519", beg="2024-01-01", end="2024-12-31")
securities = client.stock.get_securities()

# 基金 / 指数 / 债券 / 期货
fund_bars = client.fund.get_quote_history("510300")
index_bars = client.index.get_quote_history("sh000001")
bond_bars = client.bond.get_quote_history("sh010107")
futures_bars = client.futures.get_quote_history("CU1811")
```

所有查询函数都返回 `pandas.DataFrame`，单资源接口返回一行，空集合保留稳定的基准列。

---

## 📦 功能特性

- **多资产支持**：股票、基金、指数、债券、期货
- **Pandas-first**：所有数据直接返回 `DataFrame`
- **同步 + 异步**：`XflowClient` / `AsyncXflowClient`
- **分页**：惰性逐页迭代，安全加载大历史
- **健壮性**：内置重试、节流、缓存、超时控制
- **类型安全**：严格类型标注，mypy strict 通过

---

## 📖 使用文档

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

### 安全加载历史数据

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

分页信息在 `DataFrame.attrs` 中：

```python
page.attrs
# {"page": 1, "page_size": 500, "total": 5250, "has_next": True}
```

### 错误处理

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

### 高级配置

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

缓存默认关闭，且永远不会应用于 `quotes()`。

---

## 🗂 目录结构

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

---

## 📚 文档

- [Getting started](docs/getting-started.md)
- [API reference](docs/api-reference.md)
- [Pagination and caching](docs/performance.md)
- [Errors and FAQ](docs/errors-and-faq.md)
- [Migration from v0.5](MIGRATION.md)

---

## 🤝 关于 Xarkeo

[Xarkeo](https://xarkeo.com) 是 AI 原生的金融智能平台，提供高质量的市场数据服务。XFlow 是它的官方 Python 客户端，开源以方便开发者快速接入。

- 🌐 官网：https://xarkeo.com
- 📖 API 文档：https://api.xarkeo.com
- ✉️ 注册获取 Token：https://xarkeo.com/register

## 📄 License

[MIT](LICENSE) © Xarkeo
