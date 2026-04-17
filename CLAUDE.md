# DailyDawn · 内容引擎

> **本文件会被 Claude Code 自动加载到上下文。如果你是第一次打开这个项目的新会话，读完本文件即可接手。**

---

## 🎯 这个仓库是什么

**DailyDawn** 的内容引擎——每天 UTC 00:00 通过 GitHub Actions 跑一次 Python 脚本，从 7 个数据源聚合信号，用 LLM 生成中英双语 Markdown 日报，commit 到本仓库，然后 curl 通知 Web 层（`dailydawn-web`）批量发邮件。

**主上下文和待办清单在姐妹仓库：**
- `/Users/tangshiying/hxkj/dailydawn-web/CLAUDE.md` ← 项目总览
- `/Users/tangshiying/hxkj/dailydawn-web/TODO.md` ← 可勾选待办
- `/Users/tangshiying/hxkj/dailydawn-web/DECISIONS.md` ← 技术选型的 WHY

**下次进来优先读那三份。** 本文件只覆盖内容引擎自己的细节。

---

## 🗂 文件地图

```
dailydawn/
├── CLAUDE.md                      ← 你正在读这个
├── README.md                      对外展示文档（像  那样给访客看）
├── .gitignore
├── .env.example
├── requirements.txt               Python 依赖
│
├── .github/workflows/
│   └── daily-report.yml           每日 UTC 00:00 cron + workflow_dispatch
│
├── prompts/
│   ├── analyze.zh.md              中文 LLM prompt（结构化 JSON 输出约束）
│   └── analyze.en.md              英文 LLM prompt
│
├── scripts/
│   ├── main.py                    ⭐ 入口：asyncio 并发抓取 → 聚合 → LLM × 2 → 保存
│   ├── aggregator.py              跨源去重（canonical URL）+ 分数叠加
│   ├── llm_analyzer.py            OpenAI 兼容 SDK 调度（DeepSeek 默认）
│   ├── renderer.py                把 LLM 返回的 JSON 渲染为人类可读 Markdown
│   │
│   └── fetchers/
│       ├── base.py                BaseFetcher 抽象 + Signal dataclass
│       ├── hackernews.py          HN Algolia API
│       ├── github_trending.py     GitHub trending HTML scraping
│       ├── product_hunt.py        PH GraphQL（需 token）
│       ├── reddit.py              Reddit 公开 JSON（5 个 subreddit）
│       ├── huggingface.py         HF trending models + datasets
│       ├── v2ex.py                V2EX 热榜 API
│       └── juejin.py              掘金热榜（小程序接口）
│
├── zh/                            输出目录（Markdown 按年份分子目录）
│   └── YYYY/YYYY-MM-DD.md
└── en/
    └── YYYY/YYYY-MM-DD.md
```

---

## 🔑 核心设计

### Signal 数据模型（`fetchers/base.py`）
所有 fetcher 输出统一的 `Signal`：
```python
@dataclass
class Signal:
    source: str           # 源名（"HackerNews"）
    title: str
    url: str
    score: float          # 归一化 0-1
    raw_score: int        # 原始分数
    comments: int
    author: str
    summary: str
    tags: list[str]
    extra: dict           # 源特有的额外字段
```

### 抓取策略
- **并发**：`asyncio.gather(*fetchers)` 全部一起跑
- **容错**：`safe_fetch` 包装，单源失败打印错误、返回空列表，不影响整体
- **超时**：每源默认 15 秒
- **User-Agent**：所有请求都带 `dailydawn/0.1`

### 聚合（`aggregator.py`）
- 按 canonical URL（去 scheme/tracking 参数）去重
- 跨源出现的同 URL：score 叠加（`existing.score + new.score * 0.5`）
- 取 Top 60 交给 LLM（平衡 token 消耗和覆盖面）

### LLM 分析（`llm_analyzer.py`）
- 默认 provider：`deepseek`（cheap）
- 可切换：`OPENAI` / `ANTHROPIC`（改 `.env` 里 `LLM_PROVIDER`）
- 强制 JSON 输出：`response_format={"type": "json_object"}`
- 用 `tenacity` 做指数退避重试（3 次）
- 中英文分别跑两次，总成本 ~$0.05/天

### 渲染（`renderer.py`）
把 LLM 的 JSON 渲染成带章节的 Markdown：
- `# 标题`
- `> 一句话总结`
- `## 今日趋势` × 3-5 个
- `## 2 小时构建点子` × 3-5 个
- `## 20 个值得思考的问题`
- `## 数据源` 引用列表

---

## 🚀 本地运行

```bash
cd /Users/tangshiying/hxkj/dailydawn
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 至少填 DEEPSEEK_API_KEY
python scripts/main.py
```

