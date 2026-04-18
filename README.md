<p align="center">
  <img src="./logo.svg" width="96" alt="DailyDawn logo" />
</p>

<h1 align="center">DailyDawn · 独立开发者的 AI 趋势日报</h1>

<p align="center"><b>🌐 <a href="./README.md">中文</a> · <a href="./README.en.md">English</a></b></p>

> **每天清晨 30 分钟，看清今天值得做什么、要避开什么、谁在颠覆谁。**

[![Daily Report](https://github.com/TangSY/dailydawn/actions/workflows/daily-report.yml/badge.svg)](https://github.com/TangSY/dailydawn/actions/workflows/daily-report.yml)
[![Latest zh](https://img.shields.io/badge/今日中文-zh%2F今日.md-orange)](./zh/)
[![Latest en](https://img.shields.io/badge/Today%20EN-en%2Ftoday.md-orange)](./en/)

---

## 为什么值得每天看

你可能每天早上都要在 HN、Product Hunt、Reddit、HuggingFace、GitHub Trending 之间来回翻，手工拼出「今天到底发生了什么」。这种活儿，LLM 比人做得又快又全。

DailyDawn 替你把这件事干完：每天 UTC 00:00 自动从 7 个信号源抓 150+ 条原始信号，跨源去重后分进 5 个维度（**发现机会 / 技术选型 / 竞争情报 / 需求雷达 / 趋势判断**），每个维度派一个 agent 深挖，再由主笔合成一篇结构化中英双语日报。

每篇约 5000 中文字 / 5500 英文词，包含：

- **20 个今日专属深度小节**——问题基于当日实际信号动态生成，每天都不一样
- **三级构建建议**——今日 2 小时构建 / 周末扩展 / 本周更长线的赌注 / 本周风险
- **跨源关键词涨幅**——Google Trends 7 日上升的搜索词，捕获买家意图
- 整体围绕「**独立开发者本周该做什么**」组织，不是新闻搬运

---

## 看一眼今天

- 📖 [中文最新](./zh/) · [English latest](./en/)
- 📦 [完整归档（中文）](./zh/2026/) · [Archive (English)](./en/2026/)
- 🌐 在线网站：<https://dailydawn.dev>
- 📬 邮件订阅：<https://dailydawn.dev>（中英分发，可一键切换）
- 📡 RSS / JSON Feed：<https://dailydawn.dev/zh.json> · <https://dailydawn.dev/en.json>

---

## 一篇日报的样子

```
# DailyDawn · 2026-04-18

> 📍 今日 Top 3 信号
> 1. 高置信度：…1937 票 / 1425 评论…
> 2. 外部发现：…"agent memory" 7 日搜索 +120%…
> 3. 双重验证：…HN + PH + HuggingFace 三源同步…

## 🗣 技术派说（600+ 字 POV 开篇）
## 🎯 今日 2 小时构建（一个具体可执行的点子）

## 发现机会（4 个今日专属子问题）
## 技术选型（4 个）
## 竞争情报（4 个）
## 需求雷达（4 个）
## 趋势判断（4 个，含关键词涨幅）

## 🔥 行动触发
### 周末扩展构建
### 这一周更长线的赌注
### 本周最大的风险 / 陷阱
```

20 个 H3 子小节 + 三级构建 + 反向视角，每天问题都不一样（动态生成）。

---

## 数据源

| 源 | 接入 | 说明 |
|---|---|---|
| Hacker News | Algolia API | 24h 内 points>20 的 story（避免历史长尾） |
| GitHub Trending | HTML 爬取 | 当日 trending 仓库 Top 25 |
| Product Hunt | GraphQL API | 当日 votes top 20 |
| Reddit | 公开 JSON | 12 个 sub（含 r/indiehackers、r/SideProject） |
| HuggingFace | 公开 API | 7 日 likes 升序的模型 + 数据集 |
| V2EX | 公开 API | 中文技术社区热议 |
| Google Trends | pytrends | 20 个独立开发者关键词的 7 日涨幅 |

任意源失败自动跳过，不阻塞主流程（`safe_fetch` 包装）。

---

## 工作原理

```
GitHub Actions cron (UTC 00:00)
    │
    ├─ fetchers/*  并发抓 150+ signals (~30s)
    ├─ aggregator  跨源去重 + 分数叠加 + Top60 + 保留全部 Trends
    │
    ├─ pipeline/classifier        → 5 buckets (tech/launch/competition/demand/trend)
    ├─ pipeline/question_generator → 20 个今日专属 H3 问题（zh + en 各一份）
    ├─ pipeline/source_digest      → 每源 cluster 摘要
    │
    ├─ pipeline/experts × 5 × 2 lang  → 5 × 4 子小节深度分析
    ├─ pipeline/editor × 2 lang       → POV 开篇 + Top3 + 三级构建合成
    │
    ├─ renderer  → zh/YYYY/YYYY-MM-DD.md + en/YYYY/YYYY-MM-DD.md
    ├─ git commit + push
    └─ webhook  → 通知 Web 层批量发邮件
```

每天约 18 次 LLM 调用（OpenAI 兼容协议，可接 DeepSeek / OpenAI / Doubao 等）。

---

## 技术栈

- **Python 3.12** + `httpx` + `asyncio` 全异步
- **OpenAI SDK** 接任意 OpenAI 兼容 LLM 网关
- **GitHub Actions** 调度 + commit + webhook
- **pytrends** 抓 Google Trends 关键词涨幅
- **tenacity** 指数退避 + LLM 失败降级
- 共 ~1500 行 Python，零数据库

Web 层在另一仓库（私有），Cloudflare Workers + D1 + Queues + Resend。

---

## 想自己跑

```bash
git clone https://github.com/TangSY/dailydawn
cd dailydawn
pip install -r requirements.txt
cp .env.example .env  # 填 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
python scripts/main.py  # 跑一次，产出 zh/2026/今日.md + en/2026/今日.md
```

---

## License

MIT
