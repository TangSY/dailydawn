from __future__ import annotations

import random

import httpx

from .base import BaseFetcher, Signal

# 覆盖独立开发者关心的多个方向：技术 / 创业 / AI / 云原生 / 前端 / 开源
SUBREDDITS = [
    "programming",
    "startups",
    "LocalLLaMA",
    "MachineLearning",
    "webdev",
    "SaaS",
    "opensource",
    "devops",
    "rust",
    "selfhosted",
]

# 随机 UA 缓解匿名限流（非根治，Reddit 新政策下 CF runner 出口 IP 仍可能偶发 403）
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

MIN_UPS = 20  # 原 50 过于激进，降到 20 扩大覆盖（LLM 聚合阶段再筛 Top 60）


class RedditFetcher(BaseFetcher):
    source_name = "reddit"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        signals: list[Signal] = []
        for sub in SUBREDDITS:
            url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=15"
            try:
                resp = await client.get(
                    url,
                    timeout=self.timeout,
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception:
                continue

            for child in data.get("data", {}).get("children", []):
                d = child["data"]
                ups = d.get("ups", 0)
                if ups < MIN_UPS:
                    continue
                signals.append(
                    Signal(
                        source=f"Reddit /r/{sub}",
                        title=d.get("title", ""),
                        url=d.get("url_overridden_by_dest")
                        or f"https://reddit.com{d.get('permalink','')}",
                        raw_score=ups,
                        score=min(ups / 2000.0, 1.0),
                        comments=d.get("num_comments", 0),
                        author=d.get("author", ""),
                        tags=[sub],
                    )
                )
        return signals
