from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.parse import urlparse

from .fetchers.base import Signal

# 窗口类来源：Signal.source（显示名）命中则 age_bucket = today_window。
# GitHub Trending 的"今日"是 star 增量窗口，Google Trends 是 7 日聚合窗口，
# 两者都不是单条 "published_at 等于今日" 语义但按产品定义视为今日信号。
_TODAY_WINDOW_SOURCES = {"GitHub Trending", "Google Trends"}


def _canonical_url(url: str) -> str:
    """去掉 utm/tracking 参数用于去重。"""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    except Exception:
        return url


def _compute_age_bucket(signal: Signal, today_utc: date) -> str:
    """按 published_at 归档到 today / past_72h / older；窗口类源直接 today_window。"""
    if signal.source in _TODAY_WINDOW_SOURCES:
        return "today_window"
    if not signal.published_at:
        return "unknown"
    try:
        raw = signal.published_at.replace("Z", "+00:00")
        pub_date = datetime.fromisoformat(raw).astimezone(timezone.utc).date()
    except Exception:
        return "unknown"
    days_ago = (today_utc - pub_date).days
    if days_ago <= 0:
        return "today"
    if days_ago <= 3:
        return "past_72h"
    return "older"


def aggregate(signals: list[Signal]) -> list[Signal]:
    """
    按 URL 去重，同 URL 跨源的分数叠加。

    返回 Top 60 高分信号 + **所有 Google Trends 信号**（不被截断）。
    Google Trends 的 score 计算方式是 growth_pct/500，值普遍 <0.3，如果直接
    按分数排名会被 HN 高票帖（score 接近 1.0）挤出 Top 60，导致 trend expert
    拿不到买家意图数据。保留机制确保 pytrends_growth 采到的关键词涨幅
    100% 进入下游 pipeline。
    """
    bucket: dict[str, Signal] = {}
    for s in signals:
        key = _canonical_url(s.url)
        if not key or key in {"https://", "http://"}:
            continue

        if key in bucket:
            existing = bucket[key]
            # 跨源出现 = 信号更强
            existing.score = min(existing.score + s.score * 0.5, 1.5)
            existing.extra.setdefault("also_on", []).append(s.source)
        else:
            bucket[key] = s

    ranked = sorted(bucket.values(), key=lambda x: x.score, reverse=True)
    top60 = ranked[:60]
    top60_urls = {_canonical_url(s.url) for s in top60}

    # 补回未进入 Top 60 的 Google Trends 信号（趋势 expert 的关键输入）
    trends_supplement = [
        s for s in ranked[60:]
        if s.source == "Google Trends" and _canonical_url(s.url) not in top60_urls
    ]

    final = top60 + trends_supplement

    # 打 age_bucket 标签。下游 expert / editor prompt 依据它做「今日主骨 + 历史佐证」硬约束。
    today_utc = datetime.now(timezone.utc).date()
    for s in final:
        s.age_bucket = _compute_age_bucket(s, today_utc)

    return final
