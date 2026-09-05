"""板块模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Block:
    """板块。"""

    code: str
    name: str
    type: str = ""


@dataclass
class BlockMember:
    """板块成员。"""

    symbol: str
    name: str
