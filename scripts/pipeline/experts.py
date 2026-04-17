from __future__ import annotations

import asyncio
import json

from ..fetchers.base import Signal
from .llm import call_text, load_prompt

SYSTEM_ZH = "你是一名资深技术派独立开发者观察员，擅长用硬数据和锋利判断做深度分析。"
SYSTEM_EN = "You are a senior indie-builder-facing tech analyst who delivers sharp, data-driven takes."

# 4 个专家角色定义（对应 classifier 输出的 4 个 bucket）
ROLES_ZH: dict[str, dict[str, str]] = {
    "tech": {
        "name": "技术选型观察员",
        "focus": "模型发布、框架、开发者工具、基础设施、性能与成本对比",
    },
    "launch": {
        "name": "独立发布观察员",
        "focus": "YC / Product Hunt 首发、GA 版本、独立开发者出货",
    },
    "competition": {
        "name": "竞争情报员",
        "focus": "巨头战略动作、定价变动、品类洗牌、收购与开源策略",
    },
    "demand": {
        "name": "需求雷达员",
        "focus": "用户痛点、搜索意图、未被货币化的需求、社区抱怨与质问",
    },
}

ROLES_EN: dict[str, dict[str, str]] = {
    "tech": {
        "name": "Tech Stack Observer",
        "focus": "model releases, frameworks, dev tools, infra, perf/cost comparisons",
    },
    "launch": {
        "name": "Indie Launch Observer",
        "focus": "YC / Product Hunt debuts, GA releases, solo-builder shipping",
    },
    "competition": {
        "name": "Competitive Intel Analyst",
        "focus": "big-tech moves, pricing shifts, category consolidation, acquisitions, open-source plays",
    },
    "demand": {
        "name": "Demand Radar",
        "focus": "user pain points, search intent, unmonetized demand, community frustrations",
    },
}


def _format_signal_for_prompt(s: Signal) -> dict:
    return {
        "source": s.source,
        "title": s.title,
        "url": s.url,
        "raw_score": s.raw_score,
        "comments": s.comments,
        "author": s.author,
        "summary": s.summary,
        "tags": s.tags,
        "extra": s.extra,
    }


def _build_user_prompt(
    *,
    lang: str,
    role: dict[str, str],
    bucket_signals: list[Signal],
    digests: list[dict],
    trends: list[Signal],
) -> str:
    template = load_prompt(f"expert.{lang}.md")

    bucket_json = json.dumps(
        [_format_signal_for_prompt(s) for s in bucket_signals],
        ensure_ascii=False,
        indent=2,
    )
    digests_json = json.dumps(digests, ensure_ascii=False, indent=2)
    trends_json = json.dumps(
        [_format_signal_for_prompt(t) for t in trends],
        ensure_ascii=False,
        indent=2,
    )

    return (
        template
        .replace("{{role_name}}", role["name"])
        .replace("{{role_focus}}", role["focus"])
        .replace("{{bucket_signals}}", bucket_json)
        .replace("{{digests}}", digests_json)
        .replace("{{trends_data}}", trends_json)
    )


def _run_one_expert(
    lang: str,
    bucket_key: str,
    role: dict[str, str],
    bucket_signals: list[Signal],
    digests: list[dict],
    trends: list[Signal],
) -> dict:
    """单个专家调用（同步，供 to_thread 包装）。失败时返回空段落占位。"""
    system = SYSTEM_ZH if lang == "zh" else SYSTEM_EN
    user = _build_user_prompt(
        lang=lang,
        role=role,
        bucket_signals=bucket_signals,
        digests=digests,
        trends=trends,
    )
    try:
        markdown = call_text(system, user, temperature=0.55)
    except Exception as err:
        print(f"[expert:{lang}:{bucket_key}] failed: {err}")
        markdown = ""
    return {"bucket": bucket_key, "role": role["name"], "markdown": markdown}


async def run_experts(
    *,
    lang: str,
    signals: list[Signal],
    classification: dict,
    digests: list[dict],
    trends: list[Signal],
) -> list[dict]:
    """
    并行运行 4 个专家 agent。每个专家只看自己 bucket 的信号 + 共享的 digests 和 trends。
    trends 始终全量传入（信号少，且横跨所有 bucket）。
    """
    roles = ROLES_ZH if lang == "zh" else ROLES_EN
    buckets = classification.get("buckets", {})

    tasks = []
    for bucket_key, role in roles.items():
        ids = buckets.get(bucket_key, [])
        bucket_signals = [signals[i] for i in ids if 0 <= i < len(signals)]
        tasks.append(
            asyncio.to_thread(
                _run_one_expert,
                lang,
                bucket_key,
                role,
                bucket_signals,
                digests,
                trends,
            )
        )
    return await asyncio.gather(*tasks)
