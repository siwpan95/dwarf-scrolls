"""游历模式 —— ECS 组件定义。

所有玩家实体组件：位置、生命、时间、阵营、誓言、装备、
卷轴碎片、背包、隐藏剧情、支线任务、日志、命令队列。

引擎接口：仅依赖 ✅ Component（ECS 基类，稳定接口）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# ── 引擎边界：仅用 Component 基类 ──
from alloy.core.ecs import Component


@dataclass
class Position(Component):
    """玩家所在省份。"""
    province: str = "cyrodiil"


@dataclass
class Health(Component):
    """生命值。"""
    value: int = 20
    max_value: int = 30


@dataclass
class Clock(Component):
    """世界时间（天）。"""
    day: int = 1


@dataclass
class Alignment(Component):
    """玩家当前所在地的阵营（位置属性，随移动变化）。"""
    kind: str = "neutral"


@dataclass
class Allegiance(Component):
    """玩家宣誓的势力（圣灵 / 魔神 / 中立），影响可通行性与事件。"""
    kind: str = "none"        # none | aedric | daedric
    prince: str = ""          # daedric 分支：魔神王子 id
    faction_id: str = ""      # 代表派系 id
    standing: int = 0         # 立场强度


@dataclass
class Gear(Component):
    """装备：武器与攻击力。"""
    weapon: str = "旅人短剑"
    attack: int = 3


@dataclass
class Satchel(Component):
    """卷轴碎片囊。"""
    fragments: List[str] = field(default_factory=list)
    chronicle_unlocked: bool = False


@dataclass
class Pack(Component):
    """战利品背包。"""
    items: List[str] = field(default_factory=list)


@dataclass
class Lore(Component):
    """隐藏剧情囊。"""
    hidden: List[str] = field(default_factory=list)
    revealed: bool = False


@dataclass
class Quests(Component):
    """五大魔神王子的独立支线任务进度。

    每个王子对应一个独立支线；``quests[prince]`` 结构：
        {"started": bool, "done": bool, "steps": List[bool], "reward_claimed": bool}
    """
    quests: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class PlayLog(Component):
    """游历日志。"""
    entries: List[str] = field(default_factory=list)


@dataclass
class CommandQueue(Component):
    """待处理的玩家命令。"""
    queue: List[str] = field(default_factory=list)
