from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.aggregator import aggregate
from scripts.fetchers import ALL_FETCHERS
from scripts.pipeline.orchestrator import run_pipeline
from scripts.renderer import save_report

load_dotenv()

# 产出 summary 给 CI workflow 读取 → curl 打 Web 层 webhook。
# 放 /tmp 避免被 git 追踪，workflow 里用 `--data-binary @file` 直接发送。
_SUMMARY_OUTPUT_PATH = Path("/tmp/dailydawn-summary.json")

# 跨日主题去重锚：每天 pipeline 跑完 append 一条到 meta/recent-taglines.jsonl，
# 次日 pipeline 读最后 N 条传给 editor，prompt 里硬约束禁止主题重合。
# workflow 里 `git add meta/` 和 zh/ en/ 一起提交。
_RECENT_TAGLINES_PATH = Path(__file__).parent.parent / "meta" / "recent-taglines.jsonl"


async def fetch_all() -> list:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetcher().safe_fetch(client) for fetcher in ALL_FETCHERS]
        results = await asyncio.gather(*tasks)

    signals = []
    for result in results:
        signals.extend(result)
    print(f"✓ Fetched {len(signals)} signals from {len(ALL_FETCHERS)} sources")
    return signals


def _load_recent_taglines(days: int = 7) -> list[dict]:
    """读 meta/recent-taglines.jsonl 尾部 N 条。文件不存在或 jsonl 行损坏时降级返回。"""
    if not _RECENT_TAGLINES_PATH.exists():
        return []
    try:
        lines = _RECENT_TAGLINES_PATH.read_text(encoding="utf-8").strip().splitlines()
    except OSError as err:
        print(f"⚠ recent-taglines read failed ({err}); treating as empty")
        return []
    recent: list[dict] = []
    for line in lines[-days:]:
        line = line.strip()
        if not line:
            continue
        try:
            recent.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return recent


def _append_recent_taglines(date: str, reports: dict) -> None:
    """跑完 pipeline 把今日 tagline + top3_themes append 到 jsonl，workflow commit meta/。"""
    zh = reports.get("zh") or {}
    en = reports.get("en") or {}
    entry = {
        "date": date,
        "tagline_zh": zh.get("tagline"),
        "tagline_en": en.get("tagline"),
        "top3_themes_zh": zh.get("top3_themes") or [],
        "top3_themes_en": en.get("top3_themes") or [],
    }
    if not (entry["tagline_zh"] or entry["tagline_en"]):
        print("⚠ no tagline generated, skipping recent-taglines append")
        return
    try:
        _RECENT_TAGLINES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _RECENT_TAGLINES_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        rel = _RECENT_TAGLINES_PATH.relative_to(Path(__file__).parent.parent)
        print(f"✓ appended to {rel}")
    except OSError as err:
        print(f"⚠ recent-taglines append failed ({err})")


def _write_summary_payload(date: str, reports: dict) -> None:
    """把双语 tagline + top3_themes 落到 /tmp 供 CI 读取发 webhook。

    topics 字段直接复用 top3_themes（LLM 已生成的 ≤15 字主题词，3 项），
    Web 层会用作详情页 <title> 长尾词后缀 + JSON-LD Article keywords。
    """
    zh = reports.get("zh") or {}
    en = reports.get("en") or {}
    payload = {
        "date": date,
        "summary_zh": zh.get("tagline"),
        "summary_en": en.get("tagline"),
        "topics_zh": zh.get("top3_themes") or [],
        "topics_en": en.get("top3_themes") or [],
    }
    try:
        _SUMMARY_OUTPUT_PATH.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        print(
            f"✓ summary payload written to {_SUMMARY_OUTPUT_PATH}: "
            f"zh={'✓' if payload['summary_zh'] else '—'}({len(payload['topics_zh'])} topics) "
            f"en={'✓' if payload['summary_en'] else '—'}({len(payload['topics_en'])} topics)"
        )
    except OSError as err:
        # 本地跑没 /tmp 或 CI 环境不同都不阻塞内容生成
        print(f"⚠ summary payload write failed ({err}); webhook will only carry date")


async def amain() -> None:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"=== DailyDawn · {date} ===")

    signals = await fetch_all()
    if not signals:
        print("✗ No signals fetched, aborting.")
        sys.exit(1)

    ranked = aggregate(signals)
    print(f"✓ Aggregated to {len(ranked)} unique signals")

    recent_taglines = _load_recent_taglines(days=7)
    print(f"✓ Loaded {len(recent_taglines)} recent taglines (dedupe anchor for editor)")

    print("→ Running multi-agent pipeline (classifier → digest → experts × 4 → editor)...")
    reports = await run_pipeline(
        date=date,
        signals=ranked,
        recent_taglines=recent_taglines,
    )

    for lang, result in reports.items():
        markdown = (result or {}).get("markdown") or ""
        if not markdown:
            print(f"✗ [{lang}] empty output, skipping save")
            continue
        path = save_report(markdown, lang, date)
        print(f"✓ [{lang}] saved to {path.relative_to(Path(__file__).parent.parent)}")

    _append_recent_taglines(date, reports)
    _write_summary_payload(date, reports)


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
