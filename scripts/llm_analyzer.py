from __future__ import annotations

import json
import os
import re
from pathlib import Path

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .fetchers.base import Signal

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _require_env(name: str) -> str:
    """读取必需的环境变量，缺失直接报错（不允许默认值）。"""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required env var: {name}. "
            f"Set it in .env (local) or GitHub Secrets (CI)."
        )
    return value


def _get_client() -> OpenAI:
    """构造 OpenAI 兼容 client。

    支持任何遵循 OpenAI Chat Completions 协议的服务：
    OpenAI 官方 / DeepSeek / Doubao / OneAPI 中转网关等。
    通过 LLM_API_KEY + LLM_BASE_URL 两个环境变量配置，无默认值。
    """
    return OpenAI(
        api_key=_require_env("LLM_API_KEY"),
        base_url=_require_env("LLM_BASE_URL"),
    )


def _load_prompt(lang: str) -> str:
    path = PROMPTS_DIR / f"analyze.{lang}.md"
    return path.read_text(encoding="utf-8")


def _extract_json(text: str) -> str:
    """从 LLM 返回文本提取 JSON：兼容 markdown code fence 包裹。

    有些模型/网关即使请求 response_format=json_object 仍会包 ```json ... ```。
    """
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
    return match.group(1) if match else text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=20))
def analyze(signals: list[Signal], lang: str, date: str) -> dict:
    client = _get_client()
    model = _require_env("LLM_MODEL")

    prompt_template = _load_prompt(lang)
    sources_json = json.dumps(
        [
            {
                "source": s.source,
                "title": s.title,
                "url": s.url,
                "score": round(s.score, 2),
                "raw_score": s.raw_score,
                "comments": s.comments,
                "summary": s.summary,
                "tags": s.tags,
            }
            for s in signals
        ],
        ensure_ascii=False,
        indent=2,
    )

    prompt = prompt_template.replace("{{sources_json}}", sources_json).replace(
        "{{date}}", date
    )

    system_msg = (
        "你是一个独立开发者趋势观察员，输出严格 JSON。"
        if lang == "zh"
        else "You are a tech trend analyst for indie builders. Output strict JSON."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]

    # 优先用 response_format 强制 JSON；不支持的模型降级为纯文本对话
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.4,
        )
    except Exception as err:
        reason = str(err).lower()
        if "response_format" in reason or "json_object" in reason:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.4,
            )
        else:
            raise

    content = response.choices[0].message.content
    return json.loads(_extract_json(content))
