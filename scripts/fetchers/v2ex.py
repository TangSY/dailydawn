from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import BaseFetcher, Signal


class V2EXFetcher(BaseFetcher):
    source_name = "v2ex"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        resp = await client.get(
            "https://www.v2ex.com/api/topics/hot.json",
            timeout=self.timeout,
            headers={"User-Agent": "dailydawn/0.1"},
        )
        resp.raise_for_status()
        topics = resp.json()

        signals: list[Signal] = []
        for t in topics[:20]:
            replies = t.get("replies", 0)
            # V2EX 返回 created (unix 秒)：帖子首次发布时间
            created_ts = t.get("created")
            published_at = (
                datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat()
                if created_ts
                else None
            )
            signals.append(
                Signal(
                    source="V2EX",
                    title=t.get("title", ""),
                    url=t.get("url", ""),
                    raw_score=replies,
                    score=min(replies / 200.0, 1.0),
                    comments=replies,
                    author=t.get("member", {}).get("username", ""),
                    tags=[t.get("node", {}).get("title", "")] if t.get("node") else [],
                    published_at=published_at,
                )
            )
        return signals
