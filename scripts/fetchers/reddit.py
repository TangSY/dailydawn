from __future__ import annotations

import os

import httpx

from .base import BaseFetcher, Signal

SUBREDDITS = ["programming", "startups", "LocalLLaMA", "MachineLearning", "webdev"]


class RedditFetcher(BaseFetcher):
    source_name = "reddit"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        # 用公开 JSON 接口无需 OAuth（限流更严，但跑个日报够了）
        signals: list[Signal] = []
        for sub in SUBREDDITS:
            url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=10"
            try:
                resp = await client.get(
                    url,
                    timeout=self.timeout,
                    headers={"User-Agent": "dailydawn/0.1"},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception:
                continue

            for child in data.get("data", {}).get("children", []):
                d = child["data"]
                ups = d.get("ups", 0)
                if ups < 50:
                    continue
                signals.append(
                    Signal(
                        source=f"Reddit /r/{sub}",
                        title=d.get("title", ""),
                        url=d.get("url_overridden_by_dest") or f"https://reddit.com{d.get('permalink','')}",
                        raw_score=ups,
                        score=min(ups / 2000.0, 1.0),
                        comments=d.get("num_comments", 0),
                        author=d.get("author", ""),
                        tags=[sub],
                    )
                )
        return signals
