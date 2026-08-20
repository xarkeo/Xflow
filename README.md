# Xarkeo

Pandas-first Python access to the Xarkeo market data API.

## Install

```bash
python -m pip install xarkeo
```

## Configure a token

Use an environment variable:

```bash
export XARKEO_TOKEN='xar_your_token'
```

Or set it in the current Python process:

```python
import xarkeo as xk

xk.set_token("xar_your_token")
```

The SDK never writes your token to disk.

## Query data

```python
import xarkeo as xk

latest = xk.latest_daily("000009", exchange="SSE")
bars = xk.daily("000009", exchange="SSE", start_date="2026-01-01")
quotes = xk.quotes(["000009:SSE", "000001:SSE"])

print(latest)
print(bars.head())
print(quotes)
```

All query functions return `pandas.DataFrame`. Single-resource endpoints return one row; empty collections retain stable baseline columns.

## Available functions

| Function | Description |
| --- | --- |
| `security(symbol, exchange=...)` | One security |
| `securities(exchange=..., page=..., page_size=...)` | Security page |
| `daily(symbol, exchange=..., ...)` | Daily bar page |
| `latest_daily(symbol, exchange=...)` | Latest daily bar |
| `actions(symbol, exchange=..., ...)` | Corporate-action page |
| `quotes(symbols)` | Current quotes for qualified symbols |
| `calendar(year)` | Trading calendar |

## Load history safely

Use an explicit client to stream or collect bounded pages:

```python
from xarkeo import XarkeoClient

with XarkeoClient("xar_your_token") as client:
    for page in client.iter_daily(
        "000009",
        exchange="SSE",
        page_size=500,
        max_pages=100,
    ):
        process(page)

    history = client.daily_all(
        "000009",
        exchange="SSE",
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
from xarkeo import AuthenticationError, RateLimitError, XarkeoError

try:
    data = xk.calendar(2026)
except AuthenticationError:
    print("Set XARKEO_TOKEN or call xarkeo.set_token(...).")
except RateLimitError as exc:
    print(exc.retry_after)
except XarkeoError as exc:
    print(exc)
```

## Advanced client options

`XarkeoClient` supports a timeout, an in-process GET cache, and a custom compatible API root for tests or private deployments:

```python
client = XarkeoClient(
    "xar_your_token",
    cache_ttl=30,
    timeout=15,
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
