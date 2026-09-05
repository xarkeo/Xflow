"""XFlow 传输层：HTTP 请求、连接池、超时分级、拦截器。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .errors import ApiError, AuthenticationError, NotFoundError, RateLimitError, TransportError, ValidationError

DEFAULT_BASE_URL = "https://api.xarkeo.com/api/v1"
DEFAULT_TIMEOUT = httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0)


class Transport:
    """HTTP 传输层：管理连接池、超时、请求/响应拦截。"""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty URL.")
        self._base_url = base_url.rstrip("/") + "/"
        self._owns_http_client = http_client is None
        # http2 需要 h2 包，缺失时优雅降级为 http1.1
        http2 = _http2_available()
        self._http = http_client or httpx.Client(
            base_url=self._base_url,
            headers={"Accept": "application/json"},
            timeout=timeout,
            http2=http2,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )

    def request(self, method: str, path: str, headers: Mapping[str, str] | None = None, **kwargs: Any) -> dict[str, Any]:
        """发送请求，返回解析后的 JSON dict。"""
        try:
            response = self._http.request(method, path, headers=dict(headers or {}), **kwargs)
        except httpx.HTTPError as exc:
            raise TransportError("Unable to communicate with the Xarkeo API.") from exc
        if response.is_error:
            self._raise_api_error(response)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiError(
                "The Xarkeo API returned invalid JSON.",
                status_code=response.status_code,
                headers=response.headers,
            ) from exc
        if not isinstance(payload, dict):
            raise ApiError(
                "The Xarkeo API returned a JSON value other than an object.",
                status_code=response.status_code,
                response_data=payload,
                headers=response.headers,
            )
        return payload

    def close(self) -> None:
        if self._owns_http_client:
            self._http.close()

    @staticmethod
    def _raise_api_error(response: httpx.Response) -> None:
        try:
            payload: Any = response.json()
        except ValueError:
            payload = response.text
        message = _api_message(payload, response.status_code)
        kwargs = {
            "status_code": response.status_code,
            "response_data": payload,
            "headers": response.headers,
        }
        if response.status_code in (401, 403):
            raise AuthenticationError(message, **kwargs)
        if response.status_code == 404:
            raise NotFoundError(message, **kwargs)
        if response.status_code == 422:
            raise ValidationError(message, **kwargs)
        if response.status_code == 429:
            raise RateLimitError(message, retry_after=_retry_after(response), **kwargs)
        raise ApiError(message, **kwargs)


def _api_message(payload: Any, status_code: int) -> str:
    if isinstance(payload, Mapping):
        for key in ("message", "detail", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    return f"Xarkeo API returned HTTP {status_code}."


def _http2_available() -> bool:
    """检查 h2 包是否可用（http2 需要）。"""
    try:
        import h2  # noqa: F401

        return True
    except ImportError:
        return False


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    try:
        return max(0.0, float(value)) if value is not None else None
    except ValueError:
        return None
