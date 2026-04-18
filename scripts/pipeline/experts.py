from __future__ import annotations

import asyncio
import json

from ..fetchers.base import Signal
from .llm import call_text, load_prompt

SYSTEM_ZH = "你是一名资深技术派独立开发者观察员，擅长用硬数据和锋利判断做深度分析。"
SYSTEM_EN = "You are a senior indie-builder-facing tech analyst who delivers sharp, data-driven takes."

# 5 个专家角色定义（对应 classifier 输出的 5 个 bucket）
# 每个 bucket 下 4 个固定子问题，模仿  的"每章 4 小节"结构
ROLES_ZH: dict[str, dict[str, object]] = {
    "launch": {
        "name": "独立发布观察员",
        "focus": "YC / Product Hunt 首发、Show HN、GA 版本、独立开发者出货与营收里程碑",
        "section_title": "发现机会",
        "sub_questions": [
            "今天有哪些独立创始人产品上线了？",
            "今天最有意思的 Show HN 是什么？",
            "哪些独立创始人突破了值得关注的营收里程碑？",
            "今天独立开发者实际在用什么技术栈？",
        ],
    },
    "tech": {
        "name": "技术选型观察员",
        "focus": "AI 模型发布、框架、开发者工具、基础设施、性能与成本对比",
        "section_title": "技术选型",
        "sub_questions": [
            "今天实际发布了哪些 AI 模型和框架？",
            "哪些 GitHub 仓库真正在加速（而不只是坐在榜首）？",
            "什么新搜索词正在飙升？",
            "HuggingFace 上有哪些真正对产品有价值的趋势？",
        ],
    },
    "competition": {
        "name": "竞争情报员",
        "focus": "巨头战略动作、定价变动、品类洗牌、收购与开源策略",
        "section_title": "竞争情报",
        "sub_questions": [
            "今天谁在威胁谁？",
            "今天最大的价格差距在哪里？",
            "现在最大的开放机会在哪里？",
            "什么已经饱和或已被定价消化——应该避开？",
        ],
    },
    "demand": {
        "name": "需求雷达员",
        "focus": "用户痛点、搜索意图、未被货币化的需求、社区抱怨与对主流服务的不满",
        "section_title": "需求雷达",
        "sub_questions": [
            "独立社区里有哪些实时痛点信号？",
            "未被货币化的需求藏在哪里？",
            "成熟玩家在做什么值得借鉴？",
            "用户对主流服务的不满到底有多强烈？",
        ],
    },
    "trend": {
        "name": "趋势判断员",
        "focus": "跨源时间窗变化、搜索词涨幅与冷却、自托管与开源替代品上升、跨领域被忽视信号",
        "section_title": "趋势判断",
        "sub_questions": [
            "过去七天最强的搜索词上升模式是什么？",
            "哪些词在冷却，这告诉我们什么？",
            "哪些自托管 / 开源替代品正在上升——这揭示了什么？",
            "今天有哪些间接或跨领域信号正在被忽视？",
        ],
    },
}

ROLES_EN: dict[str, dict[str, object]] = {
    "launch": {
        "name": "Indie Launch Observer",
        "focus": "YC / Product Hunt debuts, Show HN, GA releases, solo-builder shipping, revenue milestones",
        "section_title": "Launch discoveries",
        "sub_questions": [
            "What indie-founder products launched today?",
            "What's the most interesting Show HN today?",
            "Which indie founders hit revenue milestones worth noting?",
            "What tech stack are indie builders actually using today?",
        ],
    },
    "tech": {
        "name": "Tech Stack Observer",
        "focus": "AI model releases, frameworks, dev tools, infra, perf/cost comparisons",
        "section_title": "Tech stack",
        "sub_questions": [
            "What AI models and frameworks actually shipped today?",
            "Which GitHub repos are really accelerating (not just sitting at the top)?",
            "What new search terms are surging?",
            "What HuggingFace trends actually matter for products?",
        ],
    },
    "competition": {
        "name": "Competitive Intel Analyst",
        "focus": "big-tech moves, pricing shifts, category consolidation, acquisitions, open-source plays",
        "section_title": "Competitive intel",
        "sub_questions": [
            "Who's threatening whom today?",
            "Where's the biggest pricing gap today?",
            "Where's the biggest open opportunity right now?",
            "What's already saturated or priced-in — should be avoided?",
        ],
    },
    "demand": {
        "name": "Demand Radar",
        "focus": "user pain points, search intent, unmonetized demand, community frustrations with mainstream services",
        "section_title": "Demand radar",
        "sub_questions": [
            "What real-time pain signals are hitting indie communities?",
            "Where is unmonetized demand hiding?",
            "What are mature players doing that's worth borrowing?",
            "How angry are users with mainstream services right now?",
        ],
    },
    "trend": {
        "name": "Trend Analyst",
        "focus": "cross-source momentum, search query growth and cooling, rising self-hosted/open-source alternatives, overlooked cross-domain signals",
        "section_title": "Trend verdict",
        "sub_questions": [
            "What are the strongest search-term rising patterns over the past 7 days?",
            "Which terms are cooling, and what does that tell us?",
            "Which self-hosted / open-source alternatives are rising — what does it reveal?",
            "What indirect or cross-domain signals are being overlooked today?",
        ],
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


def _format_sub_questions(sub_questions: list[str]) -> str:
    return "\n".join(f"{i + 1}. {q}" for i, q in enumerate(sub_questions))


def _build_user_prompt(
    *,
    lang: str,
    role: dict[str, object],
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

    sub_qs: list[str] = role["sub_questions"]  # type: ignore[assignment]

    return (
        template
        .replace("{{role_name}}", role["name"])  # type: ignore[arg-type]
        .replace("{{role_focus}}", role["focus"])  # type: ignore[arg-type]
        .replace("{{sub_questions}}", _format_sub_questions(sub_qs))
        .replace("{{bucket_signals}}", bucket_json)
        .replace("{{digests}}", digests_json)
        .replace("{{trends_data}}", trends_json)
    )


def _run_one_expert(
    lang: str,
    bucket_key: str,
    role: dict[str, object],
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

    # 运行时校验：检查产出是否包含 4 个 H3 小节（ 风格）
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
    digests: list[dict],
    trends: list[Signal],
) -> list[dict]:
    """
    并行运行 5 个专家 agent。每个专家只看自己 bucket 的信号 + 共享的 digests 和 trends。
    trends 全量传入（对所有 bucket 都有意义，但对 trend bucket 最关键）。
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
