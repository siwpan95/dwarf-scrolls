"""程序化历史模拟 —— 把「世界骨架」叠加成一部可载入卷轴的编年史。

以矮人要塞 Legends Mode 的精神，逐年（按绝对年份跨纪元）掷骰生成史事：
诞生 / 死亡（战死·寿终·暗杀）/ 即位 / 战役 / 宣战 / 媾和 / 结盟 /
巨龙之战（以上古卷轴放逐世界吞噬者，留下时间之伤）/ 湮灭入侵 /
发现上古卷轴 / 锻造神器 / 龙破（时间的织线断裂）/ 塔的激活与倾颓 / 教派分裂。

每条史事交叉引用 人物·地点·派系·神器，并归入一个「时代（Age）」——
后者以矮人要塞那种平实的口吻概述一段纪元：「这个时代以……为特征。」
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .engine_bootstrap import GAME_ROOT
from .legends import WorldModel, HistoricalEvent, Age, Figure


# 每年各史事类型的权重
EVENT_WEIGHTS = [
    ("birth", 0.12), ("death", 0.18), ("accession", 0.08), ("battle", 0.13),
    ("war_start", 0.05), ("war_end", 0.04), ("alliance", 0.05),
    ("dragon_war", 0.03), ("daedric_incursion", 0.07), ("elder_scroll_found", 0.04),
    ("artifact_forged", 0.05), ("dragon_break", 0.02), ("tower_activated", 0.04),
    ("tower_fallen", 0.02), ("schism", 0.03),
]

MAX_EVENTS = 460

# 时代命名（按窗口内主导史事类型）
AGE_STYLES = {
    "battle": ("血与铁之纪", "这个时代以连绵的刀兵为特征，烽火燃遍泰姆瑞尔，无数英名殁于阵前。"),
    "death": ("凋零之纪", "这个时代带走许多旧日的英雄，墓石在各省悄然增多。"),
    "war_start": ("风暴前夜之纪", "宿怨在暗处积聚，宣战的号角终于撕裂了表面的和平。"),
    "dragon_war": ("龙归来之纪", "巨龙的阴影重新笼罩天空，龙语在喉之雪回响，时间本身为之震颤。"),
    "daedric_incursion": ("湮灭低语之纪", "魔神的裂隙在凡世绽开，冷港的锁链与颤栗的疯狂渗入梦中。"),
    "elder_scroll_found": ("卷轴重光之纪", "尘封的上古卷轴再度被飞蛾祭司捧出，未写的命运在眼前浮现。"),
    "alliance": ("盟誓之纪", "旗帜在新的誓约下交汇，旧敌成为比邻，疆界被重新商量。"),
    "accession": ("加冕之纪", "新的君主在古都登基，王朝的齿轮悄然转向。"),
    "artifact_forged": ("巧匠之纪", "秘法在锻炉中凝形，镇族之宝自匠人之手诞生。"),
    "tower_activated": ("锚定之纪", "古老的塔重新点亮，凡世的根基随之稳固。"),
    "schism": ("裂教之纪", "信仰的裂痕蔓延，同一炉灶升起了两支青烟。"),
    "birth": ("新生之纪", "新的名字被写进史册，年轻的脚步将在日后踏响战场。"),
    "dragon_break": ("灰白停顿之纪", "时间的织线在此断裂又重续，无人能确言当时究竟发生了什么。"),
}
AGE_DEFAULT = ("沉静之纪", "这个时代相对平静，泰姆瑞尔在两次风暴之间勉强喘息。")


class HistoryGenerator:
    """把 WorldModel 叠加出史事与时代。"""

    def __init__(self, seed: int = 0, world: Optional[WorldModel] = None,
                 content_dir: Any = None) -> None:
        self.seed = int(seed)
        self.rng = random.Random(self.seed ^ 0x9E3779B9)
        self.world = world
        self.content_dir = Path(content_dir) if content_dir else (GAME_ROOT / "content")
        self.templates = self._load("events.json")["templates"]
        self.cosmo = self._load("cosmology.json")
        self._names = self._load("names.json")
        self._eid = 0

    def _load(self, name: str) -> Any:
        return json.loads((self.content_dir / name).read_text(encoding="utf-8"))

    # ── 工具 ──
    def _new_event_id(self) -> str:
        self._eid += 1
        return f"ev_{self._eid:04d}"

    def _era_local(self, year: int) -> Tuple[Any, int]:
        era = self.world.era_for_year(year)
        return era, year - era.start

    def _alive_figures(self, year: int, exclude: Optional[Figure] = None) -> List[Figure]:
        out = []
        for f in self.world.figures:
            if f.is_mythic:
                continue
            if f.born_year > year - 10:
                continue
            if f.died_year >= 0 and f.died_year <= year:
                continue
            if exclude is not None and f is exclude:
                continue
            out.append(f)
        return out

    def _pick_faction(self, exclude: Optional[str] = None) -> Any:
        fs = [f for f in self.world.factions if f.id != exclude]
        return self.rng.choice(fs) if fs else None

    def _pick_two_factions(self) -> Tuple[Any, Any]:
        a = self.rng.choice(self.world.factions)
        b = self.rng.choice([f for f in self.world.factions if f.id != a.id])
        return a, b

    def _pick_site(self) -> Any:
        return self.rng.choice(self.world.sites) if self.world.sites else None

    def _pick_artifact(self) -> Any:
        return self.rng.choice(self.world.artifacts) if self.world.artifacts else None

    def _pick_daedra(self) -> str:
        ids = list(self.world.meta.get("daedra", {}).keys())
        return self.rng.choice(ids) if ids else "azura"

    def _pick_tower(self) -> Dict[str, str]:
        towers = self.cosmo.get("towers", [])
        return self.rng.choice(towers) if towers else {"name": "无名之塔", "stone": "无名之石"}

    def _ctx(self, year: int, **extra) -> Dict[str, str]:
        era, local = self._era_local(year)
        ctx = {
            "era": era.prefix, "year": str(local),
            "adj": "", "race": "", "fig": "", "fig2": "",
            "faction": "", "faction2": "", "site": "", "region": "",
            "leader": "", "epithet": "", "count": str(self.rng.randint(80, 4200)),
            "age": str(self.rng.randint(24, 92)),
            "daedra": "", "tower": "", "stone": "", "dragon": "", "artifact": "",
        }
        ctx.update(extra)
        return ctx

    def _fill(self, etype: str, ctx: Dict[str, str]) -> str:
        tmpls = self.templates.get(etype, ["{fig} 于 {era}{year} 留下了痕迹。"])
        return self.rng.choice(tmpls).format(**ctx)

    def _make_event(self, year: int, etype: str, text: str, refs: Dict[str, str]) -> HistoricalEvent:
        return HistoricalEvent(
            id=self._new_event_id(), year=year, era_id=self.world.era_for_year(year).id,
            type=etype, text=text, refs=refs,
        )

    # ── 各史事生成 ──
    def _gen_birth(self, year: int) -> Optional[HistoricalEvent]:
        fac = self._pick_faction()
        if fac is None:
            return None
        style = self._style_of(fac.race or "generic")
        given = self.rng.choice(style["given"])
        name = f"{given}·{self.rng.choice(style['house'])}" if self.rng.random() < 0.5 else given
        title = self.rng.choice(style["epithet"])
        fig = Figure(id=f"fig_{1000+self._eid:03d}", name=name, race=fac.race or "generic",
                     faction_id=fac.id, born_year=year, died_year=-1, title=title)
        self.world.figures.append(fig)
        self.world._idx["figure"][fig.id] = fig
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        ctx = self._ctx(year, race=(self.world.meta.get("race", {}).get(fac.race, fac.race)),
                        fig=fig.name, faction=fac.name,
                        site=site.name if site else "", region=region.name if region else "")
        text = self._fill("birth", ctx)
        refs = {"figure": fig.id, "faction": fac.id}
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        fig.achievements.append(self._new_event_id())
        return self._make_event(year, "birth", text, refs)

    def _style_of(self, race_id: str) -> Dict[str, Any]:
        race = next((r for r in self._races() if r["id"] == race_id), None)
        key = race["name_style"] if race else "generic"
        names = self._load("names.json") if not hasattr(self, "_names") else self._names
        return names["styles"].get(key, names["styles"]["generic"])

    def _races(self) -> List[Dict[str, Any]]:
        if not hasattr(self, "_races_cache"):
            self._races_cache = self._load("races.json")["races"]
        return self._races_cache

    def _gen_death(self, year: int) -> Optional[HistoricalEvent]:
        alive = self._alive_figures(year)
        if not alive:
            return None
        fig = self.rng.choice(alive)
        fig.died_year = year
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        fac = self.world.get("faction", fig.faction_id)
        kind = self.rng.choice(["death_battle", "death_age", "death_assassinate"])
        ctx = self._ctx(year, fig=fig.name, faction=(fac.name if fac else fig.faction_id),
                        site=site.name if site else "", region=region.name if region else "",
                        age=str(year - fig.born_year), epithet=fig.title)
        refs = {"figure": fig.id}
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if fac:
            refs["faction"] = fac.id
        if kind == "death_assassinate":
            killer = self._pick_faction(exclude=fig.faction_id)
            if killer:
                ctx["faction2"] = killer.name
                refs["faction2"] = killer.id
        text = self._fill(kind, ctx)
        return self._make_event(year, kind, text, refs)

    def _gen_accession(self, year: int) -> Optional[HistoricalEvent]:
        alive = self._alive_figures(year)
        if not alive:
            return None
        fig = self.rng.choice(alive)
        fac = self.world.get("faction", fig.faction_id)
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        ctx = self._ctx(year, fig=fig.name, faction=(fac.name if fac else fig.faction_id),
                        leader=(fac.leader_title if fac else "领袖"),
                        site=site.name if site else "", region=region.name if region else "")
        refs = {"figure": fig.id}
        if fac:
            refs["faction"] = fac.id
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        text = self._fill("accession", ctx)
        fig.achievements.append(self._new_event_id())
        return self._make_event(year, "accession", text, refs)

    def _gen_battle(self, year: int) -> Optional[HistoricalEvent]:
        a, b = self._pick_two_factions()
        alive = self._alive_figures(year)
        cmd = self.rng.choice(alive) if alive else None
        cas = self.rng.choice(alive) if alive else None
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        ctx = self._ctx(year, faction=a.name, faction2=b.name,
                        fig=(cmd.name if cmd else "无名将领"),
                        fig2=(cas.name if cas else "一名敌将"),
                        site=site.name if site else "", region=region.name if region else "")
        refs = {"faction": a.id, "faction2": b.id}
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if cmd:
            refs["figure"] = cmd.id; cmd.achievements.append(self._new_event_id())
        if cas:
            refs["figure2"] = cas.id; cas.died_year = year; cas.achievements.append(self._new_event_id())
        text = self._fill("battle", ctx)
        return self._make_event(year, "battle", text, refs)

    def _gen_war(self, year: int, end: bool) -> Optional[HistoricalEvent]:
        a, b = self._pick_two_factions()
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        etype = "war_end" if end else "war_start"
        ctx = self._ctx(year, faction=a.name, faction2=b.name,
                        site=site.name if site else "", region=region.name if region else "")
        refs = {"faction": a.id, "faction2": b.id}
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        text = self._fill(etype, ctx)
        return self._make_event(year, etype, text, refs)

    def _gen_alliance(self, year: int) -> Optional[HistoricalEvent]:
        a, b = self._pick_two_factions()
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        alive = self._alive_figures(year)
        broker = self.rng.choice(alive) if alive else None
        ctx = self._ctx(year, faction=a.name, faction2=b.name,
                        fig=(broker.name if broker else ""),
                        site=site.name if site else "", region=region.name if region else "")
        refs = {"faction": a.id, "faction2": b.id}
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if broker:
            refs["figure"] = broker.id
        text = self._fill("alliance", ctx)
        return self._make_event(year, "alliance", text, refs)

    def _gen_dragon_war(self, year: int) -> Optional[HistoricalEvent]:
        dragons = [f for f in self.world.figures if f.is_dragon]
        if not dragons:
            return None
        dragon = self.rng.choice(dragons)
        alive = self._alive_figures(year)
        hero = self.rng.choice(alive) if alive else None
        # 选用一卷上古卷轴
        scroll = next((a for a in self.world.artifacts if a.kind == "elder_scroll"), None)
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        ctx = self._ctx(year, fig=(hero.name if hero else "无名英雄"), dragon=dragon.name,
                        site=site.name if site else "", region=region.name if region else "",
                        artifact=(scroll.name if scroll else "上古卷轴"))
        refs = {}
        if hero:
            refs["figure"] = hero.id; hero.achievements.append(self._new_event_id())
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if scroll:
            refs["artifact"] = scroll.id
        text = self._fill("dragon_war", ctx)
        return self._make_event(year, "dragon_war", text, refs)

    def _gen_daedric(self, year: int) -> Optional[HistoricalEvent]:
        daedra_id = self._pick_daedra()
        daedra_name = self.world.meta.get("daedra", {}).get(daedra_id, daedra_id)
        fac = self._pick_faction()
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        alive = self._alive_figures(year)
        defdr = self.rng.choice(alive) if alive else None
        art = self._pick_artifact()
        ctx = self._ctx(year, daedra=daedra_name, faction=(fac.name if fac else ""),
                        fig=(defdr.name if defdr else "守军"),
                        site=site.name if site else "", region=region.name if region else "",
                        artifact=(art.name if art else ""))
        refs = {}
        if fac:
            refs["faction"] = fac.id
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if defdr:
            refs["figure"] = defdr.id; defdr.achievements.append(self._new_event_id())
        if art:
            refs["artifact"] = art.id
        text = self._fill("daedric_incursion", ctx)
        return self._make_event(year, "daedric_incursion", text, refs)

    def _gen_scroll_found(self, year: int) -> Optional[HistoricalEvent]:
        scrolls = [a for a in self.world.artifacts if a.kind == "elder_scroll"]
        if not scrolls:
            return None
        art = self.rng.choice(scrolls)
        moth = next((f for f in self.world.factions if f.id == "ancestor_moth"), None)
        alive = self._alive_figures(year)
        priest = self.rng.choice(alive) if alive else None
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        ctx = self._ctx(year, artifact=art.name, fig=(priest.name if priest else "一名飞蛾祭司"),
                        faction=(moth.name if moth else "先祖飞蛾祭司团"),
                        site=site.name if site else "", region=region.name if region else "")
        refs = {"artifact": art.id}
        if moth:
            refs["faction"] = moth.id
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if priest:
            refs["figure"] = priest.id; priest.achievements.append(self._new_event_id())
        text = self._fill("elder_scroll_found", ctx)
        return self._make_event(year, "elder_scroll_found", text, refs)

    def _gen_artifact_forged(self, year: int) -> Optional[HistoricalEvent]:
        art = self._pick_artifact()
        if art is None:
            return None
        fac = self._pick_faction()
        alive = self._alive_figures(year)
        forger = self.rng.choice(alive) if alive else None
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        ctx = self._ctx(year, artifact=art.name, faction=(fac.name if fac else ""),
                        fig=(forger.name if forger else "一名匠人"),
                        site=site.name if site else "", region=region.name if region else "")
        refs = {"artifact": art.id}
        if fac:
            refs["faction"] = fac.id
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if forger:
            refs["figure"] = forger.id; forger.achievements.append(self._new_event_id())
        text = self._fill("artifact_forged", ctx)
        return self._make_event(year, "artifact_forged", text, refs)

    def _gen_dragon_break(self, year: int) -> Optional[HistoricalEvent]:
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        fac = self._pick_faction()
        ctx = self._ctx(year, site=site.name if site else "", region=region.name if region else "",
                        faction=(fac.name if fac else ""))
        refs = {}
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if fac:
            refs["faction"] = fac.id
        text = self._fill("dragon_break", ctx)
        return self._make_event(year, "dragon_break", text, refs)

    def _gen_tower(self, year: int, fallen: bool) -> Optional[HistoricalEvent]:
        tower = self._pick_tower()
        # 找到该塔所在省
        prov = next((p for p in self.world.regions if p.name == tower.get("place")), None)
        if prov is None:
            prov = self.rng.choice(self.world.regions)
        site = next((s for s in self.world.sites if s.region_id == prov.id and s.kind == "tower"), None)
        fac = self._pick_faction()
        alive = self._alive_figures(year)
        actor = self.rng.choice(alive) if alive else None
        ctx = self._ctx(year, tower=tower["name"], stone=tower.get("stone", "无名之石"),
                        region=prov.name, fig=(actor.name if actor else ""),
                        site=(site.name if site else prov.capital),
                        faction=(fac.name if fac else ""))
        refs = {"region": prov.id}
        if site:
            refs["site"] = site.id
        if fac:
            refs["faction"] = fac.id
        if actor:
            refs["figure"] = actor.id; actor.achievements.append(self._new_event_id())
        etype = "tower_fallen" if fallen else "tower_activated"
        text = self._fill(etype, ctx)
        return self._make_event(year, etype, text, refs)

    def _gen_schism(self, year: int) -> Optional[HistoricalEvent]:
        fac = self._pick_faction()
        alive = self._alive_figures(year)
        leader = self.rng.choice(alive) if alive else None
        site = self._pick_site()
        region = self.world.get("region", site.region_id) if site else None
        ctx = self._ctx(year, faction=fac.name, leader=(fac.leader_title if fac else "领袖"),
                        fig=(leader.name if leader else ""),
                        site=site.name if site else "", region=region.name if region else "")
        refs = {"faction": fac.id}
        if site:
            refs["site"] = site.id; refs["region"] = site.region_id
        if leader:
            refs["figure"] = leader.id
        text = self._fill("schism", ctx)
        return self._make_event(year, "schism", text, refs)

    # ── 主循环 ──
    def generate(self) -> WorldModel:
        world = self.world
        # 起始年份：自精灵纪元起；结束：末纪元起点 + 跨度
        start = world.eras[1].start
        last = world.eras[-1]
        end = last.start + 500

        # 神话/巨龙开篇事件（黎明纪元的创世痕迹）
        self._opening_myth(world)

        year = start
        while year <= end and len(world.events) < MAX_EVENTS:
            etype = self.rng.choices(
                [e for e, _ in EVENT_WEIGHTS],
                weights=[w for _, w in EVENT_WEIGHTS], k=1,
            )[0]
            ev = self._dispatch(etype, year)
            if ev is not None:
                world.events.append(ev)
            year += 1

        world.events.sort(key=lambda e: e.year)
        self._build_ages(world, start, end)
        world.build_indexes()
        return world

    def _opening_myth(self, world: WorldModel) -> None:
        """黎明纪元的创世痕迹：阿卡与洛克兰、塔的树立、巨龙之战争序幕。"""
        dawn = world.eras[0]
        year = dawn.start + 5
        # 精金塔树立
        tower = next((t for t in self.cosmo.get("towers", []) if t["id"] == "adamantine"), None)
        if tower:
            prov = next((p for p in world.regions if p.name == tower.get("place")), world.regions[0])
            ctx = self._ctx(year, tower=tower["name"], stone=tower.get("stone", ""),
                           region=prov.name, faction="empire")
            refs = {"region": prov.id}
            text = f"于黎明之初，{tower['name']}（{tower.get('stone','')}）在{prov.name}树立，凡世第一次被锚定于混沌之中。"
            world.events.append(self._make_event(year, "tower_activated", text, refs))
        # 巨龙之战序章（用神话人物）
        dragons = [f for f in world.figures if f.is_dragon]
        heroes = [f for f in world.figures if f.is_mythic and not f.is_dragon]
        if dragons and heroes:
            dragon = self.rng.choice(dragons)
            hero = self.rng.choice(heroes)
            scroll = next((a for a in world.artifacts if a.kind == "elder_scroll"), None)
            ctx = self._ctx(year + 20, fig=hero.name, dragon=dragon.name,
                           site="世界之喉", region="天际",
                           artifact=(scroll.name if scroll else "上古卷轴"))
            refs = {"figure": hero.id, "region": "skyrim"}
            if scroll:
                refs["artifact"] = scroll.id
            text = f"于黎明，{hero.name}在世界之喉（天际）以一卷上古卷轴将巨龙{dragon.name}掷向未来的湍流，时间之伤自此不愈。"
            world.events.append(self._make_event(year + 20, "dragon_war", text, refs))

    def _dispatch(self, etype: str, year: int) -> Optional[HistoricalEvent]:
        if etype == "birth":
            return self._gen_birth(year)
        if etype == "death":
            return self._gen_death(year)
        if etype == "accession":
            return self._gen_accession(year)
        if etype == "battle":
            return self._gen_battle(year)
        if etype == "war_start":
            return self._gen_war(year, False)
        if etype == "war_end":
            return self._gen_war(year, True)
        if etype == "alliance":
            return self._gen_alliance(year)
        if etype == "dragon_war":
            return self._gen_dragon_war(year)
        if etype == "daedric_incursion":
            return self._gen_daedric(year)
        if etype == "elder_scroll_found":
            return self._gen_scroll_found(year)
        if etype == "artifact_forged":
            return self._gen_artifact_forged(year)
        if etype == "dragon_break":
            return self._gen_dragon_break(year)
        if etype == "tower_activated":
            return self._gen_tower(year, False)
        if etype == "tower_fallen":
            return self._gen_tower(year, True)
        if etype == "schism":
            return self._gen_schism(year)
        return None

    # ── 时代（Ages） ──
    def _build_ages(self, world: WorldModel, start: int, end: int) -> None:
        step = 600
        aid = 0
        year = start
        while year < end:
            seg_end = min(end, year + step)
            evs = [e for e in world.events if year <= e.year < seg_end]
            # 主导类型
            counts: Dict[str, int] = {}
            for e in evs:
                counts[e.type] = counts.get(e.type, 0) + 1
            dominant = max(counts, key=counts.get) if counts else ""
            name, desc = AGE_STYLES.get(dominant, AGE_DEFAULT)
            age = Age(id=f"age_{aid:02d}", name=name, start=year, end=seg_end,
                      desc=desc, event_ids=[e.id for e in evs])
            world.ages.append(age)
            aid += 1
            year = seg_end
        # 重新编号，使名称更有层次感
        for i, age in enumerate(world.ages):
            if age.name == AGE_DEFAULT[0]:
                age.name = f"第 {i+1} 纪"
