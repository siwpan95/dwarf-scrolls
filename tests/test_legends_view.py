"""T14 — Legends Mode 视图层测试。

验证 ``LegendsReader`` 的导航栈（落地页 / 分类列表 / 条目页 / 地图）以及
共享视图工具 ``build_entry`` ``collect_links`` 的行为。
"""
from dwarf_scrolls.core.world_gen import WorldGenerator
from dwarf_scrolls.core.history_gen import HistoryGenerator
from dwarf_scrolls.game.legends_view import (
    LegendsReader, build_entry, collect_links,
)


def _world(seed: int = 42):
    w = WorldGenerator(seed=seed).generate()
    HistoryGenerator(seed=seed, world=w).generate()
    return w


def test_initial_view_is_landing():
    r = LegendsReader(_world())
    assert r.view is not None
    assert r.view.lines
    # 落地页带分类与地图链接
    assert collect_links(r.view)


def test_navigate_category_then_entry():
    r = LegendsReader(_world())
    r.navigate(("category", "figure"))
    links = collect_links(r.view)
    assert links
    # 第一条分类链接应指向某个 figure 条目
    kind, eid = links[0]
    r.navigate((kind, eid))
    assert r.view.lines
    assert r.view.title


def test_entry_view_has_content():
    w = _world()
    page = build_entry(w, "figure", w.figures[0].id)
    assert page.lines
    # 交叉引用以超链接形式出现
    has_link = any(getattr(s, "link", None) for ln in page.lines for s in ln)
    assert has_link


def test_map_view():
    r = LegendsReader(_world())
    r.navigate(("map", "root"))
    assert r.view.lines
    # 地图中出现省份瓦片字符
    text = "".join(s.text for ln in r.view.lines for s in ln)
    assert any(t in text for t in "☼YERKCMDB")


def test_back_and_home():
    r = LegendsReader(_world())
    landing_title = r.view.title
    r.navigate(("category", "site"))
    assert r.view.title != landing_title
    r.back()
    assert r.view.title == landing_title
    r.navigate(("category", "faction"))
    r.home()
    assert r.view.title == landing_title
    assert r.stack == []
