"""程序内截图自检 —— 把任意一屏（``View``）渲染成 PNG。

对应需求「内部截图检测 / 程序内截图自检」：矮人要塞是暗底亮色的终端画风，
本模块把游戏的文本帧（落地页 / 条目 / ASCII 地图 / 游历模式）原样绘制为图片，
使程序能在无显示器环境下也能「截取自身画面」做校验或存档。

设计要点：
- 不依赖 tkinter（headless 也能跑）；渲染用 PIL。
- **地图视图的字符网格直接来自引擎 ``MapData``**（``View.map_data``），
  阵营着色用 ``View.map_color_map``（引擎渲染器同款 ANSI 色名），
  保证截图与引擎渲染管线一致；
- 字体优先用系统 CJK 等宽感字体，缺失时回退 PIL 默认位图字体。
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from dwarf_scrolls.game.legends_view import View, Span

HEX = {
    "black": "#1a1a1a", "white": "#e8e0d0", "bright_black": "#7a7a7a",
    "red": "#d9534f", "bright_red": "#ff6b6b",
    "green": "#7ec850", "bright_green": "#a6e22e",
    "yellow": "#e5c07b", "bright_yellow": "#ffd866",
    "blue": "#6b9bff", "bright_blue": "#8ab4ff",
    "magenta": "#c792ea", "bright_magenta": "#d9a6ff",
    "cyan": "#5fd7d7", "bright_cyan": "#7fecec",
    "brown": "#b5895a", "dim": "#7a7a7a",
}
_BG = "#0d0d1a"
_TITLE = "bright_yellow"


def _rgb(hexstr: str) -> tuple:
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:/Windows/Fonts/Noto Sans SC (TrueType).otf",
        r"C:/Windows/Fonts/msyh.ttc",
        r"C:/Windows/Fonts/SimHei.ttf",
        r"C:/Windows/Fonts/consola.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _map_to_spans(map_data, color_map) -> list:
    """把引擎 ``MapData`` 网格转成截图用的 Span 行（字符 + 阵营色）。"""
    spans: list = []
    cm = color_map or {}
    for r in range(map_data.rows):
        row = []
        for c in range(map_data.cols):
            ch = map_data.get(c, r)
            if ch in (" ", "#"):
                row.append(Span("  ", "dim"))
            else:
                row.append(Span(ch + " ", cm.get(ch, "white")))
        spans.append(row)
    return spans


def render_view_to_png(view: View, path: str, *, font_size: int = 18,
                       bg: str = _BG, pad: int = 16) -> str:
    """把一屏 ``View`` 渲染为 PNG 并保存到 ``path``，返回路径。"""
    font = _load_font(font_size)
    line_h = int(font_size * 1.55)
    title_h = int(font_size * 1.7) if view.title else 0

    # 地图视图：网格来自引擎 MapData，拼在 lines 之前
    map_data = getattr(view, "map_data", None)
    if map_data is not None:
        cm = getattr(view, "map_color_map", None)
        start = getattr(view, "map_row_start", 0)
        end = getattr(view, "map_row_end", 0)
        render_lines = (
            _map_to_spans(map_data, cm)
            + view.lines[:start]
            + view.lines[end:]
        )
    else:
        render_lines = view.lines

    # 先量宽度
    max_w = pad * 2
    for line in render_lines:
        w = sum(font.getlength(sp.text) for sp in line)
        max_w = max(max_w, int(w) + pad * 2)
    height = pad * 2 + title_h + len(render_lines) * line_h
    if view.footer:
        height += line_h

    img = Image.new("RGB", (max_w, height), _rgb(bg))
    d = ImageDraw.Draw(img)
    y = pad
    if view.title:
        d.text((pad, y), view.title, font=font, fill=_rgb(HEX[_TITLE]))
        y += title_h
    for line in render_lines:
        x = pad
        for sp in line:
            color = _rgb(HEX.get(sp.color or "white", HEX["white"]))
            d.text((x, y), sp.text, font=font, fill=color)
            x += font.getlength(sp.text)
        y += line_h
    if view.footer:
        d.text((pad, y), view.footer, font=font, fill=_rgb(HEX["dim"]))
    img.save(path)
    return path


def capture_reader(reader, path: str, **kw) -> str:
    """对 ``LegendsReader`` 当前屏截图（便捷封装）。"""
    return render_view_to_png(reader.view, path, **kw)
