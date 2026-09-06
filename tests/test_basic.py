"""XFlow 基础测试。"""

import pytest

import xflow
from xflow import (
    ApiError,
    AsyncXflowClient,
    AuthenticationError,
    ConfigurationError,
    NotFoundError,
    PaginationError,
    RateLimitError,
    TransportError,
    ValidationError,
    XflowClient,
)


def test_version():
    """版本号存在且格式正确。"""
    assert xflow.__version__ == "1.0.0"


def test_public_api_exports():
    """公共 API 导出完整。"""
    assert XflowClient is not None
    assert AsyncXflowClient is not None
    for exc in (
        ApiError,
        AuthenticationError,
        ConfigurationError,
        NotFoundError,
        PaginationError,
        RateLimitError,
        TransportError,
        ValidationError,
    ):
        assert issubclass(exc, Exception)


def test_client_requires_token():
    """未配置 token 时抛出 ConfigurationError。"""
    with pytest.raises(ConfigurationError):
        XflowClient()


def test_client_accepts_token():
    """传入 token 可正常创建客户端。"""
    client = XflowClient("xar_test_token")
    assert client is not None
    client.close()


def test_client_context_manager():
    """支持上下文管理器。"""
    with XflowClient("xar_test_token") as client:
        assert client is not None
