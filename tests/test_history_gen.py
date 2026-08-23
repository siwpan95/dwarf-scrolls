"""T11 — 程序化历史测试。

验证 ``HistoryGenerator`` 在 ``WorldGenerator`` 骨架上叠加史事与时代，且
交叉引用无断链、事件类型分布合理、可重复。
"""
from dwarf_scrolls.core.world_gen import WorldGenerator
from dwarf_scrolls.core.history_gen import HistoryGenerator


def _world(seed: int):
    w = WorldGenerator(seed=seed).generate()
    HistoryGenerator(seed=seed, world=w).generate()
    return w


LINKABLE = {"figure", "site", "region", "faction", "artifact", "age"}


def test_history_adds_events_and_ages():
    w = _world(42)
    assert len(w.events) > 100
    assert len(w.ages) >= 3


def test_no_broken_refs():
    w = _world(42)
    broken = 0
    for ev in w.events:
        for rk, rid in ev.refs.items():
            if rk in LINKABLE and w.get(rk, rid) is None:
                broken += 1
    assert broken == 0, f"{broken} broken refs"


def test_event_types_distributed():
    w = _world(42)
    types = {}
    for ev in w.events:
        types[ev.type] = types.get(ev.type, 0) + 1
    # 应有多种事件类型（出生/死亡/战争/龙战/迪德拉入侵/龙破/塔/史事…）
    assert len(types) >= 6
    # 战争类事件应存在
    assert any(t in types for t in ("war_start", "war_end", "battle", "dragon_war"))


def test_deterministic():
    a = _world(7)
    b = _world(7)
    assert len(a.events) == len(b.events)
    assert a.events[0].type == b.events[0].type


def test_year_label_and_era():
    w = _world(42)
    # 元年之后的年份应有标记
    lab = w.year_label(152)
    assert lab
    # 能查出某年份所属时代
    era = w.era_for_year(200)
    assert era is not None
