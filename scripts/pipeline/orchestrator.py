from __future__ import annotations

import asyncio

from ..fetchers.base import Signal
from .classifier import classify
from .source_digest import digest_all_sources
from .question_generator import generate_questions
from .experts import run_experts
from .editor import run_editor


async def generate_report(
    *,
    lang: str,
    date: str,
    signals: list[Signal],
    classification: dict,
    questions: dict[str, list[str]],
    digests: list[dict],
    recent_taglines: list[dict],
) -> dict[str, str | list[str] | None]:
    """
    单语言的"专家 × 5 并行 + 主笔"流水线。
    classification 和 digests 语言无关（zh/en 共享）；questions 按语言生成。
    recent_taglines：最近 7 天已发布的 tagline + top3_themes，editor 用它做跨日主题去重。

    返回 {"markdown": str, "tagline": str | None, "top3_themes": list[str]}。
    """
    # 抽出 Google Trends 信号（按源名过滤）
    trends = [s for s in signals if s.source == "Google Trends"]

    experts_output = await run_experts(
        lang=lang,
        signals=signals,
        classification=classification,
        questions=questions,
        digests=digests,
        trends=trends,
    )

    # editor 是同步调用，用 to_thread 避免阻塞 event loop
    result = await asyncio.to_thread(
        run_editor,
        lang=lang,
        date=date,
        signals=signals,
        classification=classification,
        experts_output=experts_output,
        trends=trends,
        recent_taglines=recent_taglines,
    )
    return result


async def run_pipeline(
    *,
    date: str,
    signals: list[Signal],
    langs: list[str] = ["zh", "en"],
    recent_taglines: list[dict] | None = None,
) -> dict[str, dict[str, str | list[str] | None]]:
    """
    完整流水线：
      1. classify（1 次，语言无关）
      2. generate_questions（N 次并行，按语言；今日专属 20 个问题/语言）
      3. digest_all_sources（N 次并行，语言无关）
      4. 对每个 lang 并行跑 experts (×5) + editor (×1)

    recent_taglines：跨日主题去重锚（最近 7 天的 tagline + top3_themes），传给 editor。

    返回 {lang: {"markdown": str, "tagline": str | None, "top3_themes": list[str]}}。
    """
    print("→ [classifier] ...")
    classification = await asyncio.to_thread(classify, signals)
    buckets_counts = {k: len(v) for k, v in classification.get("buckets", {}).items()}
    print(f"✓ [classifier] buckets: {buckets_counts}")

    # 问题生成和 source_digest 语言/源无关，可并行
    print("→ [question_generator + source_digest] running in parallel ...")
    questions_tasks = [
        asyncio.to_thread(
            generate_questions,
            lang=lang,
            signals=signals,
            classification=classification,
        )
        for lang in langs
    ]
    digests_task = digest_all_sources(signals)

    *questions_results, digests = await asyncio.gather(
        *questions_tasks, digests_task
    )
    questions_by_lang: dict[str, dict[str, list[str]]] = dict(
        zip(langs, questions_results)
    )

    for lang in langs:
        qs = questions_by_lang[lang]
        sample = qs.get("launch", [])
        print(f"✓ [questions:{lang}] e.g. launch[0]='{sample[0] if sample else '—'}'")
    print(f"✓ [source_digest] {len(digests)} sources digested")

    # 各语言独立生成（专家可以并行，editor 串行）
    results = await asyncio.gather(
        *[
            generate_report(
                lang=lang,
                date=date,
                signals=signals,
                classification=classification,
                questions=questions_by_lang[lang],
                digests=digests,
                recent_taglines=recent_taglines or [],
            )
            for lang in langs
        ]
    )
    return dict(zip(langs, results))
