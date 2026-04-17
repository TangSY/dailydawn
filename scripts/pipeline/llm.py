from __future__ import annotations

import json
import os
import re
from pathlib import Path

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required env var: {name}. "
            f"Set it in .env (local) or GitHub Secrets (CI)."
        )
    return value


def get_client() -> OpenAI:
    """构造 OpenAI 兼容 client（复用 llm_analyzer 的配置契约）。"""
    return OpenAI(
        api_key=_require_env("LLM_API_KEY"),
        base_url=_require_env("LLM_BASE_URL"),
    )


def get_model() -> str:
    return _require_env("LLM_MODEL")


def load_prompt(name: str) -> str:
    """加载 prompts/{name} 文件（name 含扩展名，如 'classifier.md'）。"""
    path = PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


def _extract_json(text: str) -> str:
    """兼容 markdown code fence 包裹的 JSON。"""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\{\[][\s\S]*[\}\]])\s*```", text)
    return match.group(1) if match else text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=20))
def call_json(
    system: str,
    user: str,
    *,
    temperature: float = 0.4,
    model: str | None = None,
) -> dict | list:
    """调用 LLM 并解析 JSON 输出。失败时指数退避重试 3 次。"""
    client = get_client()
    model = model or get_model()

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
    except Exception as err:
        reason = str(err).lower()
        if "response_format" in reason or "json_object" in reason:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
        else:
            raise

    content = response.choices[0].message.content
    return json.loads(_extract_json(content))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=20))
def call_text(
    system: str,
    user: str,
    *,
    temperature: float = 0.5,
    model: str | None = None,
) -> str:
    """调用 LLM 返回纯文本（主笔合成 markdown 用）。"""
    client = get_client()
    model = model or get_model()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()
