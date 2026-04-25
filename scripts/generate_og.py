"""
为今日双语日报生成 OG image（1200x630 PNG），写到 og/{lang}/YYYY/YYYY-MM-DD.png。

为什么在内容引擎侧做：
  - Cloudflare Workers Free plan CPU 上限 10ms，无法跑 satori + resvg
  - GH Actions runner 完全自由：Python + Pillow + Noto CJK 字体（apt installed）
  - 产物 commit 到公开内容仓库，Web 层通过 jsdelivr CDN 引用，全球边缘缓存

字体：Noto Sans CJK SC（OFL 许可），workflow 用 apt install fonts-noto-cjk 安装
      路径：/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc

CLI:
  python scripts/generate_og.py --date 2026-04-25
  python scripts/generate_og.py --default   # 仅生成 og/default.png（站点级默认）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run `pip install Pillow`.", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).parent.parent
OG_DIR = REPO_ROOT / "og"
META_RECENT = REPO_ROOT / "meta" / "recent-taglines.jsonl"

# 字体路径候选（按优先级）
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/PingFang.ttc",  # macOS 本地开发兜底
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Bold.otf",
]
FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]

CANVAS = (1200, 630)
COLOR_BG_TOP = (254, 243, 199)     # #fef3c7
COLOR_BG_BOTTOM = (254, 215, 170)  # #fed7aa
COLOR_BRAND = (31, 41, 55)         # #1f2937
COLOR_ACCENT = (234, 88, 12)       # #ea580c
COLOR_SUN_INNER = (251, 146, 60)   # #fb923c
COLOR_SUBTITLE = (124, 45, 18)     # #7c2d12
COLOR_BODY = (55, 65, 81)          # #374151
COLOR_FAINT = (107, 114, 128)      # #6b7280


def _find_font(candidates: list[str]) -> str | None:
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _load_font(path: str | None, size: int) -> ImageFont.ImageFont:
    """带 ttc 子字库索引兜底。Noto CJK ttc 有多个 face，default 0 通常是 SC。"""
    if not path:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, size)
    except Exception as err:
        print(f"⚠ font load failed for {path}: {err}; falling back to default", file=sys.stderr)
        return ImageFont.load_default()


def _gradient_bg() -> Image.Image:
    """垂直渐变 #fef3c7 → #fed7aa。"""
    img = Image.new("RGB", CANVAS, COLOR_BG_TOP)
    draw = ImageDraw.Draw(img)
    h = CANVAS[1]
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(COLOR_BG_TOP[0] + (COLOR_BG_BOTTOM[0] - COLOR_BG_TOP[0]) * t)
        g = int(COLOR_BG_TOP[1] + (COLOR_BG_BOTTOM[1] - COLOR_BG_TOP[1]) * t)
        b = int(COLOR_BG_TOP[2] + (COLOR_BG_BOTTOM[2] - COLOR_BG_TOP[2]) * t)
        draw.line([(0, y), (CANVAS[0], y)], fill=(r, g, b))
    return img


