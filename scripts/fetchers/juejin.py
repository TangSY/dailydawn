from __future__ import annotations

import httpx

from .base import BaseFetcher, Signal


class JuejinFetcher(BaseFetcher):
    source_name = "juejin"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        # 掘金热榜 API（官方小程序接口）
        url = "https://api.juejin.cn/content_api/v1/content/article_rank"
        params = {"category_id": "1", "type": "hot"}
        resp = await client.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        signals: list[Signal] = []
        for item in data.get("data", [])[:20]:
            info = item.get("content", {})
            counter = item.get("content_counter", {})
            hot = counter.get("hot_rank", 0)
            article_id = info.get("content_id", "")
            signals.append(
                Signal(
                    source="掘金",
                    title=info.get("title", ""),
                    url=f"https://juejin.cn/post/{article_id}",
                    raw_score=hot,
                    score=min(hot / 1000.0, 1.0),
                    comments=counter.get("comment_count", 0),
                    author=item.get("author", {}).get("name", ""),
                )
            )
        return signals
