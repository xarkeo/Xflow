"""XFlow 配置层：环境变量 + 配置文件。优先级：代码 > 环境变量 > 配置文件。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """XFlow 配置。"""

    token: str | None = None
    base_url: str | None = None
    timeout: float | None = None
    cache_ttl: float = 0.0
    enable_throttle: bool = True
    retry_attempts: int = 3
    raw_data: bool = False
    disk_cache_dir: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置。"""
        return cls(
            token=os.environ.get("XARKEO_TOKEN"),
            base_url=os.environ.get("XARKEO_BASE_URL"),
            timeout=_float_env("XARKEO_TIMEOUT"),
            cache_ttl=_float_env("XARKEO_CACHE_TTL", 0.0),
            enable_throttle=os.environ.get("XARKEO_ENABLE_THROTTLE", "1") != "0",
            retry_attempts=_int_env("XARKEO_RETRY_ATTEMPTS", 3),
            raw_data=os.environ.get("XARKEO_RAW_DATA", "0") == "1",
            disk_cache_dir=os.environ.get("XARKEO_DISK_CACHE_DIR"),
        )


def _float_env(name: str, default: float | None = None) -> float | None:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
