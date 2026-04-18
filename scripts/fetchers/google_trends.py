from __future__ import annotations

import feedparser
import httpx

from .base import BaseFetcher, Signal

# 每日热搜 RSS（公开稳定接口，比 widget explore API 可靠）
# 多地区覆盖，geo=US 主力，GB/IN 辅助扩充英语圈视角
RSS_GEOS = ["US", "GB", "IN"]

# 过滤弱热搜：approx_traffic 低于此值的不入库
_MIN_TRAFFIC = 10_000


def _parse_traffic(approx: str) -> int:
    """把 Google 的 '500K+' / '1M+' / '2,000+' 转成整数。"""
    if not approx:
        return 0
    s = approx.upper().strip().rstrip("+").replace(",", "").strip()
    try:
        if s.endswith("K"):
            return int(float(s[:-1]) * 1_000)
        if s.endswith("M"):
            return int(float(s[:-1]) * 1_000_000)
        return int(float(s))
    except (ValueError, TypeError):
        return 0


class GoogleTrendsFetcher(BaseFetcher):
    """
    抓取 Google Trends 每日热搜 RSS。

    弃用了之前的 widget explore API（不稳定，经常返回空 token）。
    现在用公开的 `/trends/trendingsearches/daily/rss?geo=XX` RSS 接口，
    结构稳定、无需鉴权。

    每条热搜 → 一个 Signal，包含 approx_traffic（转为整数分数）+ 相关新闻标题上下文。
    """

    source_name = "google_trends"
    timeout = 15.0

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        signals: list[Signal] = []

        for geo in RSS_GEOS:
            url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}"
            try:
                resp = await client.get(
                    url,
                    timeout=self.timeout,
                    headers={"User-Agent": "Mozilla/5.0 dailydawn/0.1"},
                )
                if resp.status_code != 200:
                    print(f"[google_trends:{geo}] HTTP {resp.status_code}")
                    continue
            except Exception as err:
                print(f"[google_trends:{geo}] request failed: {type(err).__name__}: {err}")
                continue

            feed = feedparser.parse(resp.text)
            if not feed.entries:
                print(f"[google_trends:{geo}] empty feed (body head: {resp.text[:200]!r})")
                continue
            for entry in feed.entries[:25]:
                title = (entry.get("title") or "").strip()
                if not title:
                    continue

                traffic_str = (
                    entry.get("ht_approx_traffic")
                    or entry.get("approx_traffic")
                    or ""
                )
                traffic = _parse_traffic(traffic_str)
                if traffic < _MIN_TRAFFIC:
                    continue

                # 相关新闻标题（命名空间 ht: news_item）
                news_titles: list[str] = []
                # feedparser 会把 <ht:news_item> 展开到 entry 里
                news_items = entry.get("ht_news_items") or entry.get("news_items") or []
                if isinstance(news_items, list):
                    for ni in news_items[:3]:
                        if isinstance(ni, dict):
                            t = ni.get("ht_news_item_title") or ni.get("title") or ""
                            if t:
                                news_titles.append(t)

                query_url = f"https://trends.google.com/trends/explore?q={title.replace(' ', '+')}&geo={geo}"
                summary_parts = [
                    f"[{geo}] 今日热搜，预估搜索量 {traffic_str}"
                ]
                if news_titles:
                    summary_parts.append("相关新闻：" + "; ".join(news_titles))

                signals.append(
                    Signal(
                        source="Google Trends",
                        title=title,
                        url=query_url,
                        raw_score=traffic,
                        score=min(traffic / 1_000_000.0, 1.0),
                        summary=" · ".join(summary_parts),
                        tags=["daily_search", geo.lower()],
                        extra={
                            "geo": geo,
                            "approx_traffic": traffic_str,
                            "news_titles": news_titles,
                        },
                    )
                )

        return signals
