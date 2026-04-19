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


async def fetch_all() -> list:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetcher().safe_fetch(client) for fetcher in ALL_FETCHERS]
        results = await asyncio.gather(*tasks)

    signals = []
    for result in results:
        signals.extend(result)
    print(f"✓ Fetched {len(signals)} signals from {len(ALL_FETCHERS)} sources")
    return signals


def _write_summary_payload(date: str, reports: dict) -> None:
    """把双语 tagline 落到 /tmp 供 CI 读取发 webhook。"""
    payload = {
        "date": date,
        "summary_zh": (reports.get("zh") or {}).get("tagline"),
        "summary_en": (reports.get("en") or {}).get("tagline"),
    }
    try:
        _SUMMARY_OUTPUT_PATH.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        print(
            f"✓ summary payload written to {_SUMMARY_OUTPUT_PATH}: "
            f"zh={'✓' if payload['summary_zh'] else '—'} "
            f"en={'✓' if payload['summary_en'] else '—'}"
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

    print("→ Running multi-agent pipeline (classifier → digest → experts × 4 → editor)...")
    reports = await run_pipeline(date=date, signals=ranked)

    for lang, result in reports.items():
        markdown = (result or {}).get("markdown") or ""
        if not markdown:
            print(f"✗ [{lang}] empty output, skipping save")
            continue
        path = save_report(markdown, lang, date)
        print(f"✓ [{lang}] saved to {path.relative_to(Path(__file__).parent.parent)}")

    _write_summary_payload(date, reports)


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
