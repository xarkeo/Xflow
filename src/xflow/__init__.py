"""XFlow — XFin 官方对外客户端 SDK（Python）。

面向外部第三方用户，封装 XFin 数据 API，处理 PAT 认证、限流重试，提供 pandas-first 的类型安全数据访问。
"""

from .client import AsyncXflowClient, XflowClient
from .common.errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    NotFoundError,
    PaginationError,
    RateLimitError,
    TransportError,
    ValidationError,
)

__all__ = [
    "XflowClient",
    "AsyncXflowClient",
    "ApiError",
    "AuthenticationError",
    "ConfigurationError",
    "NotFoundError",
    "PaginationError",
    "RateLimitError",
    "TransportError",
    "ValidationError",
]

__version__ = "1.0.0"

