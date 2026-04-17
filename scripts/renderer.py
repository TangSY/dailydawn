from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent


def save_report(markdown: str, lang: str, date: str) -> Path:
    """
    保存 markdown 到 {ROOT}/{lang}/{YYYY}/{date}.md

    新流水线下，markdown 由 editor agent 直接产出（不再从 JSON 渲染）。
    """
    year = date[:4]
    dir_path = ROOT / lang / year
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{date}.md"
    file_path.write_text(markdown, encoding="utf-8")
    return file_path
