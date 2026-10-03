# PROJECT KNOWLEDGE BASE

**Updated:** 2026-09-28

## OVERVIEW

XFlow 是 Xarkeo 官方出品的 **Python 客户端 SDK**（Pandas-first），面向第三方用户访问 Xarkeo 市场数据 API。已发布到 PyPI（`xarkeo-xflow` v1.0.0）。

## STRUCTURE

```
./
├── src/xflow/
│   ├── client.py          # XflowClient 主入口
│   ├── converters.py      # 响应 → pandas.DataFrame 转换
│   ├── models/            # 数据模型（security/calendar/factor/bar/block）
│   └── common/            # 通用能力
│       ├── auth.py        # Token 认证
│       ├── transport.py   # HTTP 传输
│       ├── cache.py       # 缓存
│       ├── retry.py       # 重试
│       ├── throttle.py    # 限流
│       ├── pagination.py  # 分页
│       ├── config.py      # 配置
│       ├── errors.py      # 异常
│       └── logging.py     # 日志
├── tests/                 # 测试
├── dist/                  # 构建产物
└── pyproject.toml         # 打包配置
```

## 使用方式

```python
from xflow import XflowClient as xk

client = xk(token="xar_xxx")  # 或环境变量 XARKEO_TOKEN
df = client.get_daily("sh600519", start="2024-01-01")
```

## 开发约定

- **Pandas-first**：所有数据接口返回 `pandas.DataFrame`
- **Token 认证**：形如 `xar_xxx`，通过 `XARKEO_TOKEN` 环境变量或构造参数传入
- **标的代码格式**：`sh600519` / `sz000001`（非 `600000.SSE`）
- **行情字段**：`price` / `close`（非 `last` / `pct_chg`）

## 未实现（规划中）

- **Go SDK**（`DataClient` 接口）—— 面向工程用户，尚未实现
- 详见 `xarkeo-doc/XFlow/XFlow_architecture.md` §4.3

## 相关文档

- 架构：`xarkeo-doc/XFlow/XFlow_architecture.md`
- 官网 SDK 文档：`website/app/docs/`（SDK 导向）
