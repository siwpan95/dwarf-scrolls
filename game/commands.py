"""导航分发 —— CLI 与 GUI 共用的输入解析。

把一行原始输入映射为对 ``LegendsReader`` 的操作：
- 数字  → 跳转到当前视图中第 N 个可点击链接
- b/back → 返回
- h/home → 落地页
- m/map  → 世界地图
- q/quit → 退出
返回 ``"quit"`` 时调用方应结束循环。
"""
from __future__ import annotations

from typing import Tuple

from dwarf_scrolls.game.legends_view import LegendsReader, collect_links


def dispatch(reader: LegendsReader, raw: str) -> str:
    raw = (raw or "").strip().lower()
    if raw in ("q", "quit", "退出"):
        return "quit"
    if raw in ("b", "back", "返回"):
        reader.back()
        return "ok"
    if raw in ("h", "home", "落地页"):
        reader.home()
        return "ok"
    if raw in ("m", "map", "地图"):
        reader.show_map()
        return "ok"
    if raw.isdigit():
        links = collect_links(reader.view)
        idx = int(raw) - 1
        if 0 <= idx < len(links):
            reader.navigate(links[idx])
            return "ok"
        return "invalid"
    if raw == "":
        return "ok"
    return "invalid"
