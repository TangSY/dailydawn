from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any

import httpx


@dataclass
class Signal:
    source: str
    title: str
    url: str
    score: float = 0.0                  # 归一化分数 0-1
    raw_score: int = 0                  # 原始分数（stars / upvotes）
    comments: int = 0
    author: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class BaseFetcher(ABC):
    source_name: str = "unknown"
    timeout: float = 15.0

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        """拉取数据并返回统一格式的 Signal 列表。"""
        raise NotImplementedError

    async def safe_fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        try:
            return await self.fetch(client)
        except Exception as e:
            print(f"[{self.source_name}] fetch failed: {type(e).__name__}: {e}")
            return []
