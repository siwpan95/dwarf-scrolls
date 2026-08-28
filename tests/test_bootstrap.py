"""T01 — 引擎引导测试。

验证 ``ensure_engine_loaded()`` 能把**项目内置引擎** ``dwarf_scrolls/alloy``
解析为 ``alloy`` 并注册进 sys.modules；全部关键子模块可导入；同时验证
GAME_ROOT 指向 dwarf_scrolls、引擎物理路径位于 dwarf_scrolls 项目内部（无项目外依赖）。
"""
import sys
from pathlib import Path

from dwarf_scrolls.core.engine_bootstrap import (
    ensure_engine_loaded,
    GAME_ROOT,
)


def test_engine_loaded_into_sys_modules():
    # 第一次调用完成注册
    first = ensure_engine_loaded()
    # 第二次调用幂等，不抛错
    second = ensure_engine_loaded()
    assert "alloy" in sys.modules
    # 引导函数无返回值（约定返回 None）
    assert first is None
    assert second is None


def test_engine_submodules_importable():
    # 核心 ECS 与循环
    from alloy.core import (
        World,
        EventBus,
        EventTypes,
        FixedTimestepLoop,
        Component,
        System,
    )
    # 世界数据
    from alloy.world import Character, MapData, MapGraph, MapNode, Item
    # AI 决策（行为树 / 黑板 / 脑系统）
    from alloy.ai.decision import (
        build_behavior_tree,
        BrainSystem,
        BrainComponent,
        BlackboardComponent,
    )
    # 系统（战斗 / 背包 / 制造 / 存档）
    from alloy.systems import (
        SimpleCombat,
        StackableInventory,
        ItemRegistry,
        CraftingSystem,
        Recipe,
        SaveLoadManager,
    )
    # 渲染
    from alloy.render import ConsoleRenderer

    # 仅确保均为已加载对象即可
    for obj in (
        World, EventBus, EventTypes, FixedTimestepLoop, Component, System,
        Character, MapData, MapGraph, MapNode, Item,
        build_behavior_tree, BrainSystem, BrainComponent, BlackboardComponent,
        SimpleCombat, StackableInventory, ItemRegistry, CraftingSystem,
        Recipe, SaveLoadManager, ConsoleRenderer,
    ):
        assert obj is not None


def test_roots_are_correct():
    # 一仓一目录（2026-08-27 阶段 4 勘查修复）：仓库目录名为 dwarf-scrolls（与
    # gitee 仓名一致），包名 dwarf_scrolls 经仓库根的 dwarf_scrolls.py 桥接。
    assert GAME_ROOT.name == "dwarf-scrolls"
    # 引擎必须解析到 dwarf-scrolls 项目内部的 alloy（无项目外依赖）
    import alloy
    root = Path(alloy.__file__).parent
    assert root.name == "alloy"
    assert (root / "__init__.py").exists()
    assert (root / "core").is_dir()
    # 关键回归：引擎物理路径必须落在 dwarf-scrolls 内部，而非 D:\allin\alloy
    normalized = str(root).replace("\\", "/")
    assert "/dwarf-scrolls/alloy" in normalized, normalized
    assert "/allin/alloy" not in normalized, normalized


def test_engine_path_is_real_alloy_not_example():
    """回归保护：防止「把 example 伪装成引擎」的错误死灰复燃。

    断言 ``ensure_engine_loaded()`` 后 ``alloy.__file__``（反斜杠归一化为
    ``/``）以 ``alloy/__init__.py`` 结尾，且**不包含** ``example``。
    """
    ensure_engine_loaded()
    import alloy
    normalized = alloy.__file__.replace("\\", "/")
    assert normalized.endswith("alloy/__init__.py"), normalized
    assert "example" not in normalized.lower(), normalized
