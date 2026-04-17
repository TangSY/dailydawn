from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from ..fetchers.base import Signal
from .llm import call_json, load_prompt

SYSTEM = "You are a precise source-level signal summarizer. Output strict JSON only."


_MAX_ITEMS_PER_SOURCE = 20  # 单次 input 控制在合理大小，避免 OneAPI 网关对长 input 的 500


def _digest_one_source(source_name: str, items: list[Signal]) -> dict:
    """对单一源的所有 item 做聚类摘要。超过 Top 20 只取 raw_score 最高的。"""
    prompt_template = load_prompt("source_digest.md")
    # 按 raw_score 倒序取 Top N
    top_items = sorted(items, key=lambda s: s.raw_score, reverse=True)[:_MAX_ITEMS_PER_SOURCE]
    items_json = json.dumps(
        [
            {
                "title": s.title,
                "url": s.url,
                "raw_score": s.raw_score,
                "comments": s.comments,
                "author": s.author,
                "summary": s.summary,
                "tags": s.tags,
                "extra": s.extra,
            }
            for s in top_items
        ],
        ensure_ascii=False,
        indent=2,
    )
    user = (
        prompt_template
        .replace("{{source_name}}", source_name)
        .replace("{{items_json}}", items_json)
    )
    try:
        return call_json(SYSTEM, user, temperature=0.3)
    except Exception as err:
        print(f"[source_digest] {source_name} failed: {err}")
        return {"source": source_name, "clusters": []}


async def digest_all_sources(signals: list[Signal]) -> list[dict]:
    """
    并行对每个 source 生成 digest。
    使用 asyncio.to_thread 让同步 LLM client 在线程池中运行。
    """
    # 按 source 分组（Reddit /r/programming 和 /r/startups 视为同一组 "Reddit"）
    groups: dict[str, list[Signal]] = defaultdict(list)
    for s in signals:
        # 统一归并子源（如 Reddit /r/xxx → Reddit）
        main = s.source.split(" /")[0].split(" ")[0]
        groups[main].append(s)

    tasks = [
        asyncio.to_thread(_digest_one_source, source_name, items)
        for source_name, items in groups.items()
        if items
    ]
    return await asyncio.gather(*tasks)
