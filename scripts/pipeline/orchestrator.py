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
) -> str:
    """
    单语言的"专家 × 5 并行 + 主笔"流水线。
    classification 和 digests 语言无关（zh/en 共享）；questions 按语言生成。

    返回完整的 markdown 文本（由 editor 产出）。
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
      2. generate_questions（N 次并行，按语言；今日专属 20 个问题/语言）
      3. digest_all_sources（N 次并行，语言无关）
      4. 对每个 lang 并行跑 experts (×5) + editor (×1)

    返回 {lang: markdown}。
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
            )
            for lang in langs
        ]
    )
    return dict(zip(langs, results))
