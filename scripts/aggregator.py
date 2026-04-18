from __future__ import annotations

from urllib.parse import urlparse

from .fetchers.base import Signal


def _canonical_url(url: str) -> str:
    """去掉 utm/tracking 参数用于去重。"""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    except Exception:
        return url


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

    return top60 + trends_supplement
