"""游历模式 —— 引擎装配器。

PlayEngine 用 alloy 的 GameEngine（ECS + EventBus + FixedTimestepLoop）
装配完整的游历模式：创建玩家实体、装配七个系统、接线事件总线、
提供命令 API、支持快照存档。

引擎接口依赖（详见 docs/engine_api.md）：
  - ✅ 稳定: GameEngine, EventTypes, World, Component, System, Entity
  - ⚠️  间接: Styles (gui_base) — 仅 legends_gui 使用
  - ❌  不依赖: 引擎的 audio/ai/fx 等非核心子系统
"""
from __future__ import annotations

import dataclasses
import json
import random
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import dwarf_scrolls.core.engine_bootstrap  # 触发内联引擎优先

# ── 引擎边界（稳定接口） ──
# GameEngine  — 引擎装配器入口，提供 world/bus/loop/advance
# EventTypes  — 事件类型枚举，游戏侧订阅/发射用
# World       — ECS 容器，只使用 get_entity/get_data/set_data/update
from alloy import EventTypes, GameEngine
from alloy.core.ecs import World

from dwarf_scrolls.core.legends import WorldModel, Region
from dwarf_scrolls.game.play_data import ADJACENCY
from dwarf_scrolls.game.play_components import (
    Position, Health, Clock, Alignment, Allegiance,
    Gear, Satchel, Pack, Lore, Quests, PlayLog, CommandQueue,
)
from dwarf_scrolls.game.play_systems import (
    TravelSystem, EncounterSystem, CombatSystem,
    ExplorationSystem, FactionSystem, QuestSystem, RestSystem,
)


