from __future__ import annotations

import time

import httpx

from .base import BaseFetcher, Signal

# 取最近 48 小时内的 story（跨过 UTC 00:00 workflow 触发时，确保有足够 24h 候选）
# 否则 Algolia API 会按票数返回 HN 历史上所有高票帖（Apollo 关闭/GPT-4 发布等老新闻），
# LLM 会误把它们当成"今日信号"
_WINDOW_HOURS = 48


class HackerNewsFetcher(BaseFetcher):
    source_name = "hackernews"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        cutoff = int(time.time()) - _WINDOW_HOURS * 3600
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "tags": "story",
            "numericFilters": f"points>20,created_at_i>{cutoff}",
            "hitsPerPage": 60,
        }
        resp = await client.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        signals: list[Signal] = []
        for hit in data.get("hits", []):
            if not hit.get("url"):
                continue
            points = hit.get("points", 0)
            signals.append(
                Signal(
                    source="HackerNews",
                    title=hit.get("title", ""),
                    url=hit["url"],
                    raw_score=points,
                    score=min(points / 500.0, 1.0),
                    comments=hit.get("num_comments", 0),
                    author=hit.get("author", ""),
                    # Algolia HN API 直接返回 ISO 8601（如 "2026-04-18T03:21:00.000Z"）
                    published_at=hit.get("created_at"),
                    extra={"hn_id": hit.get("objectID")},
                )
            )
        return signals
