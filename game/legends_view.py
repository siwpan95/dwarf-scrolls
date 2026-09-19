"""Legends Mode 视图层 —— 把 WorldModel 渲染成「可分发的视图」。

设计：``LegendsReader`` 持有世界与导航栈，``View`` 是一组「行（span 列表）」。
每个 ``Span`` 可带 ``link=(kind, eid)``，CLI 与 GUI 共用同一份视图：
- CLI：把带 link 的 span 编号，用户输入编号即跳转；
- GUI：把带 link 的 span 做成可点击的彩色标签。

颜色沿用矮人要塞的 16 色美学：善=青/蓝，恶=红/紫，中立=绿/黄；
可点击的引用统一为亮蓝，标题为亮黄，正文为白，元信息为暗灰。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from dwarf_scrolls.core.legends import WorldModel, entry_page
from dwarf_scrolls.core.engine_bootstrap import ensure_engine_loaded
ensure_engine_loaded()  # 确保 import allin_engine 解析到项目内置引擎地基
from allin_engine.world.map_data import MapData  # 引擎：字符网格地图数据

ALIGN_COLOR = {
    "good": "cyan", "evil": "red", "neutral": "green",
}
LINK_COLOR = "bright_blue"
TITLE_COLOR = "bright_yellow"
SUB_COLOR = "cyan"
WHITE = "white"
DIM = "bright_black"
MAGENTA = "bright_magenta"


@dataclass
class Span:
    text: str
    color: str = WHITE
    link: Optional[Tuple[str, str]] = None

    def is_link(self) -> bool:
        return self.link is not None


@dataclass
class View:
    title: str
    breadcrumb: List[str] = field(default_factory=list)
    lines: List[List[Span]] = field(default_factory=list)
    footer: str = ""
    map_data: Any = None        # 引擎 MapData：泰姆瑞尔 ASCII 网格（地图视图）
    map_rows: int = 0           # 地图视图中网格占的行数
    map_row_start: int = 0      # 网格行在 lines 中的起始索引
    map_row_end: int = 0        # 网格行在 lines 中的结束索引（半开）
    map_color_map: Any = None   # 字符→ANSI 色名，供引擎渲染器按阵营着色

    def add_line(self, *spans: Span) -> None:
        self.lines.append(list(spans))


# ── 构建：落地页 ──
def build_landing(world: WorldModel) -> View:
    v = View(title="上古卷轴 · 泰姆瑞尔编年史")
    v.breadcrumb = ["卷轴庠", "落地页"]
    intro = ("你是一名先祖飞蛾祭司。案上的卷轴无主无次，超越 Aedra 与 Daedra——"
             "它们记载着泰姆瑞尔既往与未然的一切。你将借飞蛾之仪，读尽这部 kalpic 史册。")
    for seg in _wrap(intro, 64):
        v.add_line(Span(seg, DIM))
    v.add_line(Span(""))
    v.add_line(Span("─ 分类 ─", SUB_COLOR))
    for key, label, count in world.landing_categories():
        if key == "map":
            link = ("map", "root")
        else:
            link = ("category", key)
        v.add_line(
            Span(f"  {label}", LINK_COLOR, link=link),
            Span(f"   ({count})", DIM),
        )
    v.footer = "选择分类浏览 · 世界地图 · 退出"
    return v


# ── 构建：分类列表 ──
ENTRY_KIND = {
    "figure": ("历史人物", lambda w, e: w.get("figure", e)),
    "site":   ("地点",     lambda w, e: w.get("site", e)),
    "region": ("省份",     lambda w, e: w.get("region", e)),
    "faction":("派系",     lambda w, e: w.get("faction", e)),
    "artifact":("神器",    lambda w, e: w.get("artifact", e)),
    "event":  ("史事",     lambda w, e: w.get("event", e)),
    "age":    ("时代",     lambda w, e: w.get("age", e)),
}


def build_list(world: WorldModel, cat: str) -> View:
    v = View(title=f"分类 · {_cat_label(cat)}")
    v.breadcrumb = ["卷轴庠", "落地页", _cat_label(cat)]
    items: List[Any] = []
    if cat == "figure":
        items = sorted(world.figures, key=lambda f: f.born_year)
    elif cat == "site":
        items = world.sites
    elif cat == "region":
        items = world.regions
    elif cat == "faction":
        items = world.factions
    elif cat == "artifact":
        items = world.artifacts
    elif cat == "event":
        items = sorted(world.events, key=lambda e: e.year)
    elif cat == "age":
        items = world.ages
    v.add_line(Span(f"共 {len(items)} 条，选择条目查看。", DIM))
    v.add_line(Span(""))
    for it in items:
        name = getattr(it, "name", str(it))
        info = _list_info(world, cat, it)
        v.add_line(
            Span(f"  {name}", LINK_COLOR, link=(cat, it.id)),
            Span(f"   {info}", DIM),
        )
    v.footer = "选择条目查看 · 返回 / 落地页 / 地图"
    return v


def _cat_label(cat: str) -> str:
    return {"figure": "历史人物", "site": "地点", "region": "省份",
            "faction": "派系", "artifact": "神器", "event": "史事",
            "age": "时代"}.get(cat, cat)


def _list_info(world: WorldModel, cat: str, it: Any) -> str:
    if cat == "figure":
        fac = world.get("faction", it.faction_id)
        return f"{world.meta.get('race',{}).get(it.race,it.race)} · {fac.name if fac else ''}"
    if cat == "site":
        region = world.get("region", it.region_id)
        return f"{it.kind} · {region.name if region else ''}"
    if cat == "region":
        return it.biome
    if cat == "faction":
        return f"{it.kind}"
    if cat == "artifact":
        return it.kind
    if cat == "event":
        return world.year_label(it.year)
    if cat == "age":
        return f"{world.year_label(it.start)}—{world.year_label(it.end)}"
    return ""


# ── 构建：条目页 ──
def build_entry(world: WorldModel, kind: str, eid: str) -> View:
    page = entry_page(world, kind, eid)
    v = View(title=page["title"])
    v.breadcrumb = ["卷轴庠", "落地页", page["subtitle"]]
    v.add_line(Span(page["subtitle"], SUB_COLOR))
    v.add_line(Span("─" * 40, DIM))
    for line in page["description"].split("\n"):
        for seg in _wrap(line, 64):
            v.add_line(Span(seg, WHITE))
    if page.get("stats"):
        v.add_line(Span(""))
        v.add_line(Span("─ 概要 ─", SUB_COLOR))
        for k, val in page["stats"]:
            v.add_line(Span(f"  {k}: ", DIM), Span(str(val), WHITE))
    if page.get("events"):
        v.add_line(Span(""))
        v.add_line(Span(f"─ 相关史事（{len(page['events'])}）─", SUB_COLOR))
        for txt in page["events"]:
            for seg in _wrap("• " + txt, 62):
                v.add_line(Span("  " + seg, WHITE))
    if page.get("related"):
        v.add_line(Span(""))
        v.add_line(Span("─ 交叉引用 ─", MAGENTA))
        for (rk, reid, rlabel) in page["related"]:
            v.add_line(Span(f"  ▸ {rlabel}", LINK_COLOR, link=(rk, reid)))
    v.footer = "查看交叉引用 · 返回 / 落地页 / 地图"
    return v


# ── 构建：世界地图 ──
MAP_GRID = [
    "  ☼ Y E",
    "  ☼ Y E",
    "R K C M B",
    "R K C M B",
    "  H   ",
]
MAP_CHAR_TO_PROV = {
    "☼": "summerset", "Y": "valenwood", "E": "elsweyr",
    "R": "high_rock", "K": "skyrim", "C": "cyrodiil",
    "M": "morrowind", "B": "black_marsh", "H": "hammerfell",
}


def build_map(world: WorldModel) -> View:
    v = View(title="泰姆瑞尔 · 历史地图")
    v.breadcrumb = ["卷轴庠", "世界地图"]
    v.add_line(Span("阵营属性着色：", DIM),
               Span("善", "cyan"), Span(" / ", DIM),
               Span("恶", "red"), Span(" / ", DIM),
               Span("中立", "green"))
    v.add_line(Span(""))
    v.map_row_start = len(v.lines)
    for row in MAP_GRID:
        spans: List[Span] = []
        for ch in row:
            pid = MAP_CHAR_TO_PROV.get(ch)
            if pid is None:
                spans.append(Span(ch + " ", DIM))
            else:
                prov = world.get("region", pid)
                color = ALIGN_COLOR.get(prov.alignment, "white") if prov else "white"
                spans.append(Span(ch + " ", color, link=("region", pid)))
        v.add_line(*spans)
    v.map_row_end = len(v.lines)
    v.add_line(Span(""))
    v.add_line(Span("─ 省份 ─", SUB_COLOR))
    for p in world.regions:
        color = ALIGN_COLOR.get(p.alignment, "white")
        v.add_line(Span(f"  {p.tile} {p.name}", color, link=("region", p.id)),
                   Span(f"   {p.en} · {p.biome}", DIM))
    v.map_data = world_map_data(world)
    v.map_rows = len(MAP_GRID)
    v.map_color_map = map_char_color_map(world)
    v.footer = "选择省份查看 · 返回 / 落地页"
    return v


def world_map_data(world: WorldModel) -> "MapData":
    """用引擎 ``MapData`` 持有泰姆瑞尔 ASCII 网格（矮人要塞式字符地图）。

    用 ``from_string`` 让各行列等宽（短行以空格补齐），以便引擎
    ``ConsoleRenderer.draw_grid`` 按 (col, row) 取字符时不越界。
    """
    return MapData.from_string("\n".join(MAP_GRID))


def map_char_color_map(world: WorldModel) -> Dict[str, str]:
    """省份 tile 字符 → 阵营 ANSI 色名（good=青 / evil=红 / neutral=绿）。"""
    cmap: Dict[str, str] = {}
    for p in world.regions:
        cmap[p.tile] = ALIGN_COLOR.get(p.alignment, "white")
    return cmap


# ── 读者（导航栈） ──
class LegendsReader:
    def __init__(self, world: WorldModel) -> None:
        self.world = world
        self.stack: List[View] = []
        self.view: View = build_landing(world)

    def navigate(self, link: Tuple[str, str]) -> None:
        kind, eid = link
        if kind == "map":
            self.stack.append(self.view)
            self.view = build_map(self.world)
        elif kind == "category":
            self.stack.append(self.view)
            self.view = build_list(self.world, eid)
        else:
            self.stack.append(self.view)
            self.view = build_entry(self.world, kind, eid)

    def back(self) -> None:
        if self.stack:
            self.view = self.stack.pop()

    def home(self) -> None:
        self.stack = []
        self.view = build_landing(self.world)

    def show_map(self) -> None:
        self.stack.append(self.view)
        self.view = build_map(self.world)


# ── 工具 ──
def _wrap(text: str, width: int) -> List[str]:
    if not text:
        return [""]
    out: List[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if len(cur) >= width:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def collect_links(view: View) -> List[Tuple[str, str]]:
    """按渲染顺序收集当前视图中所有可点击链接，供编号/点击使用。"""
    links: List[Tuple[str, str]] = []
    for line in view.lines:
        for sp in line:
            if sp.is_link():
                links.append(sp.link)
    return links
