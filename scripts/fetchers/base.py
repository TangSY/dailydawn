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
    # ISO 8601 UTC 字符串（如 "2026-04-18T03:21:00Z"）。
    # LLM 生成时间描述（"N 天前 / 过去 N 天"）必须基于此字段，避免"今天发布"幻觉。
    # 部分源无"单条发布时间"概念时留 None：
    #   - GitHub Trending：Trending 的"今日"指 star 增量窗口，repo 本身可能历史已久
    #   - Google Trends：关键词涨幅是 7 日聚合数据，非单条事件
    published_at: str | None = None
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
