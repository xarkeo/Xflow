"""XFlow 分页层：页码/游标/惰性迭代（FULL/ITERATOR）。"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

import pandas as pd

from .errors import PaginationError

T = TypeVar("T")


class PaginationType(str, Enum):
    """分页模式。"""

    NONE = "none"      # 单页，不翻页
    FULL = "full"      # 自动翻页，返回全部
    ITERATOR = "iterator"  # 惰性迭代器，逐页拉取


@dataclass(frozen=True)
class PageState:
    """分页元数据。"""

    page: int | None
    page_size: int | None
    total: int | None
    has_next: bool | None


def page_state_from_payload(payload: dict[str, Any]) -> PageState:
    """从 API 响应提取分页元数据。"""
    page = _positive_int_meta(payload.get("page"))
    page_size = _positive_int_meta(payload.get("page_size"))
    total = _nonnegative_int_meta(payload.get("total"))
    if page is None or page_size is None or total is None:
        has_next = None
    else:
        has_next = page * page_size < total
    return PageState(page, page_size, total, has_next)


def page_state_from_attrs(attrs: dict[Any, Any]) -> PageState:
    """从 DataFrame attrs 提取分页元数据。"""
    return PageState(
        _positive_int_meta(attrs.get("page")),
        _positive_int_meta(attrs.get("page_size")),
        _nonnegative_int_meta(attrs.get("total")),
        attrs.get("has_next") if isinstance(attrs.get("has_next"), bool) else None,
    )


def with_page_attrs(frame: pd.DataFrame, payload: dict[str, Any]) -> pd.DataFrame:
    """把分页元数据写入 DataFrame attrs。"""
    state = page_state_from_payload(payload)
    frame.attrs = {
        "page": state.page,
        "page_size": state.page_size,
        "total": state.total,
        "has_next": state.has_next,
    }
    return frame


def iterate_pages(
    fetch: Callable[[int], pd.DataFrame],
    *,
    page_size: int,
    max_pages: int,
) -> Iterator[pd.DataFrame]:
    """惰性逐页迭代。"""
    for expected_page in range(1, max_pages + 1):
        frame = fetch(expected_page)
        state = page_state_from_attrs(frame.attrs)
        if state.page is not None and state.page != expected_page:
            raise PaginationError(
                f"Expected API page {expected_page}, but response declared page {state.page}."
            )
        yield frame
        if frame.empty or state.has_next is False:
            return
        if state.total is not None and expected_page * page_size >= state.total:
            return
        if state.total is None and len(frame) < page_size:
            return


def collect_pages(
    pages: Iterator[pd.DataFrame],
    *,
    columns: tuple[str, ...],
    max_pages: int,
) -> pd.DataFrame:
    """收集所有页为一个 DataFrame。"""
    frames = list(pages)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
    last = page_state_from_attrs(frames[-1].attrs) if frames else PageState(None, None, None, None)
    stopped_reason = "max_pages"
    if frames and frames[-1].empty:
        stopped_reason = "empty_page"
    elif last.has_next is False:
        stopped_reason = "total_reached" if last.total is not None else "short_page"
    elif last.total is not None and len(combined) >= last.total:
        stopped_reason = "total_reached"
    elif frames and last.total is None and len(frames[-1]) < (last.page_size or 0):
        stopped_reason = "short_page"
    combined.attrs = {
        "pages_fetched": len(frames),
        "rows_fetched": len(combined),
        "total": last.total,
        "complete": stopped_reason != "max_pages",
        "stopped_reason": stopped_reason,
    }
    return combined


def _positive_int_meta(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _nonnegative_int_meta(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