成功后应看到：
```
=== DailyDawn · 2026-XX-XX ===
✓ Fetched 120 signals from 7 sources
✓ Aggregated to 60 unique signals
→ Analyzing [zh]...
✓ [zh] saved to zh/2026/2026-XX-XX.md
→ Analyzing [en]...
✓ [en] saved to en/2026/2026-XX-XX.md
```

---

## 🔧 如何添加一个新数据源

1. 在 `scripts/fetchers/` 新建 `newsource.py`
2. 继承 `BaseFetcher`，实现 `async def fetch(self, client) -> list[Signal]`
3. 在 `scripts/fetchers/__init__.py` 注册到 `ALL_FETCHERS`
4. 如果需要 API key：
   - 在 `.env.example` 加变量
   - 在 `.github/workflows/daily-report.yml` 的 `env:` 段加 secret 引用
5. 本地跑 `python scripts/main.py` 验证
6. Commit + push（GH Actions 会在下次 cron 时用新源）

**评分归一化约定：** 每个源的 `score` 要归一化到 0-1 之间，通常 `raw_score / typical_max` 然后 `min(..., 1.0)`。不同源的 typical_max 不同：HN 500 points、GH 1000 stars、Reddit 2000 upvotes 这类。

---

## 🔧 如何调整 LLM 输出质量

**主要通过修改 prompts。** 不要改代码，改提示词。

- 中文输出：`prompts/analyze.zh.md`
- 英文输出：`prompts/analyze.en.md`

每个 prompt 里已经有：
- Schema 定义
- 硬性要求（趋势 3-5 个、跨源证据、20 问题等）
- 风格约束（不要吹捧、不要 AI 俗套词）

调优思路：
1. 先本地跑一次，看当天输出
2. 不满意的地方：加一条硬性要求到 prompt
3. 重跑验证
4. Commit prompt 改动，下次 GH Actions 会用新版

**常见问题：**
- LLM 输出太水 → 在 prompt 加「不要套话，每个趋势必须引用至少 2 个具体 URL」
- 中文不自然 → 加「口语化，避免学术腔，避免『全面』『深度』『赋能』」
- trend 数量不稳定 → prompt 里用「恰好 N 个」而不是「3-5 个」

---

## ⚠️ 已知坑

### 1. Reddit 公开 JSON 偶发 429
`reddit.py` 现在用公开 JSON（无需 OAuth，简单）。高峰期可能限流。已在 `safe_fetch` 里容错。若连续几天失败率高，切换到 OAuth：
```python
import praw
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT"),
)
```

### 2. 掘金小程序接口可能变更
`api.juejin.cn/content_api/v1/content/article_rank` 是小程序内部接口，官方不保证稳定。失败时 `safe_fetch` 会跳过，但如果连续一周失败，要换用 HTML scraping 或放弃该源。

### 3. GitHub Trending 只能爬 HTML
GitHub 没有 trending 的官方 API。`github_trending.py` 解析的是页面 DOM，结构变化会挂。可选备用：`github-trending-api` 开源项目（GH 上 2k+ 星）。

### 4. 首次跑前确保 .env 至少有 DEEPSEEK_API_KEY
`main.py` 在 `analyze()` 阶段会报 KeyError 如果没这个 env。Product Hunt/Reddit token 缺失不致命（fetcher 内部会自己跳过）。

---

## 📌 关键 env 变量

| 变量 | 必需？ | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | ✅ | 默认 LLM |
| `LLM_PROVIDER` | ⚪ | `deepseek` / `openai` / `anthropic`，默认 deepseek |
| `LLM_MODEL` | ⚪ | 默认 `deepseek-chat` |
| `OPENAI_API_KEY` | ⚪ | 切换 OpenAI 时用 |
| `ANTHROPIC_API_KEY` | ⚪ | 切换 Anthropic 时用 |
| `PRODUCT_HUNT_TOKEN` | ⚪ | 缺失则 PH fetcher 跳过 |
| `REDDIT_CLIENT_ID/SECRET` | ⚪ | 目前 reddit.py 用公开 JSON 不需要，未来切 PRAW 时才要 |
| `GITHUB_TOKEN` | ⚪ | 提升 github.com scraping 限流（可选） |

---

## 🔗 关联文档

- 主上下文：`../dailydawn-web/CLAUDE.md`
- 完整待办：`../dailydawn-web/TODO.md`
- 技术决策：`../dailydawn-web/DECISIONS.md`

---

## 📝 会话交接提示

**下次打开这个仓库时：**
1. 如果是做内容/LLM 相关工作 → 先看本文件再看 `prompts/`
2. 如果是整体规划/部署 → 切到 `../dailydawn-web/` 看主文档
3. 如果要加新数据源 → 看上面「如何添加一个新数据源」
4. 看最近 `zh/` 和 `en/` 下的 markdown 判断内容引擎跑得怎样
