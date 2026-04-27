<p align="center">
  <img src="./logo.svg" width="96" alt="DailyDawn logo" />
</p>

<h1 align="center">DailyDawn · Daily AI brief for indie builders</h1>

<p align="center"><b>🌐 <a href="./README.en.md">English</a> · <a href="./README.md">中文</a></b></p>

> **30 minutes every morning to see what to ship, what to skip, who's eating whose lunch.**

[![Daily Report](https://github.com/TangSY/dailydawn/actions/workflows/daily-report.yml/badge.svg)](https://github.com/TangSY/dailydawn/actions/workflows/daily-report.yml)
[![Latest EN](https://img.shields.io/badge/Today%20EN-en%2Ftoday.md-orange)](./en/)
[![Latest zh](https://img.shields.io/badge/今日中文-zh%2F今日.md-orange)](./zh/)

<!-- LATEST_ISSUES_START -->

## Latest 3 issues

- [2026-04-27 · Job-Aligned Skill Tracking / Dev Employability Tools / Skill-Recruiter Integration](https://dailydawn.dev/en/2026-04-27)
  > Skill-tracking repo leads GitHub as devs prioritize role-specific upskilling
- [2026-04-26 · DIY Core Tools Repo / Modular Pen-Testing Kit / DIY Tool Adoption Surge](https://dailydawn.dev/en/2026-04-26)
  > DIY tool repo surges on GitHub as indie builders skip paid AI platforms
- [2026-04-25 · ML Intern Prep Repo / DeepSeek V4 Criticism / AI Industry Consolidation](https://dailydawn.dev/en/2026-04-25)
  > Hugging Face ML intern repo tops GitHub Trending as devs chase open AI roles

[Full archive →](https://dailydawn.dev/en/archive)

<!-- LATEST_ISSUES_END -->

---

## Why read it daily

You probably bounce between HN, Product Hunt, Reddit, HuggingFace, and GitHub Trending every morning, manually piecing together "what actually happened today." LLMs do this faster and more thoroughly than humans can.

DailyDawn handles it for you: every day at UTC 00:00 it pulls 150+ raw signals from 7 sources, dedupes across them, sorts them into 5 dimensions (**Launch discoveries / Tech stack / Competitive intel / Demand radar / Trend verdict**), spins up one agent per dimension for deep analysis, and has an editor-in-chief synthesize a structured bilingual report.

Each issue is around 5,000 Chinese characters / 5,500 English words and contains:

- **20 today-specific deep sub-sections** — questions are dynamically generated from today's actual signals; they change every day
- **Three-tier build advice** — today's 2-hour build / weekend extension / this week's longer bet / weekly risk
- **Cross-source keyword growth** — Google Trends 7-day rising queries that surface buyer intent
- Everything organized around "**what should an indie builder do this week**" — not news regurgitation

---

## Read now

- 📖 Today: [English](./en/) · [中文](./zh/)
- 📦 Full archive: [English](./en/2026/) · [中文](./zh/2026/)
- 🌐 Web: <https://dailydawn.dev>
- 📬 Email subscription: <https://dailydawn.dev> (bilingual, 1-click language switch)
- 📡 RSS / JSON Feed: <https://dailydawn.dev/en.json> · <https://dailydawn.dev/zh.json>

---

## What every issue looks like

```
# DailyDawn · 2026-04-18

> 📍 Top 3 signals
> 1. High confidence: …1937 votes / 1425 comments…
> 2. External find: …"agent memory" search +120% in 7d…
> 3. Double validation: …HN + PH + HuggingFace cross-source overlap…

## 🗣 Editor's take (600+ word POV opener)
## 🎯 Today's 2-hour build (one concrete actionable idea)

## Launch discoveries  (4 today-specific sub-questions)
## Tech stack          (4)
## Competitive intel   (4)
## Demand radar        (4)
## Trend verdict       (4, with keyword growth)

## 🔥 Action triggers
### Weekend extension build
### Longer bet this week
### Biggest risk / trap this week
```

5 sections × 4 today-specific sub-questions = **20 deep angles**, all dynamically generated from today's actual signals (so the questions change daily). Every sub-section comes with a **Key call** and a **Counterpoint**.

---

## Data sources

| Source | Method | Notes |
|---|---|---|
| Hacker News | Algolia API | Stories from last 24h with points>20 |
| GitHub Trending | HTML scrape | Top 25 trending repos today |
| Product Hunt | GraphQL API | Top 20 by votes today |
| Reddit | Public JSON | 12 subreddits incl. r/indiehackers, r/SideProject |
| HuggingFace | Public API | Models + datasets sorted by 7-day likes |
| V2EX | Public API | Chinese tech community heat |
| Google Trends | pytrends | 20 indie-builder keywords' 7-day growth |

Any source failure auto-skips without blocking the pipeline.

---

## How it works

```
GitHub Actions cron · daily at UTC 00:00
    │
    ├─ fetchers/*       Concurrently pull 150+ raw signals (~30s)
    ├─ aggregator       Cross-source dedup · Top 60 + all Trends preserved
    │
    ├─ classifier               Sort signals into 5 buckets
    ├─ question_generator       Generate 20 today-specific questions (zh + en)
    ├─ source_digest            Per-source cluster summary
    │
    ├─ experts × 5 × 2 lang     5 experts × 4 sub-section deep analysis
    └─ editor × 2 lang          POV opener + Top 3 + 3-tier build synthesis
        │
        ├─ renderer  → zh/YYYY/YYYY-MM-DD.md + en/...
        ├─ git push
        └─ webhook   → Web layer batch-sends email
```

About 18 LLM calls per day, against any OpenAI-compatible gateway (DeepSeek / OpenAI / Doubao all work).

---

## Tech stack

- **Python 3.12** · `httpx` · `asyncio` (fully async)
- **OpenAI SDK** against any OpenAI-compatible LLM gateway
- **GitHub Actions** for scheduling + commit + webhook
- **pytrends** for Google Trends keyword growth
- **tenacity** for exponential backoff + graceful degradation
- ~1500 lines of Python, no database

The Web layer (subscriptions, email distribution) lives in a separate private repo — Cloudflare Workers + D1 + Queues + Resend.

---

## Run locally

```bash
git clone https://github.com/TangSY/dailydawn
cd dailydawn
pip install -r requirements.txt
cp .env.example .env  # Fill in LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
python scripts/main.py  # One run produces zh/2026/today.md + en/2026/today.md
```

---

## License

MIT
