from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .fetchers.base import Signal

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _get_client() -> OpenAI:
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
    if provider == "deepseek":
        return OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com/v1",
        )
    if provider == "openai":
        return OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


def _load_prompt(lang: str) -> str:
    path = PROMPTS_DIR / f"analyze.{lang}.md"
    return path.read_text(encoding="utf-8")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=20))
def analyze(signals: list[Signal], lang: str, date: str) -> dict:
    client = _get_client()
    model = os.getenv("LLM_MODEL", "deepseek-chat")

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

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个独立开发者趋势观察员，输出严格 JSON。"
             if lang == "zh"
             else "You are a tech trend analyst for indie builders. Output strict JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    content = response.choices[0].message.content
    return json.loads(content)
