"""XFlow 认证层：token 管理、注入 X-API-Key，凭证不泄露。"""

from __future__ import annotations

from .errors import ConfigurationError


class Auth:
    """PAT 认证：管理 token，注入 X-API-Key 头。

    凭证来源优先级：代码传入 > 环境变量（XARKEO_TOKEN）> 配置文件。
    凭证绝不写入日志/错误信息（脱敏）。
    """

    def __init__(self, token: str | None = None) -> None:
        self._token = self._resolve_token(token)

    @staticmethod
    def _resolve_token(token: str | None) -> str:
        if token and token.strip():
            return token.strip()
        env_token = _environment_token()
        if env_token:
            return env_token
        raise ConfigurationError(
            "No Xarkeo token is configured. Set XARKEO_TOKEN or pass token to XflowClient(...)."
        )

    @property
    def token(self) -> str:
        return self._token

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        """注入 X-API-Key 头。"""
        headers["X-API-Key"] = self._token
        return headers

    def cache_scope(self) -> str:
        """返回 token 的脱敏哈希，用于缓存 key 隔离不同用户。"""
        import hashlib

        return hashlib.sha256(self._token.encode("utf-8")).hexdigest()[:16]


def _environment_token() -> str | None:
    import os

    return os.environ.get("XARKEO_TOKEN") or None