def _draw_sun(draw: ImageDraw.ImageDraw) -> None:
    cx, cy, r = 180, 200, 80
    for offset, color in [
        (0, COLOR_ACCENT),
        (-12, COLOR_SUN_INNER),
        (-24, (253, 186, 116)),  # #fdba74 outer glow
    ]:
        draw.ellipse(
            (cx - r - offset, cy - r - offset, cx + r + offset, cy + r + offset),
            fill=color if offset == 0 else None,
            outline=color if offset != 0 else None,
            width=4 if offset != 0 else 0,
        )


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont,
                max_width: int) -> list[str]:
    """简易折行：按 grapheme（中文逐字、英文按词）测宽。"""
    if not text:
        return []
    # 中文通过逐字符切；英文 token 按空格
    tokens: list[str] = []
    cur = ""
    for ch in text:
        if ch.isascii() and ch != " ":
            cur += ch
        else:
            if cur:
                tokens.append(cur)
                cur = ""
            if ch == " ":
                if tokens and not tokens[-1].endswith(" "):
                    tokens[-1] += " "
            else:
                tokens.append(ch)
    if cur:
        tokens.append(cur)

    lines: list[str] = []
    line = ""
    for tok in tokens:
        candidate = line + tok
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if (bbox[2] - bbox[0]) > max_width and line:
            lines.append(line)
            line = tok
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def render_og(
    *,
    lang: str,
    date: str,
    tagline: str | None,
    topics: list[str],
    out_path: Path,
) -> None:
    """渲染指定日期的 OG 图。"""
    font_bold_path = _find_font(FONT_CANDIDATES)
    font_reg_path = _find_font(FONT_REGULAR_CANDIDATES)

    font_brand = _load_font(font_bold_path, 84)
    font_subtitle = _load_font(font_reg_path, 30)
    font_date = _load_font(font_bold_path, 56)
    font_topic = _load_font(font_bold_path, 42)
    font_url = _load_font(font_reg_path, 22)

    img = _gradient_bg()
    draw = ImageDraw.Draw(img)

    _draw_sun(draw)

    # 品牌 + 副标题
    draw.text((320, 160), "DailyDawn", font=font_brand, fill=COLOR_BRAND)
    sub = "每日黎明 · 独立开发者的 AI 日报" if lang == "zh" else "Daily AI brief for indie builders"
    draw.text((320, 250), sub, font=font_subtitle, fill=COLOR_SUBTITLE)

    # 日期 + 主题
    draw.text((180, 380), date, font=font_date, fill=COLOR_ACCENT)

    # topics 拼接：取前 3 项，宽度 1000px 内自动折行
    topics_text = " / ".join(topics[:3]) if topics else (tagline or "")
    if topics_text:
        lines = _wrap_lines(draw, topics_text, font_topic, max_width=1020)
        y = 460
        for line in lines[:2]:  # 最多 2 行避免溢出
            draw.text((180, y), line, font=font_topic, fill=COLOR_BRAND)
            y += 56

    # 站点 URL footer
    draw.text((180, 590), "https://dailydawn.dev", font=font_url, fill=COLOR_ACCENT)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)


def render_default(out_path: Path) -> None:
    """站点级默认 OG（首页 / 归档 / 确认页用）。无日期 + 无 topics 的固定卡片。"""
    font_bold_path = _find_font(FONT_CANDIDATES)
    font_reg_path = _find_font(FONT_REGULAR_CANDIDATES)
    font_brand = _load_font(font_bold_path, 96)
    font_subtitle = _load_font(font_reg_path, 36)
    font_tag = _load_font(font_bold_path, 44)
    font_url = _load_font(font_reg_path, 24)

    img = _gradient_bg()
    draw = ImageDraw.Draw(img)
    _draw_sun(draw)

    draw.text((320, 150), "DailyDawn", font=font_brand, fill=COLOR_BRAND)
    draw.text((320, 260), "每日黎明 · Daily AI brief for indie builders",
              font=font_subtitle, fill=COLOR_SUBTITLE)

    draw.text((180, 410), "每天 30 分钟，看清 AI 战场", font=font_tag, fill=COLOR_BRAND)
    draw.text((180, 470), "for builders who ship daily", font=font_tag, fill=COLOR_BODY)

    draw.text((180, 590), "https://dailydawn.dev", font=font_url, fill=COLOR_ACCENT)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)


def _read_today_metadata(date: str) -> dict:
    """从 meta/recent-taglines.jsonl 读今日 entry（main.py 跑完已 append）。"""
    if not META_RECENT.exists():
        return {}
    try:
        for line in reversed(META_RECENT.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("date") == date:
                return entry
    except Exception as err:
        print(f"⚠ recent-taglines read failed: {err}", file=sys.stderr)
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD（默认今天 UTC）")
    parser.add_argument("--default", action="store_true", help="仅生成 og/default.png")
    args = parser.parse_args()

    if args.default:
        out = OG_DIR / "default.png"
        render_default(out)
        print(f"✓ default OG → {out.relative_to(REPO_ROOT)}")
        return 0

    from datetime import datetime, timezone
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    year = date[:4]

    meta = _read_today_metadata(date)
    if not meta:
        print(f"⚠ no metadata for {date} in recent-taglines.jsonl; using empty topics", file=sys.stderr)

    for lang in ("zh", "en"):
        tagline = meta.get(f"tagline_{lang}")
        topics = meta.get(f"top3_themes_{lang}") or []
        out = OG_DIR / lang / year / f"{date}.png"
        render_og(lang=lang, date=date, tagline=tagline, topics=topics, out_path=out)
        print(f"✓ {lang} OG → {out.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
