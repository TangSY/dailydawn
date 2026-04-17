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
    """按 URL 去重，同 URL 跨源的分数叠加。"""
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
    return ranked[:60]                  # 取 Top 60 给 LLM
