"""Legends Mode 终端前端 —— 在任意终端中以矮人要塞编年史风格阅读卷轴。

GUI 不可用时（无 tkinter / 无显示器）由 ``main`` 回退到此。渲染复用
``LegendsReader`` 产出的 ``View``：
- 普通视图：把可点击 span 编号，用户输入编号即跳转；
- **地图视图：用引擎 ``ConsoleRenderer`` 渲染 ASCII 网格**（矮人要塞式终端地图），
  再列出省份与图例——地图渲染直接走引擎渲染管线，而非手拼字符串。
"""
from __future__ import annotations

from dwarf_scrolls.core.legends import WorldModel
from dwarf_scrolls.game.legends_view import LegendsReader, collect_links, MAP_GRID
from dwarf_scrolls.game.commands import dispatch
from allin_engine.render.console_renderer import (
    ConsoleRenderer, ANSI_FOREGROUND, ANSI_RESET, ANSI_BOLD, ANSI_DIM, ANSI_UNDERLINE,
)

TITLE_COLOR = "bright_yellow"
LINK_COLOR = "bright_blue"
DIM = "bright_black"


def _c(text: str, color: str) -> str:
    if color in (None, "", "white"):
        return text
    return ConsoleRenderer.colorize(text, color)


def _flush_grid(r: ConsoleRenderer) -> str:
    """从引擎渲染缓冲 ``_buf`` 取出当前帧的 ANSI 字符串（地图网格）。"""
    out = []
    for y in range(r.rows):
        cells = []
        for x in range(r.cols):
            ch, fg, bg, attrs = r._buf[y][x]
            if ch == " ":
                cells.append(" ")
                continue
            seq = ""
            if fg in ANSI_FOREGROUND:
                seq += ANSI_FOREGROUND[fg]
            if "bold" in attrs:
                seq += ANSI_BOLD
            if "dim" in attrs:
                seq += ANSI_DIM
            if "underline" in attrs:
                seq += ANSI_UNDERLINE
            cells.append((seq + ch + ANSI_RESET) if seq else ch)
        out.append("".join(cells).rstrip())
    return "\n".join(out)


def _render_lines(lines, link_no: int) -> int:
    for line in lines:
        parts = []
        for sp in line:
            if sp.is_link():
                link_no += 1
                parts.append(_c(f"[{link_no}]{sp.text}", LINK_COLOR))
            else:
                parts.append(_c(sp.text, sp.color))
        print("".join(parts).rstrip())
    return link_no


def render(reader: LegendsReader) -> None:
    view = reader.view
    print()
    print(_c(view.title, TITLE_COLOR))
    if view.breadcrumb:
        print(_c("  >  ".join(view.breadcrumb), DIM))
    print(_c("─" * 56, DIM))
    link_no = 0
    map_data = getattr(view, "map_data", None)
    if map_data is not None:
        # 地图视图：用引擎 ConsoleRenderer 把 MapData 渲染成 ASCII 网格
        cols = max(len(row) for row in MAP_GRID) + 6
        rows = len(MAP_GRID) + 2
        r = ConsoleRenderer(cols=cols, rows=rows)
        r.draw_grid(map_data, char_color_map=getattr(view, "map_color_map", None))
        print(_flush_grid(r))
        # 跳过手拼的网格行，打印图例 / 省份列表
        start = getattr(view, "map_row_start", 0)
        end = getattr(view, "map_row_end", 0)
        non_grid = view.lines[:start] + view.lines[end:]
        link_no = _render_lines(non_grid, link_no)
    else:
        link_no = _render_lines(view.lines, link_no)
    print()
    print(_c(view.footer, DIM))


def run_cli(world: WorldModel) -> None:
    reader = LegendsReader(world)
    print(_c("上古卷轴 · 泰姆瑞尔编年史", TITLE_COLOR))
    print(_c(f"种子 0x{world.seed & 0xFFFFFFFF:x} · 史事 {len(world.events)} 条 · 人物 {len(world.figures)} 位",
             DIM))
    try:
        while True:
            render(reader)
            try:
                raw = input(_c("卷轴> ", LINK_COLOR)).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            status = dispatch(reader, raw)
            if status == "quit":
                break
            elif status == "invalid":
                print(_c("（无效的输入）", DIM))
    except (EOFError, KeyboardInterrupt):
        pass
    print(_c("愿你的名字也被写进某一卷。", DIM))
