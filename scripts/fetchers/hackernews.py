from __future__ import annotations

import httpx

from .base import BaseFetcher, Signal


class HackerNewsFetcher(BaseFetcher):
    source_name = "hackernews"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        # Algolia API: 最近 24 小时内 top stories
        # points>20 取代原 >50（当天热度低时条目太少），hitsPerPage 60 扩大候选池
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "tags": "story",
            "numericFilters": "points>20",
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
                    extra={"hn_id": hit.get("objectID")},
                )
            )
        return signals
