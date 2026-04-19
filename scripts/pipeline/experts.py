from __future__ import annotations

import asyncio
import json

from ..fetchers.base import Signal
from .llm import call_text, load_prompt

SYSTEM_ZH = "你是一名资深技术派独立开发者观察员，擅长用硬数据和锋利判断做深度分析。"
SYSTEM_EN = "You are a senior indie-builder-facing tech analyst who delivers sharp, data-driven takes."

# 5 个专家角色定义（对应 classifier 输出的 5 个 bucket）
# sub_questions 不再硬编码在这里——运行时由 question_generator agent 基于今日信号动态生成
ROLES_ZH: dict[str, dict[str, str]] = {
    "launch": {
        "name": "独立发布观察员",
        "focus": "YC / Product Hunt 首发、Show HN、GA 版本、独立开发者出货与营收里程碑",
        "section_title": "发现机会",
    },
    "tech": {
        "name": "技术选型观察员",
        "focus": "AI 模型发布、框架、开发者工具、基础设施、性能与成本对比",
        "section_title": "技术选型",
    },
    "competition": {
        "name": "竞争情报员",
        "focus": "巨头战略动作、定价变动、品类洗牌、收购与开源策略",
        "section_title": "竞争情报",
    },
    "demand": {
        "name": "需求雷达员",
        "focus": "用户痛点、搜索意图、未被货币化的需求、社区抱怨与对主流服务的不满",
        "section_title": "需求雷达",
    },
    "trend": {
        "name": "趋势判断员",
        "focus": "跨源时间窗变化、搜索词涨幅与冷却、自托管与开源替代品上升、跨领域被忽视信号",
        "section_title": "趋势判断",
    },
}

ROLES_EN: dict[str, dict[str, str]] = {
    "launch": {
        "name": "Indie Launch Observer",
        "focus": "YC / Product Hunt debuts, Show HN, GA releases, solo-builder shipping, revenue milestones",
        "section_title": "Launch discoveries",
    },
    "tech": {
        "name": "Tech Stack Observer",
        "focus": "AI model releases, frameworks, dev tools, infra, perf/cost comparisons",
        "section_title": "Tech stack",
    },
    "competition": {
        "name": "Competitive Intel Analyst",
        "focus": "big-tech moves, pricing shifts, category consolidation, acquisitions, open-source plays",
        "section_title": "Competitive intel",
    },
    "demand": {
        "name": "Demand Radar",
        "focus": "user pain points, search intent, unmonetized demand, community frustrations with mainstream services",
        "section_title": "Demand radar",
    },
    "trend": {
        "name": "Trend Analyst",
        "focus": "cross-source momentum, search query growth and cooling, rising self-hosted/open-source alternatives, overlooked cross-domain signals",
        "section_title": "Trend verdict",
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
        # 真实发布时间：正文里"N 天前 / 过去 N 天"描述必须基于此字段事实
        "published_at": s.published_at,
        "extra": s.extra,
    }


def _format_sub_questions(sub_questions: list[str]) -> str:
    return "\n".join(f"{i + 1}. {q}" for i, q in enumerate(sub_questions))


def _build_user_prompt(
    *,
    lang: str,
    role: dict[str, str],
    sub_questions: list[str],
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
        .replace("{{sub_questions}}", _format_sub_questions(sub_questions))
        .replace("{{bucket_signals}}", bucket_json)
        .replace("{{digests}}", digests_json)
        .replace("{{trends_data}}", trends_json)
    )


def _run_one_expert(
    lang: str,
    bucket_key: str,
    role: dict[str, str],
    sub_questions: list[str],
    bucket_signals: list[Signal],
    digests: list[dict],
    trends: list[Signal],
) -> dict:
    """单个专家调用（同步，供 to_thread 包装）。失败时返回空段落占位。"""
    system = SYSTEM_ZH if lang == "zh" else SYSTEM_EN
    user = _build_user_prompt(
        lang=lang,
        role=role,
        sub_questions=sub_questions,
        bucket_signals=bucket_signals,
        digests=digests,
        trends=trends,
    )
    try:
        markdown = call_text(system, user, temperature=0.55)
    except Exception as err:
        print(f"[expert:{lang}:{bucket_key}] failed: {err}")
        markdown = ""

    # 运行时校验：检查产出是否包含 4 个 H3 小节
    h3_count = markdown.count("### ")
    if markdown and h3_count < 4:
        print(
            f"[expert:{lang}:{bucket_key}] warning: only {h3_count} H3 sections (expected 4); "
            f"output may be incomplete"
        )

    return {
        "bucket": bucket_key,
        "role": role["name"],
        "section_title": role["section_title"],
        "markdown": markdown,
    }


async def run_experts(
    *,
    lang: str,
    signals: list[Signal],
    classification: dict,
    questions: dict[str, list[str]],
    digests: list[dict],
    trends: list[Signal],
) -> list[dict]:
    """
    并行运行 5 个专家 agent。每个专家只看自己 bucket 的信号 + 共享的 digests/trends，
    加上 question_generator 给的今日专属 4 个子问题。
    """
    roles = ROLES_ZH if lang == "zh" else ROLES_EN
    buckets = classification.get("buckets", {})

    tasks = []
    for bucket_key, role in roles.items():
        ids = buckets.get(bucket_key, [])
        bucket_signals = [signals[i] for i in ids if 0 <= i < len(signals)]
        sub_questions = questions.get(bucket_key, [])
        tasks.append(
            asyncio.to_thread(
                _run_one_expert,
                lang,
                bucket_key,
                role,
                sub_questions,
                bucket_signals,
                digests,
                trends,
            )
        )
    return await asyncio.gather(*tasks)
