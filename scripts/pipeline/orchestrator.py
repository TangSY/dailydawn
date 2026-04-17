from __future__ import annotations

import asyncio

from ..fetchers.base import Signal
from .classifier import classify
from .source_digest import digest_all_sources
from .experts import run_experts
from .editor import run_editor


async def generate_report(
    *,
    lang: str,
    date: str,
    signals: list[Signal],
    classification: dict,
    digests: list[dict],
) -> str:
    """
    单语言的"专家 × 4 并行 + 主笔"流水线。
    classification 和 digests 由上层预先调用（语言无关，zh/en 共享）。

    返回完整的 markdown 文本（由 editor 产出）。
    """
    # 抽出 Google Trends 信号（按源名过滤）
    trends = [s for s in signals if s.source == "Google Trends"]

    experts_output = await run_experts(
        lang=lang,
        signals=signals,
        classification=classification,
        digests=digests,
        trends=trends,
    )

    # editor 是同步调用，用 to_thread 避免阻塞 event loop
    markdown = await asyncio.to_thread(
        run_editor,
        lang=lang,
        date=date,
        signals=signals,
        classification=classification,
        experts_output=experts_output,
        trends=trends,
    )
    return markdown


async def run_pipeline(
    *,
    date: str,
    signals: list[Signal],
    langs: list[str] = ["zh", "en"],
) -> dict[str, str]:
    """
    完整流水线：
      1. classify（1 次，语言无关）
      2. digest_all_sources（N 次并行，语言无关）
      3. 对每个 lang 并行跑 experts (×4) + editor (×1)

    返回 {lang: markdown}。
    """
    print("→ [classifier] ...")
    classification = await asyncio.to_thread(classify, signals)
    buckets_counts = {k: len(v) for k, v in classification.get("buckets", {}).items()}
    print(f"✓ [classifier] buckets: {buckets_counts}")

    print("→ [source_digest] running in parallel ...")
    digests = await digest_all_sources(signals)
    print(f"✓ [source_digest] {len(digests)} sources digested")

    # 各语言独立生成（专家可以并行，但主笔串行，所以 run_report 本身就是组合）
    results = await asyncio.gather(
        *[
            generate_report(
                lang=lang,
                date=date,
                signals=signals,
                classification=classification,
                digests=digests,
            )
            for lang in langs
        ]
    )
    return dict(zip(langs, results))
