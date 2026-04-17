from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.aggregator import aggregate
from scripts.fetchers import ALL_FETCHERS
from scripts.llm_analyzer import analyze
from scripts.renderer import render_markdown, save_report

load_dotenv()


async def fetch_all() -> list:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetcher().safe_fetch(client) for fetcher in ALL_FETCHERS]
        results = await asyncio.gather(*tasks)

    signals = []
    for result in results:
        signals.extend(result)
    print(f"✓ Fetched {len(signals)} signals from {len(ALL_FETCHERS)} sources")
    return signals


def main() -> None:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"=== DailyDawn · {date} ===")

    signals = asyncio.run(fetch_all())
    if not signals:
        print("✗ No signals fetched, aborting.")
        sys.exit(1)

    ranked = aggregate(signals)
    print(f"✓ Aggregated to {len(ranked)} unique signals")

    for lang in ("zh", "en"):
        print(f"→ Analyzing [{lang}]...")
        try:
            report = analyze(ranked, lang, date)
        except Exception as e:
            print(f"✗ [{lang}] analysis failed: {e}")
            continue

        markdown = render_markdown(report, lang, date)
        path = save_report(markdown, lang, date)
        print(f"✓ [{lang}] saved to {path.relative_to(Path(__file__).parent.parent)}")


if __name__ == "__main__":
    main()
