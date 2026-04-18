from __future__ import annotations

import json

from ..fetchers.base import Signal
from .llm import call_json, load_prompt

SYSTEM_ZH = "你是 DailyDawn 的问题策展人，擅长基于今日信号生成锋利的、针对性的疑问句。严格 JSON 输出。"
SYSTEM_EN = "You are DailyDawn's question curator, generating sharp today-specific interrogative questions from signals. Strict JSON only."

_REQUIRED_BUCKETS = ("launch", "tech", "competition", "demand", "trend")


def _format_signal_brief(s: Signal) -> dict:
    return {
        "source": s.source,
        "title": s.title,
        "url": s.url,
        "raw_score": s.raw_score,
        "comments": s.comments,
        "author": s.author,
    }


def generate_questions(
    *,
    lang: str,
    signals: list[Signal],
    classification: dict,
) -> dict[str, list[str]]:
    """
    基于今日信号为 5 个 bucket 各生成 4 个今日专属问题。

    返回：
        {
          "launch": [q1, q2, q3, q4],
          "tech": [...],
          "competition": [...],
          "demand": [...],
          "trend": [...]
        }

    失败时返回 fallback 通用问题（保留日报结构不崩），不抛异常。
    """
    template = load_prompt(f"question_generator.{lang}.md")

    priority_ids = classification.get("priority_ids", [])
    priority = [signals[i] for i in priority_ids if 0 <= i < len(signals)]

    trends = [s for s in signals if s.source == "Google Trends"]

    user = (
        template
        .replace(
            "{{priority_signals}}",
            json.dumps(
                [_format_signal_brief(s) for s in priority[:20]],
                ensure_ascii=False,
                indent=2,
            ),
        )
        .replace(
            "{{cross_themes}}",
            json.dumps(
                classification.get("cross_source_themes", []),
                ensure_ascii=False,
                indent=2,
            ),
        )
        .replace(
            "{{trends_data}}",
            json.dumps(
                [_format_signal_brief(t) for t in trends[:20]],
                ensure_ascii=False,
                indent=2,
            ),
        )
    )

    system = SYSTEM_ZH if lang == "zh" else SYSTEM_EN

    try:
        result = call_json(system, user, temperature=0.6)
    except Exception as err:
        print(f"[question_generator:{lang}] failed, using fallback: {err}")
        return _fallback_questions(lang)

    # Schema 校验：5 个 bucket 各恰好 4 个问题
    normalized: dict[str, list[str]] = {}
    for bucket in _REQUIRED_BUCKETS:
        questions = result.get(bucket)
        if not isinstance(questions, list) or len(questions) != 4:
            print(
                f"[question_generator:{lang}] malformed bucket '{bucket}' "
                f"(got {type(questions).__name__} len={len(questions) if isinstance(questions, list) else 'N/A'}), "
                f"using fallback for this bucket"
            )
            normalized[bucket] = _fallback_questions(lang)[bucket]
        else:
            normalized[bucket] = [str(q).strip() for q in questions]

    return normalized


def _fallback_questions(lang: str) -> dict[str, list[str]]:
    """当 LLM 失败或 schema 错时的兜底问题（保留结构，用通用模板）。"""
    if lang == "zh":
        return {
            "launch": [
                "今天有哪些独立创始人产品上线了？",
                "今天最有意思的 Show HN 是什么？",
                "哪些独立创始人突破了值得关注的营收里程碑？",
                "今天独立开发者实际在用什么技术栈？",
            ],
            "tech": [
                "今天实际发布了哪些 AI 模型和框架？",
                "哪些 GitHub 仓库真正在加速？",
                "什么新搜索词正在飙升？",
                "HuggingFace 上有哪些真正对产品有价值的趋势？",
            ],
            "competition": [
                "今天谁在威胁谁？",
                "今天最大的价格差距在哪里？",
                "现在最大的开放机会在哪里？",
                "什么已经饱和或已被定价消化——应该避开？",
            ],
            "demand": [
                "独立社区里有哪些实时痛点信号？",
                "未被货币化的需求藏在哪里？",
                "成熟玩家在做什么值得借鉴？",
                "用户对主流服务的不满到底有多强烈？",
            ],
            "trend": [
                "过去七天最强的搜索词上升模式是什么？",
                "哪些词在冷却，这告诉我们什么？",
                "哪些自托管 / 开源替代品正在上升？",
                "今天有哪些间接或跨领域信号正在被忽视？",
            ],
        }
    return {
        "launch": [
            "What indie-founder products launched today?",
            "What's the most interesting Show HN today?",
            "Which indie founders hit revenue milestones worth noting?",
            "What tech stack are indie builders actually using today?",
        ],
        "tech": [
            "What AI models and frameworks actually shipped today?",
            "Which GitHub repos are really accelerating?",
            "What new search terms are surging?",
            "What HuggingFace trends actually matter for products?",
        ],
        "competition": [
            "Who's threatening whom today?",
            "Where's the biggest pricing gap today?",
            "Where's the biggest open opportunity right now?",
            "What's already saturated — should be avoided?",
        ],
        "demand": [
            "What real-time pain signals are hitting indie communities?",
            "Where is unmonetized demand hiding?",
            "What are mature players doing that's worth borrowing?",
            "How angry are users with mainstream services?",
        ],
        "trend": [
            "What are the strongest 7-day search rising patterns?",
            "Which terms are cooling, and what does it tell us?",
            "Which self-hosted / open-source alternatives are rising?",
            "What indirect cross-domain signals are being overlooked?",
        ],
    }
