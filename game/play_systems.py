"""游历模式 —— ECS 系统。

七个游戏系统，建立在 alloy 的 ECS + EventBus 之上：
- TravelSystem: 处理玩家命令（移动/休整/探索/宣誓）
- EncounterSystem: 按省份阵营与玩家誓言分流事件
- CombatSystem: 多回合战斗结算
- ExplorationSystem: 碎片收集与隐秘发掘
- FactionSystem: 誓言管理与势力封锁
- QuestSystem: 魔神王子支线任务
- RestSystem: 时间流逝与微量回血

引擎接口：✅ EventTypes, System, World（均为稳定接口）。
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# ── 引擎边界（稳定接口） ──
# EventTypes — 事件类型，游戏侧 emit/subscribe
# System     — ECS 系统基类，只覆写 update()
# World      — ECS 容器，只使用 get_entity/get_data/set_data
from alloy import EventTypes
from alloy.core.ecs import System, World

from dwarf_scrolls.core.legends import WorldModel
from dwarf_scrolls.game.play_data import (
    _ALIGN_CN, _ALLEGIANCE_CN,
    ENEMIES, LOOT_WEAPONS, HEAL_POTION,
    DAEDRIC_PRINCES, HIDDEN_LORE, HIDDEN_CHAPTER,
    PROVINCE_COUNT, RANDOM_ENCOUNTERS,
)
from dwarf_scrolls.game.play_components import (
    Position, Health, Clock, Alignment, Allegiance,
    Gear, Satchel, Pack, Lore, Quests, PlayLog, CommandQueue,
)

if TYPE_CHECKING:
    from dwarf_scrolls.game.play_engine import PlayEngine


# ─────────────────────────────────────────────
# TravelSystem
# ─────────────────────────────────────────────

class TravelSystem(System):
    """处理玩家命令队列：移动 / 休整 / 探索 / 宣誓 / 查看。高优先级。"""

    priority = 10

    def __init__(self, model: WorldModel, rng: random.Random, bus) -> None:
        self.model = model
        self.rng = rng
        self.bus = bus
        self.world: Optional[World] = None
        self.faction: Optional["FactionSystem"] = None
        self.exploration: Optional["ExplorationSystem"] = None

    def update(self, world: World, dt: float) -> None:
        player = world.get_entity("player")
        if player is None:
            return
        cq = player.get(CommandQueue)
        if cq is None or not cq.queue:
            return
        cmd = cq.queue.pop(0)
        if cmd.startswith("move:"):
            self._move(world, player, cmd.split(":", 1)[1])
        elif cmd == "rest":
            self._rest(world, player)
        elif cmd == "inspect":
            self._inspect(world, player)
        elif cmd == "search":
            if self.exploration is not None:
                self.exploration.search(player)
        elif cmd.startswith("vow:"):
            if self.faction is not None:
                rest = cmd.split(":", 1)[1]
                if ":" in rest:
                    k, pr = rest.split(":", 1)
                    self.faction.vow(player, k, pr)
                else:
                    self.faction.vow(player, rest)

    def _move(self, world: World, player, pid: str) -> None:
        pos = player.get(Position)
        reg = self.model.get("region", pid)
        pos.province = pid
        player.get(Alignment).kind = reg.alignment
        self.bus.emit(EventTypes.PLAYER_MOVED,
                      {"from": pos.province, "to": pid, "alignment": reg.alignment})

    def _rest(self, world: World, player) -> None:
        hp = player.get(Health)
        heal = self.rng.randint(3, 6)
        hp.value = min(hp.max_value, hp.value + heal)
        reg = self.model.get("region", player.get(Position).province)
        self._log(player, f"在{reg.name}休整，恢复{heal}点。")

    def _inspect(self, world: World, player) -> None:
        reg = self.model.get("region", player.get(Position).province)
        self._log(player, f"{reg.name}：{reg.biome}，阵营{_ALIGN_CN.get(reg.alignment, reg.alignment)}。")

    @staticmethod
    def _log(player, msg: str) -> None:
        player.get(PlayLog).entries.append(msg)


# ─────────────────────────────────────────────
# EncounterSystem
# ─────────────────────────────────────────────

class EncounterSystem(System):
    """监听 PLAYER_MOVED：按目标省阵营 + 玩家誓言分流遇敌 / 补给 / 敌对事件。"""

    priority = 100

    def __init__(self, model: WorldModel, rng: random.Random, bus, engine: "PlayEngine") -> None:
        self.model = model
        self.rng = rng
        self.bus = bus
        self.engine = engine
        self.world: Optional[World] = None
        self.combat: Optional["CombatSystem"] = None

    def update(self, world: World, dt: float) -> None:
        return

    def on_moved(self, data: Dict[str, Any]) -> None:
        if self.world is None or self.combat is None:
            return
        player = self.world.get_entity("player")
        if player is None:
            return
        hp = player.get(Health)
        to = data.get("to")
        align = data.get("alignment")
        reg = self.model.get("region", to)
        al = player.get(Allegiance)
        if align == "evil":
            if al.kind == "daedric":
                drop = self.combat.maybe_loot(player, bonus=True)
                self._log(player, f"魔神之力庇佑，你视{reg.name}的 hostile 于无物，搜得{drop}。")
            else:
                self.bus.emit(EventTypes.MOB_SPAWNED, {"province": to})
                self.combat.resolve(player, to)
        elif align == "good":
            if al.kind == "daedric":
                dmg = self.rng.randint(2, 4)
                hp.value = max(0, hp.value - dmg)
                self._log(player, f"{reg.name}的圣灵净域排斥你，受创{dmg}点。")
                self.engine.check_death(player)
            else:
                heal = self.rng.randint(1, 3) + (2 if al.kind == "aedric" else 0)
                hp.value = min(hp.max_value, hp.value + heal)
                self._log(player, f"抵达{reg.name}，盟友提供补给，恢复{heal}点。")
        else:
            self._log(player, f"抵达{reg.name}。")
            # 中立省随机遭遇（30% 概率）
            if self.rng.random() < 0.3:
                self._random_encounter(player, reg)
        if hp.value <= 0:
            self.engine.check_death(player)

    def _log(self, player, msg: str) -> None:
        TravelSystem._log(player, msg)

    def _random_encounter(self, player, reg) -> None:
        """中立省随机遭遇（商队/朝圣者/自然灾害/古遗迹）。"""
        encounter = self.rng.choice(list(RANDOM_ENCOUNTERS.values()))
        hp = player.get(Health)
        text = self.rng.choice(encounter["texts"])
        if encounter["kind"] == "heal":
            heal = self.rng.randint(2, 5)
            hp.value = min(hp.max_value, hp.value + heal)
            self._log(player, f"{reg.name}，{text}，恢复{heal}点。")
        elif encounter["kind"] == "damage":
            dmg = encounter["hp"]
            hp.value = max(0, hp.value - dmg)
            self._log(player, f"{reg.name}，{text}，受创{dmg}点。")
        elif encounter["kind"] == "loot":
            heal = self.rng.randint(1, 3)
            hp.value = min(hp.max_value, hp.value + heal)
            self._log(player, f"{reg.name}，{text}，恢复{heal}点。")


# ─────────────────────────────────────────────
# CombatSystem
# ─────────────────────────────────────────────

class CombatSystem(System):
    """战斗结算（监听 PLAYER_MOVED 时由 EncounterSystem 调用）。"""

    priority = 95

    def __init__(self, model: WorldModel, rng: random.Random, bus, engine: "PlayEngine") -> None:
        self.model = model
        self.rng = rng
        self.bus = bus
        self.engine = engine

    def update(self, world: World, dt: float) -> None:
        return

    def _prince_mods(self, player) -> Dict[str, Any]:
        al = player.get(Allegiance)
        if al.kind != "daedric" or not al.prince:
            return {"atk_mod": 0, "evil_atk_mod": 0, "enemy_atk_mod": 0,
                    "loot_chance": 0.6, "dominate": 0.0, "chaos": False}
        pr = DAEDRIC_PRINCES.get(al.prince, DAEDRIC_PRINCES["azura"])
        return {"atk_mod": pr["atk_mod"], "evil_atk_mod": pr["evil_atk_mod"],
                "enemy_atk_mod": pr["enemy_atk_mod"], "loot_chance": pr["loot_chance"],
                "dominate": pr["dominate"], "chaos": pr["chaos"]}

    def resolve(self, player, pid: str) -> bool:
        """与 pid 省的敌人作战。返回 True=胜利，False=阵亡。"""
        enemy_pool = ENEMIES.get(pid, [{"name": "游荡的 hostile", "hp": 8, "atk": 2}])
        enemy = self.rng.choice(enemy_pool)
        hp = player.get(Health)
        gear = player.get(Gear)
        reg = self.model.get("region", pid)
        mods = self._prince_mods(player)
        atk_mod = mods["atk_mod"] + (mods["evil_atk_mod"] if reg.alignment == "evil" else 0)
        if mods["chaos"]:
            atk_mod += self.rng.choice([-1, 0, 1])
        loot_chance = max(0.1, min(0.95,
                          mods["loot_chance"] + (self.rng.choice([-0.1, 0, 0.1]) if mods["chaos"] else 0)))
        player_atk = gear.attack + atk_mod
        enemy_atk = max(1, enemy["atk"] + mods["enemy_atk_mod"])
        self.bus.emit(EventTypes.COMBAT_START,
                      {"province": pid, "enemy": enemy["name"], "enemy_hp": enemy["hp"]})
        if mods["dominate"] and self.rng.random() < mods["dominate"]:
            drop = self._roll_loot_chance(player, loot_chance)
            self.bus.emit(EventTypes.MOB_DEFEATED,
                          {"province": pid, "enemy": enemy["name"], "drop": drop})
            self._log(player, f"你以支配之力碾碎了{enemy['name']}，夺得{drop['label']}。")
            return True
        ehp = enemy["hp"]
        rounds = 0
        while ehp > 0 and hp.value > 0 and rounds < 12:
            ehp -= player_atk
            rounds += 1
            if ehp <= 0:
                break
            dmg = enemy_atk
            hp.value = max(0, hp.value - dmg)
        if ehp <= 0:
            drop = self._roll_loot_chance(player, loot_chance)
            self.bus.emit(EventTypes.MOB_DEFEATED,
                          {"province": pid, "enemy": enemy["name"], "drop": drop})
            self._log(player, f"你斩杀{enemy['name']}（{rounds}回合），夺得{drop['label']}。")
            return True
        self.bus.emit(EventTypes.PLAYER_DIED, {"province": pid, "by": enemy["name"]})
        return False

    def maybe_loot(self, player, bonus: bool = False) -> str:
        drop = self._roll_loot(player)
        return drop["label"]

    def _roll_loot_chance(self, player, loot_chance: float) -> Dict[str, Any]:
        if self.rng.random() < loot_chance:
            name, atk = self.rng.choice(LOOT_WEAPONS)
            player.get(Gear).attack += atk
            player.get(Gear).weapon = name
            player.get(Pack).items.append(name)
            return {"kind": "weapon", "label": f"{name}(攻击+{atk})", "attack": atk}
        heal = HEAL_POTION[1]
        hp = player.get(Health)
        hp.value = min(hp.max_value, hp.value + heal)
        player.get(Pack).items.append(HEAL_POTION[0])
        return {"kind": "heal", "label": f"{HEAL_POTION[0]}(+{heal})", "heal": heal}

    def _roll_loot(self, player) -> Dict[str, Any]:
        return self._roll_loot_chance(player, self._prince_mods(player)["loot_chance"])

    def _log(self, player, msg: str) -> None:
        TravelSystem._log(player, msg)


# ─────────────────────────────────────────────
# ExplorationSystem
# ─────────────────────────────────────────────

class ExplorationSystem(System):
    """探索 / 碎片收集（监听 PLAYER_MOVED + 处理 search 命令）。"""

    priority = 80

    def __init__(self, model: WorldModel, rng: random.Random, bus) -> None:
        self.model = model
        self.rng = rng
        self.bus = bus
        self.world: Optional[World] = None
        self.combat: Optional["CombatSystem"] = None

    def update(self, world: World, dt: float) -> None:
        return

    def on_moved(self, data: Dict[str, Any]) -> None:
        if self.world is None:
            return
        player = self.world.get_entity("player")
        if player is None:
            return
        to = data.get("to")
        sat = player.get(Satchel)
        if to not in sat.fragments:
            sat.fragments.append(to)
            reg = self.model.get("region", to)
            self._log(player, f"在{reg.name}寻得卷轴碎片（{len(sat.fragments)}/{PROVINCE_COUNT}）。")
            self.bus.emit(EventTypes.SHARD_FOUND, {"province": to, "count": len(sat.fragments)})
            if len(sat.fragments) == PROVINCE_COUNT and not sat.chronicle_unlocked:
                sat.chronicle_unlocked = True
                self._log(player, "九省卷轴碎片已聚齐——kalpic 编年史全卷复原！")

    def search(self, player) -> None:
        found = self.discover_hidden(player)
        if self.combat is None:
            if not found:
                self._log(player, "你仔细搜索四周，未见异样。")
            return
        if found:
            return
        if self.rng.random() < 0.5:
            drop = self.combat._roll_loot(player)
            self._log(player, f"探索之中，你搜得战利品：{drop['label']}。")
        else:
            self._log(player, "你仔细搜索四周，只听见风声。")

    def discover_hidden(self, player) -> bool:
        """发掘当前省份的 kalpic 隐秘卷轴。首次搜得返回 True。"""
        prov = player.get(Position).province
        lore = player.get(Lore)
        if prov in lore.hidden:
            return False
        lore.hidden.append(prov)
        snippet = HIDDEN_LORE.get(prov, "你在此地寻得一段未署名的 kalpic 隐秘。")
        self._log(player, f"你发掘出隐藏卷轴：{snippet}")
        self.bus.emit(EventTypes.SHARD_HIDDEN, {"province": prov, "count": len(lore.hidden)})
        if len(lore.hidden) == PROVINCE_COUNT and not lore.revealed:
            lore.revealed = True
            self._log(player, HIDDEN_CHAPTER)
            self._log(player, "—— kalpic 隐藏剧情已揭示：飞蛾祭司的真相。")
        return True

    def _log(self, player, msg: str) -> None:
        TravelSystem._log(player, msg)


# ─────────────────────────────────────────────
# FactionSystem
# ─────────────────────────────────────────────

class FactionSystem(System):
    """誓言 / 势力系统（处理 vow 命令；提供可通行性查询）。"""

    priority = 70

    def __init__(self, model: WorldModel, rng: random.Random, bus) -> None:
        self.model = model
        self.rng = rng
        self.bus = bus

    def update(self, world: World, dt: float) -> None:
        return

    def vow(self, player, kind: str, prince: str = "") -> None:
        al = player.get(Allegiance)
        if kind == "aedric":
            al.kind = "aedric"
            al.prince = ""
            al.faction_id = "empire"
            al.standing += 1
            self._log(player, "你向圣灵（Aedra）宣誓：净化魔神侵蚀之地，守护泰姆瑞尔的光。")
        elif kind == "daedric":
            prince = prince or "azura"
            pr = DAEDRIC_PRINCES.get(prince, DAEDRIC_PRINCES["azura"])
            al.kind = "daedric"
            al.prince = prince
            al.faction_id = f"cult_{prince}"
            al.standing += 1
            self._log(player, f"你向魔神 {pr['name']}（{pr['title']}）献誓：{pr['blurb']}。")
        else:
            al.kind = "none"
            al.prince = ""
            al.faction_id = ""
            self._log(player, "你收回誓言，重归中立游历。")

    def passable(self, player, pid: str) -> bool:
        reg = self.model.get("region", pid)
        if reg is None:
            return True
        al = player.get(Allegiance)
        if al.kind == "aedric" and reg.alignment == "evil":
            return False
        if al.kind == "daedric" and reg.alignment == "good":
            return False
        return True

    def _log(self, player, msg: str) -> None:
        TravelSystem._log(player, msg)


# ─────────────────────────────────────────────
# QuestSystem
# ─────────────────────────────────────────────

class QuestSystem(System):
    """魔神王子独立支线任务系统（事件驱动）。"""

    priority = 55

    def __init__(self, model: WorldModel, rng: random.Random, bus, engine: "PlayEngine") -> None:
        self.model = model
        self.rng = rng
        self.bus = bus
        self.engine = engine
        self.world: Optional[World] = None

    def update(self, world: World, dt: float) -> None:
        return

    def start(self, prince: str) -> None:
        """开启（或保持）某王子的支线；首次开启时据当前状态回填已满足的步骤。"""
        if prince not in DAEDRIC_PRINCES:
            return
        p = self.world.get_entity("player") if self.world is not None else None
        if p is None:
            return
        quests = p.get(Quests).quests
        if prince not in quests:
            quests[prince] = {"started": True, "done": False,
                               "steps": [False] * len(DAEDRIC_PRINCES[prince]["quest"]["steps"]),
                               "reward_claimed": False}
        q = DAEDRIC_PRINCES[prince]["quest"]
        st = quests[prince]
        cur = p.get(Position).province
        hidden = set(p.get(Lore).hidden)
        for i, step in enumerate(q["steps"]):
            if step["prov"] == cur or step["prov"] in hidden:
                st["steps"][i] = True
        self._check_complete(prince)

    def on_moved(self, data: Dict[str, Any]) -> None:
        prince = self._active_prince()
        if prince is None:
            return
        to = data.get("to")
        st = self.world.get_entity("player").get(Quests).quests.get(prince)
        if st is None or st.get("done"):
            return
        q = DAEDRIC_PRINCES[prince]["quest"]
        for i, step in enumerate(q["steps"]):
            if step["type"] == "visit" and step["prov"] == to:
                st["steps"][i] = True
        self._check_complete(prince)

    def on_lore(self, data: Dict[str, Any]) -> None:
        prince = self._active_prince()
        if prince is None:
            return
        prov = data.get("province")
        st = self.world.get_entity("player").get(Quests).quests.get(prince)
        if st is None or st.get("done"):
            return
        q = DAEDRIC_PRINCES[prince]["quest"]
        for i, step in enumerate(q["steps"]):
            if step["type"] == "lore" and step["prov"] == prov:
                st["steps"][i] = True
        self._check_complete(prince)

    def _active_prince(self) -> Optional[str]:
        if self.world is None:
            return None
        al = self.world.get_entity("player").get(Allegiance)
        if al.kind == "daedric" and al.prince:
            return al.prince
        return None

    def _check_complete(self, prince: str) -> None:
        st = self.world.get_entity("player").get(Quests).quests.get(prince)
        if st is None or st.get("done"):
            return
        if all(st["steps"]):
            self._claim_reward(prince)

    def _claim_reward(self, prince: str) -> None:
        p = self.world.get_entity("player")
        st = p.get(Quests).quests[prince]
        st["done"] = True
        st["reward_claimed"] = True
        q = DAEDRIC_PRINCES[prince]["quest"]
        rw = q["reward"]
        if rw.get("atk"):
            gear = p.get(Gear)
            gear.attack += rw["atk"]
            gear.weapon = rw["name"]
            p.get(Pack).items.append(rw["name"])
        if rw.get("maxhp"):
            hp = p.get(Health)
            hp.max_value += rw["maxhp"]
            hp.value += rw["maxhp"]
        if rw.get("heal"):
            hp = p.get(Health)
            hp.value = min(hp.max_value, hp.value + rw["heal"])
        self._log(p, f"支线达成 · {q['name']}：{rw['text']}")
        self.bus.emit(EventTypes.QUEST_COMPLETE, {"prince": prince, "quest": q["name"],
                                                 "reward": rw["name"]})

    def _log(self, player, msg: str) -> None:
        TravelSystem._log(player, msg)


# ─────────────────────────────────────────────
# RestSystem
# ─────────────────────────────────────────────

class RestSystem(System):
    """时间流逝：每满 1 单位时间 +1 天并微量回血。"""

    priority = 90

    def __init__(self, bus, engine: "PlayEngine") -> None:
        self.bus = bus
        self.engine = engine

    def update(self, world: World, dt: float) -> None:
        player = world.get_entity("player")
        if player is None:
            return
        hp = player.get(Health)
        clk = player.get(Clock)
        if hp.value <= 0:
            self.engine.check_death(player)
            return
        acc = world.get_data("__clock_acc", 0.0) + dt
        while acc >= 1.0:
            acc -= 1.0
            clk.day += 1
            if 0 < hp.value < hp.max_value:
                hp.value += 1
        world.set_data("__clock_acc", acc)
