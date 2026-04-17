from __future__ import annotations

import asyncio
import json

import httpx

from .base import BaseFetcher, Signal

# 独立开发者关心的固定关键词集合（每天全量查 7d 涨幅）
# 取 hl=en-US + geo=worldwide，获得英文搜索趋势
SEED_KEYWORDS = [
    "ai agent",
    "claude code",
    "llm local",
    "vibe coding",
    "indie hackers",
    "saas boilerplate",
    "vector database",
    "agent memory",
    "prompt engineering",
    "open source llm",
    "llm fine tuning",
    "cloudflare workers",
    "vercel ai",
    "hugging face",
    "ollama",
    "langchain alternative",
]


class GoogleTrendsFetcher(BaseFetcher):
    """
    通过 Google Trends 的未公开 JSON 端点获取关键词 7 天涨幅。

    故意不用 pytrends —— 它频繁抛 429，且维护不稳定；
    直接调 trends.google.com 的公开 UI endpoint（无需 token），
    用共享的 httpx.AsyncClient 并发请求。

    限流策略：串行请求每个关键词（避免并发过多被 block），
    单词失败 skip，不挂整体流水线。
    """

    source_name = "google_trends"
    timeout = 10.0

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        signals: list[Signal] = []

        for kw in SEED_KEYWORDS:
            try:
                delta = await self._relative_growth_7d(client, kw)
            except Exception:
                continue
            if delta is None or delta < 20:
                # 只保留 7d 上涨 >= 20% 的关键词（弱信号过滤，原 50% 过严）
                continue
            signals.append(
                Signal(
                    source="Google Trends",
                    title=f'"{kw}" +{delta:.0f}%',
                    url=f"https://trends.google.com/trends/explore?q={kw.replace(' ', '+')}",
                    raw_score=int(delta),
                    score=min(delta / 500.0, 1.0),
                    summary=f"Search interest for '{kw}' rose {delta:.0f}% over the past 7 days.",
                    tags=["search_trend"],
                    extra={"keyword": kw, "growth_7d_pct": delta},
                )
            )
            # 小延迟避免 429
            await asyncio.sleep(0.5)

        return signals

    async def _relative_growth_7d(
        self, client: httpx.AsyncClient, keyword: str
    ) -> float | None:
        """
        返回关键词过去 7 天相对过去 14-7 天的增长百分比。
        数据点缺失或为 0 时返回 None。
        """
        url = "https://trends.google.com/trends/api/widgetdata/multiline"
        # 先请求 explore 拿 widget token
        explore_url = "https://trends.google.com/trends/api/explore"
        explore_params = {
            "hl": "en-US",
            "tz": "0",
            "req": (
                f'{{"comparisonItem":[{{"keyword":"{keyword}","geo":"","time":"now 7-d"}}],'
                f'"category":0,"property":""}}'
            ),
        }
        explore_resp = await client.get(
            explore_url,
            params=explore_params,
            timeout=self.timeout,
            headers={"User-Agent": "Mozilla/5.0 dailydawn/0.1"},
        )
        if explore_resp.status_code != 200:
            return None

        # Google 响应会以 ")]}'," 开头，需剥离
        text = explore_resp.text.lstrip(")]}',\n ")
        data = json.loads(text)
        widgets = data.get("widgets", [])
        timeseries_widget = next(
            (w for w in widgets if w.get("id") == "TIMESERIES"), None
        )
        if not timeseries_widget:
            return None

        token = timeseries_widget.get("token")
        req_body = timeseries_widget.get("request")
        if not token or not req_body:
            return None

        series_resp = await client.get(
            url,
            params={
                "hl": "en-US",
                "tz": "0",
                "req": json.dumps(req_body, separators=(",", ":")),
                "token": token,
            },
            timeout=self.timeout,
            headers={"User-Agent": "Mozilla/5.0 dailydawn/0.1"},
        )
        if series_resp.status_code != 200:
            return None

        text = series_resp.text.lstrip(")]}',\n ")
        payload = json.loads(text)
        points = (
            payload.get("default", {})
            .get("timelineData", [])
        )
        if len(points) < 2:
            return None

        values = [p.get("value", [0])[0] or 0 for p in points]
        half = len(values) // 2
        early_avg = sum(values[:half]) / max(half, 1)
        late_avg = sum(values[half:]) / max(len(values) - half, 1)
        if early_avg < 1:
            return None
        return (late_avg - early_avg) / early_avg * 100.0
