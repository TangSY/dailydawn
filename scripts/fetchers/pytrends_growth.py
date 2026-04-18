from __future__ import annotations

import asyncio
import time

import httpx

from .base import BaseFetcher, Signal

# 固定关键词集：独立开发者买家意图聚焦词
# 每日查这 20 个词在 Google Trends 上的 7 日涨幅（前半周 vs 后半周 hourly average）
SEED_KEYWORDS = [
    "ai agent",
    "claude code",
    "llm local",
    "vibe coding",
    "indie hackers",
    "saas boilerplate",
    "vector database",
    "agent memory",
    "prompt engineering",
    "open source llm",
    "llm fine tuning",
    "cloudflare workers",
    "vercel ai",
    "hugging face",
    "ollama",
    "langchain alternative",
    "rag",
    "agentic workflow",
    "mcp",
    "a2a protocol",
]

# pytrends 单次查询上限 5 个关键词
_BATCH_SIZE = 5
_INTER_BATCH_SLEEP = 2.0

# 过滤弱信号：7 日涨幅低于此值的不入库
_MIN_GROWTH_PCT = 20.0


class PyTrendsGrowthFetcher(BaseFetcher):
    """
    通过 pytrends 库查 SEED_KEYWORDS 在过去 7 天的搜索量增长率。

    对比逻辑：timeframe='now 7-d' 取 hourly data (168 点)，
    把前 84 小时和后 84 小时均值做增长率计算。

    failure mode: pytrends 对 Google 未公开接口，偶发 429。
    单 batch 失败不影响其他 batch。全部失败返空数组，pipeline 降级到"低信号日"处理。
    """

    source_name = "pytrends_growth"
    timeout = 30.0

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        # pytrends 是同步库，用 asyncio.to_thread 避免阻塞 event loop
        return await asyncio.to_thread(self._fetch_sync)

    def _fetch_sync(self) -> list[Signal]:
        # 延迟 import 避免模块加载时强依赖（但 CLAUDE.md 禁止函数内 import）
        # pytrends 在顶部 import 见 requirements.txt 保证可用
        from pytrends.request import TrendReq  # type: ignore

        try:
            py = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=0.5)
        except Exception as err:
            print(f"[pytrends_growth] init failed: {err}")
            return []

        signals: list[Signal] = []
        for batch in _chunks(SEED_KEYWORDS, _BATCH_SIZE):
            try:
                py.build_payload(batch, timeframe="now 7-d", geo="")
                df = py.interest_over_time()
            except Exception as err:
                print(f"[pytrends_growth:{batch}] query failed: {type(err).__name__}: {err}")
                time.sleep(_INTER_BATCH_SLEEP)
                continue

            if df is None or df.empty:
                time.sleep(_INTER_BATCH_SLEEP)
                continue

            for kw in batch:
                if kw not in df.columns:
                    continue
                series = df[kw].astype(float).values
                if len(series) < 4:
                    continue
                half = len(series) // 2
                early = float(series[:half].mean())
                late = float(series[half:].mean())
                if early < 1.0:
                    continue
                growth = (late - early) / early * 100.0
                if growth < _MIN_GROWTH_PCT:
                    continue

                signals.append(
                    Signal(
                        source="Google Trends",
                        title=f'"{kw}" +{growth:.0f}% (7d)',
                        url=f"https://trends.google.com/trends/explore?q={kw.replace(' ', '+')}",
                        raw_score=int(growth),
                        score=min(growth / 500.0, 1.0),
                        summary=(
                            f"'{kw}' search interest rose {growth:.0f}% comparing "
                            f"late-week vs early-week hourly averages in the past 7 days."
                        ),
                        tags=["search_trend", "buyer_intent"],
                        extra={
                            "keyword": kw,
                            "growth_pct_7d": round(growth, 1),
                            "early_avg": round(early, 1),
                            "late_avg": round(late, 1),
                        },
                    )
                )

            time.sleep(_INTER_BATCH_SLEEP)

        return signals


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
