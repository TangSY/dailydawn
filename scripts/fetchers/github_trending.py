from __future__ import annotations

from bs4 import BeautifulSoup
import httpx

from .base import BaseFetcher, Signal


class GitHubTrendingFetcher(BaseFetcher):
    source_name = "github_trending"

    async def fetch(self, client: httpx.AsyncClient) -> list[Signal]:
        url = "https://github.com/trending?since=daily"
        resp = await client.get(
            url,
            timeout=self.timeout,
            headers={"User-Agent": "Mozilla/5.0 dailydawn/0.1"},
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        signals: list[Signal] = []

        for article in soup.select("article.Box-row")[:25]:
            link = article.select_one("h2 a")
            if not link:
                continue
            repo = link.get("href", "").strip("/")
            title = repo
            desc_el = article.select_one("p")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            # 今日 star 数
            stars_today = 0
            today_el = article.find("span", class_="d-inline-block float-sm-right")
            if today_el:
                try:
                    stars_today = int(
                        "".join(c for c in today_el.get_text() if c.isdigit())
                    )
                except ValueError:
                    pass

            lang_el = article.select_one("[itemprop=programmingLanguage]")
            lang = lang_el.get_text(strip=True) if lang_el else ""

            signals.append(
                Signal(
                    source="GitHub Trending",
                    title=title,
                    url=f"https://github.com/{repo}",
                    raw_score=stars_today,
                    score=min(stars_today / 1000.0, 1.0),
                    summary=desc,
                    tags=[lang] if lang else [],
                    # 有意留 None：Trending 页面的"今日"指 star 增量窗口，
                    # repo 本身创建时间可能是几年前（popular 老仓库仍会冒榜）。
                    # 取 pushed_at 需要每个 repo 一次额外 API 调用（25 req/day），
                    # 暂不做，让 prompt 对 GitHub Trending 信号不强制时间描述
                    published_at=None,
                )
            )
        return signals
