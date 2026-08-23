"""T13 — 存档管理测试。

验证 ``SaveManager`` 能把整座编年史世界保存为 ``scroll_NN.json`` 并完整读回，
列表/自动存档/存在性判断均正常。
"""
import shutil
from pathlib import Path

from dwarf_scrolls.core.world_gen import WorldGenerator
from dwarf_scrolls.core.history_gen import HistoryGenerator
from dwarf_scrolls.core.save_manager import SaveManager


def _world(seed: int = 42):
    w = WorldGenerator(seed=seed).generate()
    HistoryGenerator(seed=seed, world=w).generate()
    return w


def test_save_and_load_roundtrip(tmp_path: Path):
    sm = SaveManager(str(tmp_path))
    assert not sm.has_saves()
    ok = sm.save(_world(42), slot=3)
    assert ok
    assert sm.has_saves()
    assert any(p.name == "scroll_03.json" for p in sm.list_saves())
    w2 = sm.load(3)
    assert w2 is not None
    assert len(w2.events) > 100
    assert len(w2.figures) > 80


def test_auto_save_slot():
    sm = SaveManager(str(tmp_path := Path("/tmp/ds_sm_test")))
    if sm.save_dir.exists():
        shutil.rmtree(sm.save_dir)
    sm = SaveManager(str(tmp_path))
    sm.auto_save(_world(1))
    assert sm.load(99) is not None


def test_load_missing_returns_none(tmp_path: Path):
    sm = SaveManager(str(tmp_path))
    assert sm.load(77) is None
    assert sm.load_latest() is None
