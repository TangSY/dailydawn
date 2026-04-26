<p align="center">
  <img src="./logo.svg" width="96" alt="DailyDawn logo" />
</p>

<h1 align="center">DailyDawn · 独立开发者的 AI 趋势日报</h1>

<p align="center"><b>🌐 <a href="./README.md">中文</a> · <a href="./README.en.md">English</a></b></p>

> **每天清晨 30 分钟，看清今天值得做什么、要避开什么、谁在颠覆谁。**

[![Daily Report](https://github.com/TangSY/dailydawn/actions/workflows/daily-report.yml/badge.svg)](https://github.com/TangSY/dailydawn/actions/workflows/daily-report.yml)
[![Latest zh](https://img.shields.io/badge/今日中文-zh%2F今日.md-orange)](./zh/)
[![Latest en](https://img.shields.io/badge/Today%20EN-en%2Ftoday.md-orange)](./en/)

<!-- LATEST_ISSUES_START -->

## 最近 3 期日报

- [2026-04-26 · 复刻式编程学习 / 黑客工具热度攀升 / ML实践导向学习](https://dailydawn.dev/zh/2026-04-26)
  > 复刻式编程学习仓库登GitHub趋势，ML入门转向任务实践
- [2026-04-25 · ML实习项目集登顶 / 开源ML工具热度 / 跨源AI项目联动](https://dailydawn.dev/zh/2026-04-25)
  > HuggingFace ML实习项目集登GitHub趋势榜首
- [2026-04-24 · 免费Claude Code工具 / 黑客工具热度飙升 / 闭源模型用户逃逸](https://dailydawn.dev/zh/2026-04-24)
  > 免费Claude Code工具登GitHub趋势，黑客工具热度飙升

[全部归档 →](https://dailydawn.dev/archive)

<!-- LATEST_ISSUES_END -->

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

## 立刻读

- 📖 今天：[中文](./zh/) · [English](./en/)
- 📦 全部归档：[中文](./zh/2026/) · [English](./en/2026/)
- 🌐 网站：<https://dailydawn.dev>
- 📬 邮件订阅：<https://dailydawn.dev>（中英可一键切换）
- 📡 RSS / JSON Feed：<https://dailydawn.dev/zh.json> · <https://dailydawn.dev/en.json>

---

## 一篇日报长这样

```
# DailyDawn · 2026-04-18

> 📍 今日 Top 3 信号
> 1. 高置信度：…1937 票 / 1425 评论…
> 2. 外部发现：…"agent memory" 7 日搜索 +120%…
> 3. 双重验证：…HN + PH + HuggingFace 三源同步…

## 🗣 技术派说（600+ 字 POV 开篇）
## 🎯 今日 2 小时构建（一个具体可执行的点子）

## 发现机会     （4 个今日专属子问题）
## 技术选型     （4 个）
## 竞争情报     （4 个）
## 需求雷达     （4 个）
## 趋势判断     （4 个，含关键词涨幅）

## 🔥 行动触发
### 周末扩展构建
### 这一周更长线的赌注
### 本周最大的风险 / 陷阱
```

5 大章节 × 4 个今日专属子小节 = **20 个深度切面**，每天的问题都不一样（基于当日信号动态生成）。每节都带「关键判断」+「反向视角」。

---

## 数据源

| 源 | 接入方式 | 说明 |
|---|---|---|
| Hacker News | Algolia API | 24 小时内 points>20 的 story |
| GitHub Trending | HTML 爬取 | 当日 trending Top 25 |
| Product Hunt | GraphQL API | 当日 votes Top 20 |
| Reddit | 公开 JSON | 12 个 subreddit，含 r/indiehackers、r/SideProject |
| HuggingFace | 公开 API | 7 日 likes 排序的模型 + 数据集 |
| V2EX | 公开 API | 中文技术社区热议 |
| Google Trends | pytrends | 20 个独立开发者关键词的 7 日涨幅 |

任一源失败自动跳过，不阻塞流水线。

---

## 幕后流程

```
GitHub Actions cron · 每天 UTC 00:00
    │
    ├─ fetchers/*       并发抓 150+ 条原始信号 （约 30 秒）
    ├─ aggregator       跨源去重 · Top 60 + 全部 Trends 保留
    │
    ├─ classifier               把信号分进 5 个 bucket
    ├─ question_generator       为今天生成 20 个专属问题（zh + en）
    ├─ source_digest            每源聚类摘要
    │
    ├─ experts × 5 × 2 lang     5 个专家 × 4 子小节深度分析
    └─ editor × 2 lang          POV 开篇 + Top 3 + 三级构建合成
        │
        ├─ renderer  → zh/YYYY/YYYY-MM-DD.md + en/...
        ├─ git push
        └─ webhook   → Web 层批量发邮件
```

每天约 18 次 LLM 调用，走任意 OpenAI 兼容网关（DeepSeek / OpenAI / Doubao 等都行）。

---

## 技术栈

- **Python 3.12** · `httpx` · `asyncio` 全异步
- **OpenAI SDK** 兼容任意 LLM 网关
- **GitHub Actions** 调度 + commit + webhook
- **pytrends** 抓 Google Trends 关键词涨幅
- **tenacity** 指数退避重试 + 优雅降级
- ~1500 行 Python，零数据库

Web 层（订阅 / 邮件分发）在另一私有仓库：Cloudflare Workers + D1 + Queues + Resend。

---

## 本地跑起来

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
