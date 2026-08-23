"""T17 — 截图自检能力测试。

验证 ``render_view_to_png`` 能把 ``View`` 渲染成 PNG 文件，
这是「程序内截图自检」的基础能力。
"""
from pathlib import Path

from dwarf_scrolls.game.legends_view import View, Span
from dwarf_scrolls.game.screenshot import render_view_to_png


def test_render_view_to_png(tmp_path: Path):
    v = View(title="Test Screen")
    v.add_line(Span("Hello ", "white"), Span("World", "bright_blue"))
    v.footer = "footer"
    out = tmp_path / "test.png"
    render_view_to_png(v, str(out), font_size=14)
    assert out.exists()
    assert out.stat().st_size > 0
