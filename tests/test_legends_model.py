"""T12 — 编年史数据模型与叙事测试。

验证 ``WorldModel`` 的序列化往返、查询接口、年份/时代换算，以及
``entry_page`` 能产出各类型条目的叙事字典。
"""
from dwarf_scrolls.core.world_gen import WorldGenerator
from dwarf_scrolls.core.history_gen import HistoryGenerator
from dwarf_scrolls.core.legends import WorldModel, entry_page


def _world(seed: int = 42):
    w = WorldGenerator(seed=seed).generate()
    HistoryGenerator(seed=seed, world=w).generate()
    return w


def test_roundtrip_json():
    w = _world(42)
    s = w.to_json()
    w2 = WorldModel.from_json(s)
    assert len(w2.events) == len(w.events)
    assert len(w2.figures) == len(w.figures)
    assert len(w2.sites) == len(w.sites)
    assert len(w2.regions) == len(w.regions)


def test_get_and_index():
    w = _world(42)
    w.build_indexes()
    for coll, kind in [(w.figures, "figure"), (w.sites, "site"),
                       (w.regions, "region"), (w.factions, "faction"),
                       (w.artifacts, "artifact"), (w.ages, "age")]:
        e = coll[0]
        assert w.get(kind, e.id) is e


def test_entry_page_keys():
    w = _world(42)
    for kind, coll in [("figure", w.figures), ("site", w.sites),
                       ("region", w.regions), ("faction", w.factions),
                       ("artifact", w.artifacts), ("age", w.ages)]:
        page = entry_page(w, kind, coll[0].id)
        assert isinstance(page, dict)
        assert page["title"] and page["description"]
        # 落地页反查入口也在 narratives 中
        assert "subtitle" in page


def test_landing_categories():
    w = _world(42)
    cats = w.landing_categories()
    keys = {c[0] for c in cats}
    assert {"figure", "site", "region", "faction", "artifact", "event", "age"} <= keys