class PlayEngine:
    """用 alloy 的 GameEngine 装配游历模式。"""

    def __init__(self, model: WorldModel, seed: int = 0, save_path: Optional[str] = None) -> None:
        self.model = model
        self.seed = seed
        self.rng = random.Random(seed)
        self.dead = False
        self.overlay: Optional[str] = None   # None | "chronicle" | "lore" | "quest"
        self.resumed: bool = False
        self.save_path: Optional[str] = save_path

        # 引擎装配
        self.engine = GameEngine().add_core()
        self.world: World = self.engine.world
        self.bus = self.engine.bus

        # 玩家实体 + 组件
        start = "cyrodiil"
        start_reg = self.model.get("region", start)
        p = self.world.create_entity("player")
        p.add(Position(start))
        p.add(Health(20, 30))
        p.add(Clock(1))
        p.add(Alignment(start_reg.alignment))
        p.add(Allegiance("none", "", 0))
        p.add(Gear("旅人短剑", 3))
        p.add(Satchel([], False))
        p.add(Pack([]))
        p.add(Lore([], False))
        p.add(Quests({}))
        p.add(PlayLog([f"第 1 天：你以{start_reg.name}为起点踏上泰姆瑞尔。"]))
        p.add(CommandQueue([]))

        # 系统装配
        self.travel = TravelSystem(self.model, self.rng, self.bus)
        self.encounter = EncounterSystem(self.model, self.rng, self.bus, self)
        self.encounter.world = self.world
        self.combat = CombatSystem(self.model, self.rng, self.bus, self)
        self.encounter.combat = self.combat
        self.exploration = ExplorationSystem(self.model, self.rng, self.bus)
        self.exploration.world = self.world
        self.exploration.combat = self.combat
        self.travel.world = self.world
        self.travel.faction = FactionSystem(self.model, self.rng, self.bus)
        self.travel.exploration = self.exploration
        self.rest_sys = RestSystem(self.bus, self)
        self.quest_sys = QuestSystem(self.model, self.rng, self.bus, self)
        self.quest_sys.world = self.world
        self.world.add_system(self.travel)
        self.world.add_system(self.rest_sys)
        self.world.add_system(self.exploration)
        self.world.add_system(self.encounter)
        self.world.add_system(self.combat)
        self.world.add_system(self.quest_sys)

        # 事件总线接线
        self.bus.subscribe(EventTypes.PLAYER_MOVED, self.encounter.on_moved)
        self.bus.subscribe(EventTypes.PLAYER_MOVED, self.exploration.on_moved)
        self.bus.subscribe(EventTypes.PLAYER_MOVED, self.quest_sys.on_moved)
        self.bus.subscribe(EventTypes.SHARD_HIDDEN, self.quest_sys.on_lore)
        self.bus.subscribe(EventTypes.PLAYER_DIED, self._on_dead)

    # ── 命令 API ──

    def move_to(self, pid: str) -> bool:
        if self.dead:
            return False
        player = self.world.get_entity("player")
        if pid not in self.adjacent_regions():
            reg = self.model.get("region", pid)
            name = reg.name if reg is not None else pid
            TravelSystem._log(player, f"无法直接抵达{name}。")
            return False
        if not self._faction().passable(player, pid):
            reg = self.model.get("region", pid)
            TravelSystem._log(player, f"{reg.name}被势力封锁，你无法通行。")
            return False
        player.get(CommandQueue).queue.append("move:" + pid)
        self.tick(1.0)
        self._autosave()
        return True

    def rest(self) -> None:
        if self.dead:
            return
        self.world.get_entity("player").get(CommandQueue).queue.append("rest")
        self.tick(1.0)
        self._autosave()

    def inspect(self) -> None:
        if self.dead:
            return
        self.world.get_entity("player").get(CommandQueue).queue.append("inspect")
        self.tick(1.0)
        self._autosave()

    def search(self) -> None:
        if self.dead:
            return
        self.world.get_entity("player").get(CommandQueue).queue.append("search")
        self.tick(1.0)
        self._autosave()

    def vow(self, kind: str, prince: str = "") -> None:
        if self.dead:
            return
        if kind not in ("aedric", "daedric", "none"):
            return
        cmd = "vow:" + kind + (":" + prince if prince else "")
        self.world.get_entity("player").get(CommandQueue).queue.append(cmd)
        self.tick(1.0)
        if kind == "daedric":
            self.quest_sys.start(prince or "azura")
        self._autosave()

    def dispatch(self, action: str) -> None:
        if action == "chronicle":
            self.overlay = "chronicle"
            return
        if action == "chronicle_back":
            self.overlay = None
            return
        if action == "lore":
            self.overlay = "lore"
            return
        if action == "lore_back":
            self.overlay = None
            return
        if action == "quest":
            self.overlay = "quest"
            return
        if action == "quest_back":
            self.overlay = None
            return
        if action.startswith("move:"):
            self.move_to(action.split(":", 1)[1])
        elif action == "rest":
            self.rest()
        elif action == "inspect":
            self.inspect()
        elif action == "search":
            self.search()
        elif action.startswith("vow:"):
            rest = action.split(":", 1)[1]
            if ":" in rest:
                k, pr = rest.split(":", 1)
                self.vow(k, pr)
            else:
                self.vow(rest)

    # ── 时间推进 ──

    def tick(self, dt: float = 1.0) -> None:
        if not self.dead:
            self.world.update(dt)

    def advance(self, real_dt: float) -> None:
        if not self.dead:
            self.engine.advance(real_dt)

    # ── 查询 ──

    def current_region(self) -> Region:
        pid = self.world.get_entity("player").get(Position).province
        return self.model.get("region", pid)

    def adjacent_regions(self) -> List[str]:
        pid = self.world.get_entity("player").get(Position).province
        return sorted(ADJACENCY.get(pid, set()))

    def passable(self, pid: str) -> bool:
        return self._faction().passable(self.world.get_entity("player"), pid)

    def _faction(self) -> FactionSystem:
        return self.travel.faction  # type: ignore[return-value]

    def check_death(self, player) -> None:
        if self.dead:
            return
        if player.get(Health).value <= 0:
            self.bus.emit(EventTypes.PLAYER_DIED,
                          {"province": player.get(Position).province})

    def _on_dead(self, data: Dict[str, Any]) -> None:
        if self.dead:
            return
        self.dead = True
        player = self.world.get_entity("player")
        TravelSystem._log(player, "你倒在了泰姆瑞尔的土地上……（返回落地页重开）")

    # ── 存档（Snapshotable 模式） ──

    def to_snapshot(self) -> Dict[str, Any]:
        p = self.world.get_entity("player")
        comps: Dict[str, Any] = {}
        for C in (Position, Health, Clock, Alignment, Allegiance,
                  Gear, Satchel, Pack, Lore, Quests, PlayLog, CommandQueue):
            comps[C.__name__] = dataclasses.asdict(p.get(C))
        return {
            "version": 1,
            "seed": self.seed,
            "dead": self.dead,
            "overlay": self.overlay,
            "resumed": True,
            "clock_acc": self.world.get_data("__clock_acc", 0.0),
            "rng": self.rng.getstate(),
            "components": comps,
        }

    @classmethod
    def from_snapshot(cls, model: WorldModel, data: Dict[str, Any]) -> "PlayEngine":
        e = cls(model, seed=data.get("seed", 0))
        p = e.world.get_entity("player")
        comps = data.get("components", {})
        for C in (Position, Health, Clock, Alignment, Allegiance,
                  Gear, Satchel, Pack, Lore, Quests, PlayLog, CommandQueue):
            d = comps.get(C.__name__)
            if d:
                p.add(C(**d))
        e.dead = data.get("dead", False)
        e.overlay = data.get("overlay")
        e.resumed = data.get("resumed", True)
        e.world.set_data("__clock_acc", data.get("clock_acc", 0.0))
        try:
            e.rng.setstate(data.get("rng"))
        except Exception:
            # 随机状态格式不兼容——退回当前 rng，不影响续局
            pass
        return e

    def save_to(self, path: str) -> bool:
        Path(path).write_text(
            json.dumps(self.to_snapshot(), ensure_ascii=False), encoding="utf-8")
        return True

    def _autosave(self) -> None:
        if self.save_path:
            try:
                self.save_to(self.save_path)
            except Exception:
                print("[dwarf_scrolls] 自动存档失败：", file=sys.stderr)
                traceback.print_exc()

    @classmethod
    def load_from(cls, model: WorldModel, path: str) -> Optional["PlayEngine"]:
        pp = Path(path)
        if not pp.exists():
            return None
        return cls.from_snapshot(model, json.loads(pp.read_text(encoding="utf-8")))


# 兼容旧 import
PlayState = PlayEngine
