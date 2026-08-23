"""T10 — 世界生成测试。

验证 ``WorldGenerator`` 能产出结构完整、随种子确定的泰姆瑞尔世界骨架
（省份 / 地点 / 派系 / 人物 / 神器 / 时代），且不同种子产生不同结果。
"""
from dwarf_scrolls.core.world_gen import WorldGenerator


def _build(seed: int):
    return WorldGenerator(seed=seed).generate()


def test_world_has_expected_counts():
    w = _build(42)
    # 9 个泰姆瑞尔省份（来自 content/provinces.json）
    assert len(w.regions) == 9, w.regions
    # 至少应有若干地点、派系、人物、神器、时代
    assert len(w.sites) >= 20
    assert len(w.factions) >= 10
    assert len(w.figures) >= 80
    assert len(w.artifacts) >= 8
    assert len(w.eras) >= 4


def test_world_meta_populated():
    w = _build(42)
    # meta 表应携带种族 / 迪德拉 / 神族 名称表，供历史生成取用
    assert "race" in w.meta and w.meta["race"]
    assert "daedra" in w.meta and w.meta["daedra"]
    assert "divine" in w.meta and w.meta["divine"]


def test_deterministic_per_seed():
    a = _build(7)
    b = _build(7)
    assert len(a.figures) == len(b.figures)
    assert a.figures[0].name == b.figures[0].name
    assert len(a.sites) == len(b.sites)


def test_different_seeds_differ():
    a = _build(1)
    b = _build(2)
    # 不同种子应产生不同的人物名单（几乎必然）
    names_a = {f.name for f in a.figures}
    names_b = {f.name for f in b.figures}
    assert names_a != names_b


def test_indexes_resolve():
    w = _build(42)
    w.build_indexes()
    f0 = w.figures[0]
    assert w.get("figure", f0.id) is f0
    # 不存在的 id 返回 None
    assert w.get("figure", "nope") is None
