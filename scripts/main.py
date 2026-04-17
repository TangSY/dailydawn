from __future__ import annotations

import asyncio
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


async def fetch_all() -> list:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetcher().safe_fetch(client) for fetcher in ALL_FETCHERS]
        results = await asyncio.gather(*tasks)

    signals = []
    for result in results:
        signals.extend(result)
    print(f"✓ Fetched {len(signals)} signals from {len(ALL_FETCHERS)} sources")
    return signals


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

    for lang, markdown in reports.items():
        if not markdown:
            print(f"✗ [{lang}] empty output, skipping save")
            continue
        path = save_report(markdown, lang, date)
        print(f"✓ [{lang}] saved to {path.relative_to(Path(__file__).parent.parent)}")


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
