"""XFlow 日志层：请求追踪、脱敏调试。"""

from __future__ import annotations

import logging

logger = logging.getLogger("xflow")


def setup(level: int = logging.INFO) -> None:
    """配置 xflow 日志。"""
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)


def debug_request(method: str, path: str, params: dict | None = None) -> None:
    """记录请求（脱敏，不含 token）。"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("REQ %s %s params=%s", method, path, params)


def debug_response(status_code: int, path: str, duration_ms: float) -> None:
    """记录响应。"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("RES %d %s %.1fms", status_code, path, duration_ms)
