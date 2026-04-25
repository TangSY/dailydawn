"""
在 README.md / README.en.md 顶部注入「最近 3 期日报」链接块。

幂等：用 HTML 注释做 sentinel；每次运行覆盖 sentinel 之间的内容。
首次运行（找不到 sentinel）时插入到首个 `---` 横线之前。

用途：把 GitHub 仓库流量反哺到 dailydawn.dev 站点 SEO（双向引流）。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
META_RECENT = REPO_ROOT / "meta" / "recent-taglines.jsonl"
README_ZH = REPO_ROOT / "README.md"
README_EN = REPO_ROOT / "README.en.md"
SITE_URL = "https://dailydawn.dev"

SENTINEL_START = "<!-- LATEST_ISSUES_START -->"
SENTINEL_END = "<!-- LATEST_ISSUES_END -->"


def _load_recent(n: int = 3) -> list[dict]:
    """读 meta/recent-taglines.jsonl 尾部 N 条（最新在前）。"""
    if not META_RECENT.exists():
        return []
    try:
        lines = META_RECENT.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return []
    entries: list[dict] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(entries) >= n:
            break
    return entries


def _build_block(entries: list[dict], lang: str) -> str:
    """生成「最近 3 期」markdown 块。"""
    if not entries:
        return ""
    heading = "## 最近 3 期日报" if lang == "zh" else "## Latest 3 issues"
    suffix_label = "全部归档 →" if lang == "zh" else "Full archive →"
    archive_path = "/archive" if lang == "zh" else "/en/archive"

    lines = [SENTINEL_START, "", heading, ""]
    for e in entries:
        date = e.get("date", "?")
        tagline = e.get(f"tagline_{lang}") or e.get(f"tagline_{'en' if lang == 'zh' else 'zh'}") or ""
        themes = e.get(f"top3_themes_{lang}") or []
        path = f"/zh/{date}" if lang == "zh" else f"/en/{date}"
        url = f"{SITE_URL}{path}"

        # 标题：日期 + topics（首选 ≤3 项）；fallback tagline
        title_parts = themes[:3] if themes else ([tagline] if tagline else [])
        title_suffix = " · " + " / ".join(title_parts) if title_parts else ""
        lines.append(f"- [{date}{title_suffix}]({url})")
        if tagline and themes:
            # tagline 单独成一行（次级描述），避免主标题过长
            lines.append(f"  > {tagline}")

    lines.append("")
    lines.append(f"[{suffix_label}]({SITE_URL}{archive_path})")
    lines.append("")
    lines.append(SENTINEL_END)
    return "\n".join(lines)


def _inject(content: str, block: str) -> str:
    """把 block 注入到 sentinel 之间；首次运行时插到第一个 '---' 之前。"""
    if not block:
        return content

    pattern = re.compile(
        re.escape(SENTINEL_START) + r"[\s\S]*?" + re.escape(SENTINEL_END),
        flags=re.MULTILINE,
    )
    if pattern.search(content):
        return pattern.sub(block, content)

    # 首次注入：找第一个独占一行的 ---
    lines = content.splitlines()
    insert_at = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_at = i
            break
    if insert_at is None:
        # 兜底：追加到末尾
        return content.rstrip() + "\n\n" + block + "\n"

    new_lines = lines[:insert_at] + [block, ""] + lines[insert_at:]
    return "\n".join(new_lines) + ("\n" if content.endswith("\n") else "")


def _update_file(path: Path, lang: str, entries: list[dict]) -> bool:
    if not path.exists():
        print(f"⚠ {path.name} not found, skipping")
        return False
    block = _build_block(entries, lang)
    if not block:
        print(f"⚠ no entries to inject into {path.name}")
        return False
    original = path.read_text(encoding="utf-8")
    updated = _inject(original, block)
    if updated == original:
        print(f"= {path.name} unchanged")
        return False
    path.write_text(updated, encoding="utf-8")
    print(f"✓ {path.name} updated with {len(entries)} latest issues")
    return True


def main() -> int:
    entries = _load_recent(n=3)
    if not entries:
        print("⚠ recent-taglines.jsonl empty or missing; nothing to inject")
        return 0
    _update_file(README_ZH, "zh", entries)
    _update_file(README_EN, "en", entries)
    print(f"  ts: {datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
