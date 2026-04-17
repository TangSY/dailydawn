from __future__ import annotations

import json

from ..fetchers.base import Signal
from .llm import call_json, load_prompt

SYSTEM = "You are a precise signal classifier. Output strict JSON only."


def classify(signals: list[Signal]) -> dict:
    """
    输入聚合后的 Top-N signals（通常 60 条），输出分类结果。

    返回结构：
    {
      "buckets": {"tech": [...], "launch": [...], "competition": [...], "demand": [...]},
      "cross_source_themes": [{"theme", "signal_ids", "sources"}],
      "priority_ids": [...]
    }
    """
    prompt_template = load_prompt("classifier.md")
    signals_json = json.dumps(
        [
            {
                "id": i,
                "source": s.source,
                "title": s.title,
                "url": s.url,
                "score": round(s.score, 2),
                "raw_score": s.raw_score,
                "comments": s.comments,
                "author": s.author,
                "summary": s.summary,
                "tags": s.tags,
            }
            for i, s in enumerate(signals)
        ],
        ensure_ascii=False,
        indent=2,
    )
    user = prompt_template.replace("{{signals_json}}", signals_json)
    return call_json(SYSTEM, user, temperature=0.2)
