"""游历模式 —— 建立在 alloy 的 ECS + 事件总线 + 固定步长主循环之上。

─────────────────────────────────────────────────
向后兼容重导出层
─────────────────────────────────────────────────
本模块已将实现拆分到以下子模块：
  play_data.py       — 游戏数据与常量（邻接、敌人、魔神分支、隐藏剧情）
  play_components.py — ECS 组件定义
  play_systems.py    — ECS 系统（Travel/Encounter/Combat/Exploration/Faction/Quest/Rest）
  play_engine.py     — PlayEngine 装配器 + PlayState 别名
  play_ui.py         — UI 渲染函数（build_*_view / dispatch_play_action）

所有旧 import 路径（from dwarf_scrolls.game.play_core import ...）保持有效，
本文件仅做重导出。
"""
from dwarf_scrolls.game.legends_view import MAP_CHAR_TO_PROV

# ── 数据 ──
from dwarf_scrolls.game.play_data import (
    ADJACENCY, PROVINCE_COUNT,
    ENEMIES, LOOT_WEAPONS, HEAL_POTION,
    DAEDRIC_PRINCES,
    HIDDEN_LORE, HIDDEN_LORE_READING,
    HIDDEN_CHAPTER, AEDRIC_EPILOGUE, PRINCE_EPILOGUE,
    _branch_key, _lore_reading, _branch_label,
)

# ── 组件 ──
from dwarf_scrolls.game.play_components import (
    Position, Health, Clock, Alignment, Allegiance,
    Gear, Satchel, Pack, Lore, Quests, PlayLog, CommandQueue,
)

# ── 系统 ──
from dwarf_scrolls.game.play_systems import (
    TravelSystem, EncounterSystem, CombatSystem,
    ExplorationSystem, FactionSystem, QuestSystem, RestSystem,
)

# ── 引擎装配器 ──
from dwarf_scrolls.game.play_engine import (
    PlayEngine, PlayState,
)

# ── UI 渲染 ──
from dwarf_scrolls.game.play_ui import (
    build_play_view, build_chronicle_view, build_lore_view, build_quest_view,
    _epilogue_for, dispatch_play_action,
)
