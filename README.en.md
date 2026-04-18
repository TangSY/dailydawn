<p align="center">
  <img src="./logo.svg" width="96" alt="DailyDawn logo" />
</p>

<h1 align="center">DailyDawn · Daily AI signal for indie builders</h1>

<p align="center"><b>🌐 <a href="./README.en.md">English</a> · <a href="./README.md">中文</a></b></p>

> **30 minutes every morning to see what to build, what to avoid, who's threatening whom.**

[![Daily Report](https://github.com/TangSY/dailydawn/actions/workflows/daily-report.yml/badge.svg)](https://github.com/TangSY/dailydawn/actions/workflows/daily-report.yml)
[![Latest EN](https://img.shields.io/badge/Today%20EN-en%2Ftoday.md-orange)](./en/)
[![Latest zh](https://img.shields.io/badge/今日中文-zh%2F今日.md-orange)](./zh/)

---

## Why read it

You probably toggle between HN, Product Hunt, Reddit, HuggingFace, and GitHub Trending every morning, manually stitching together "what actually happened today." LLMs do this faster and more thoroughly than you can.

**What DailyDawn does**: every day at UTC 00:00, it pulls 150+ raw signals from 7 sources, deduplicates across them, runs them through a 5-bucket multi-agent classifier, and produces one structured bilingual report. 20 today-specific H3 sub-sections (the questions change daily) + three-tier build advice (2 hours / weekend / this week) + cross-source keyword growth.

About 5,000 Chinese characters / 5,500 English words per day, organized around "what should an indie builder do this week" — not news regurgitation.

---

## See today's issue

- 📖 [Today (EN)](./en/) · [今日（中文）](./zh/)
- 📦 [Full archive (EN)](./en/2026/) · [完整归档（中文）](./zh/2026/)
- 🌐 Web: <https://dailydawn.dev>
- 📬 Email subscription: <https://dailydawn.dev> (bilingual; 1-click language switch)
- 📡 RSS / JSON Feed: <https://dailydawn.dev/en.json> · <https://dailydawn.dev/zh.json>

---

## What an issue looks like

```
# DailyDawn · 2026-04-18

> 📍 Top 3 signals
> 1. High confidence: …1937 votes / 1425 comments…
> 2. External find: …"agent memory" search +120% in 7d…
> 3. Double validation: …HN + PH + HuggingFace cross-source overlap…

## 🗣 Editor's take (600+ word POV opener)
## 🎯 Today's 2-hour build (one concrete actionable idea)

## Launch discoveries (4 today-specific sub-questions)
## Tech stack (4)
## Competitive intel (4)
## Demand radar (4)
## Trend verdict (4, with keyword growth)

## 🔥 Action triggers
### Weekend extension build
### Longer bet this week
### Biggest risk / trap this week
```

20 H3 sub-sections + 3-tier build + counterpoints. **Questions change every day** (dynamically generated from today's signals).

---

## Data sources

| Source | Method | Notes |
|---|---|---|
| Hacker News | Algolia API | Stories from last 24h with points>20 (avoids historical long tail) |
| GitHub Trending | HTML scrape | Top 25 trending repos today |
| Product Hunt | GraphQL API | Top 20 by votes today |
| Reddit | Public JSON | 12 subreddits incl. r/indiehackers, r/SideProject |
| HuggingFace | Public API | Models + datasets sorted by 7-day likes |
| V2EX | Public API | Chinese tech community heat |
| Google Trends | pytrends | 20 indie-builder keywords' 7-day growth |

Any source failure auto-skips without blocking the main flow (`safe_fetch` wrapper).

---

## How it works

```
GitHub Actions cron (UTC 00:00)
    │
    ├─ fetchers/*  Concurrently pull 150+ signals (~30s)
    ├─ aggregator  Cross-source dedup + score boost + Top60 + preserve all Trends
    │
    ├─ pipeline/classifier         → 5 buckets (tech/launch/competition/demand/trend)
    ├─ pipeline/question_generator → 20 today-specific H3 questions (zh + en separate)
    ├─ pipeline/source_digest      → Per-source cluster summary
    │
    ├─ pipeline/experts × 5 × 2 lang  → 5 × 4 sub-section deep analysis
    ├─ pipeline/editor × 2 lang       → POV opener + Top 3 + 3-tier build synthesis
    │
    ├─ renderer  → zh/YYYY/YYYY-MM-DD.md + en/YYYY/YYYY-MM-DD.md
    ├─ git commit + push
    └─ webhook  → Notify Web layer for batch email send
```

About 18 LLM calls per day (OpenAI-compatible protocol — works with DeepSeek / OpenAI / Doubao / any compliant gateway).

---

## Tech stack

- **Python 3.12** + `httpx` + `asyncio` fully async
- **OpenAI SDK** against any OpenAI-compatible LLM gateway
- **GitHub Actions** for scheduling + commit + webhook
- **pytrends** for Google Trends keyword growth
- **tenacity** for exponential backoff + LLM failure fallback
- About 1500 lines of Python total. No database.

The Web layer (subscriptions / email distribution) is in a separate private repo — Cloudflare Workers + D1 + Queues + Resend.

---

## Run it yourself

```bash
git clone https://github.com/TangSY/dailydawn
cd dailydawn
pip install -r requirements.txt
cp .env.example .env  # Fill in LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
python scripts/main.py  # One-shot run, produces zh/2026/today.md + en/2026/today.md
```

---

## License

MIT
