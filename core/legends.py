"""《矮人要塞风格的上古卷轴》——世界编年史数据模型与叙事层。

本模块定义「以矮人要塞 Legends Mode 形态呈现上古卷轴」所需的数据模型：
Era（纪元）/ Region（省）/ Site（地点）/ Figure（历史人物）/ Faction（派系）/
Artifact（神器）/ HistoricalEvent（史事）/ Age（时代）以及聚合它们的 WorldModel。

叙事层 ``narrate_*`` 把每一条史事与每一个条目渲染成矮人要塞 Legends Mode
那种「档案式、平实而连绵」的编年史散文，并产出可点击的交叉引用（超链接）。

所有数据类均可 ``to_dict()/from_dict()`` 完全序列化，便于存档与读档。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ── 可交叉引用的条目种类（用于超链接） ──
LINKABLE_KEYS = {"figure", "figure2", "site", "region", "faction", "faction2", "artifact"}
# 把 figure2 / faction2 归一为单数种类
KEY_TO_KIND = {
    "figure": "figure", "figure2": "figure",
    "site": "site",
    "region": "region",
    "faction": "faction", "faction2": "faction",
    "artifact": "artifact",
}


@dataclass
class Era:
    id: str
    name: str
    prefix: str
    start: int
    desc: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Era":
        return cls(**d)


@dataclass
class Region:
    id: str
    name: str
    en: str
    tile: str
    alignment: str
    biome: str
    capital: str
    color: str
    desc: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Region":
        return cls(**d)


@dataclass
class Site:
    id: str
    name: str
    region_id: str
    kind: str                 # city / tower / temple / fortress / ruin
    faction_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Site":
        return cls(**d)


@dataclass
class Faction:
    id: str
    name: str
    en: str
    kind: str                 # alliance / empire / cult / guild / order / daedric
    crest: str
    colors: List[str] = field(default_factory=list)
    provinces: List[str] = field(default_factory=list)
    race: str = ""
    leader_title: str = ""
    desc: str = ""
    daedra: Optional[str] = None
    divine: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Faction":
        return cls(**d)


@dataclass
class Figure:
    id: str
    name: str
    race: str
    faction_id: str
    born_year: int
    died_year: int = -1       # -1 表示在世
    title: str = ""           # 称号 / 家族
    is_mythic: bool = False
    is_dragon: bool = False
    achievements: List[str] = field(default_factory=list)  # 关联史事 id

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Figure":
        return cls(**d)


@dataclass
class Artifact:
    id: str
    name: str
    en: str
    kind: str                 # elder_scroll / daedric / aedric / relic
    desc: str = ""
    daedra: Optional[str] = None
    divine: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Artifact":
        return cls(**d)


@dataclass
class HistoricalEvent:
    id: str
    year: int                 # 绝对年份
    era_id: str
    type: str
    text: str
    refs: Dict[str, str] = field(default_factory=dict)  # figure/site/region/faction/artifact -> id

    @property
    def name(self) -> str:
        """列表展示名：截取史事文本前 60 字（完整文本在条目页查看）。"""
        if len(self.text) <= 60:
            return self.text
        return self.text[:57] + "..."

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "HistoricalEvent":
        return cls(**d)


@dataclass
class Age:
    id: str
    name: str
    start: int
    end: int
    desc: str
    event_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Age":
        return cls(**d)


@dataclass
class WorldModel:
    seed: int
    title: str
    eras: List[Era] = field(default_factory=list)
    regions: List[Region] = field(default_factory=list)
    sites: List[Site] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    factions: List[Faction] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    events: List[HistoricalEvent] = field(default_factory=list)
    ages: List[Age] = field(default_factory=list)

    # ── 元名称表（种族/魔神/圣灵 名称，便于叙事与读档后解析） ──
    meta: Dict[str, Any] = field(default_factory=dict)

    # ── 索引（构建后填充） ──
    _idx: Dict[str, Dict[str, Any]] = field(default_factory=dict, repr=False)

    # ───────── 索引 ─────────
    def build_indexes(self) -> None:
        self._idx = {
            "era":     {e.id: e for e in self.eras},
            "region":  {r.id: r for r in self.regions},
            "site":    {s.id: s for s in self.sites},
            "figure":  {f.id: f for f in self.figures},
            "faction": {f.id: f for f in self.factions},
            "artifact":{a.id: a for a in self.artifacts},
            "age":     {a.id: a for a in self.ages},
            "event":   {e.id: e for e in self.events},
        }

    def get(self, kind: str, eid: str) -> Optional[Any]:
        return self._idx.get(kind, {}).get(eid)

    def _ensure_index(self) -> None:
        if not self._idx:
            self.build_indexes()

    # ───────── 年份标签 ─────────
    def era_for_year(self, abs_year: int) -> Era:
        self._ensure_index()
        sel = self.eras[0]
        for e in self.eras:
            if abs_year >= e.start:
                sel = e
        return sel

    def year_label(self, abs_year: int) -> str:
        era = self.era_for_year(abs_year)
        local = abs_year - era.start
        if era.prefix == "黎明":
            return f"黎明 {local}"
        return f"{era.prefix} {local}"

    # ───────── 序列化 ─────────
    def to_dict(self) -> dict:
        return {
            "seed": self.seed,
            "title": self.title,
            "eras": [e.to_dict() for e in self.eras],
            "regions": [r.to_dict() for r in self.regions],
            "sites": [s.to_dict() for s in self.sites],
            "figures": [f.to_dict() for f in self.figures],
            "factions": [f.to_dict() for f in self.factions],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "events": [e.to_dict() for e in self.events],
            "ages": [a.to_dict() for a in self.ages],
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorldModel":
        wm = cls(
            seed=d.get("seed", 0),
            title=d.get("title", "无名之卷"),
            eras=[Era.from_dict(x) for x in d.get("eras", [])],
            regions=[Region.from_dict(x) for x in d.get("regions", [])],
            sites=[Site.from_dict(x) for x in d.get("sites", [])],
            figures=[Figure.from_dict(x) for x in d.get("figures", [])],
            factions=[Faction.from_dict(x) for x in d.get("factions", [])],
            artifacts=[Artifact.from_dict(x) for x in d.get("artifacts", [])],
            events=[HistoricalEvent.from_dict(x) for x in d.get("events", [])],
            ages=[Age.from_dict(x) for x in d.get("ages", [])],
            meta=d.get("meta", {}),
        )
        wm.build_indexes()
        return wm

    def to_json(self, *, ensure_ascii: bool = False, **kw: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, **kw)

    @classmethod
    def from_json(cls, s: str) -> "WorldModel":
        return cls.from_dict(json.loads(s))

    # ───────── 交叉引用 ─────────
    def event_related(self, ev: HistoricalEvent) -> List[Tuple[str, str, str]]:
        """返回事件的超链接目标列表 [(kind, eid, label)]。"""
        self._ensure_index()
        out: List[Tuple[str, str, str]] = []
        seen = set()
        for key, eid in ev.refs.items():
            if key not in LINKABLE_KEYS:
                continue
            kind = KEY_TO_KIND[key]
            if (kind, eid) in seen:
                continue
            ent = self.get(kind, eid)
            if ent is None:
                continue
            label = getattr(ent, "name", eid)
            out.append((kind, eid, label))
            seen.add((kind, eid))
        return out

    # ───────── 叙事：条目页 ─────────
    def narrate_figure(self, fig: Figure) -> Dict[str, Any]:
        self._ensure_index()
        race = self.get("region", fig.race)  # 兼容；实际 race 存 id
        race_name = self._race_name(fig.race)
        fac = self.get("faction", fig.faction_id)
        fac_name = fac.name if fac else fig.faction_id
        lines = []
        if fig.is_mythic:
            lines.append("神话人物，事迹载于创世之初、时间凝固之前。")
        lines.append(f"种族：{race_name}")
        lines.append(f"所属：{fac_name}")
        born = self.year_label(fig.born_year)
        died = self.year_label(fig.died_year) if fig.died_year >= 0 else "至今犹存"
        lines.append(f"生卒：{born} — {died}")
        if fig.title:
            lines.append(f"称号：{fig.title}")
        if fig.achievements:
            lines.append(f"事迹：其名载入 {len(fig.achievements)} 卷史事。")
        evs = [e for e in self.events if e.refs.get("figure") == fig.id or e.refs.get("figure2") == fig.id]
        evs.sort(key=lambda e: e.year)
        related: List[Tuple[str, str, str]] = []
        for e in evs:
            for kind, eid, label in self.event_related(e):
                if (kind, eid) not in [(k, i) for k, i, _ in related] and kind != "figure":
                    related.append((kind, eid, label))
        title = fig.name + (f" · {fig.title}" if fig.title else "")
        return {
            "kind": "figure", "eid": fig.id, "title": title,
            "subtitle": f"{race_name} · {fac_name}",
            "description": "\n".join(lines),
            "events": [e.text for e in evs],
            "stats": [("种族", race_name), ("派系", fac_name),
                      ("生", born), ("卒", died), ("史事", str(len(evs)))],
            "related": related,
        }

    def narrate_faction(self, fac: Faction) -> Dict[str, Any]:
        self._ensure_index()
        prov_names = [self.get("region", p).name for p in fac.provinces if self.get("region", p)]
        members = [f for f in self.figures if f.faction_id == fac.id]
        evs = [e for e in self.events
               if e.refs.get("faction") == fac.id or e.refs.get("faction2") == fac.id]
        evs.sort(key=lambda e: e.year)
        lines = [fac.desc] if fac.desc else []
        if prov_names:
            lines.append("辖境：" + "、".join(prov_names))
        lines.append(f"领袖称号：{fac.leader_title}")
        if fac.daedra:
            d = self._daedra_name(fac.daedra)
            lines.append(f"侍奉魔神：{d}")
        related: List[Tuple[str, str, str]] = []
        for m in members[:12]:
            related.append(("figure", m.id, m.name))
        for p in prov_names:
            pass
        for e in evs:
            for kind, eid, label in self.event_related(e):
                if kind == "region" and (kind, eid) not in [(k, i) for k, i, _ in related]:
                    related.append((kind, eid, label))
        return {
            "kind": "faction", "eid": fac.id, "title": fac.name,
            "subtitle": f"{fac.kind} · 纹章：{fac.crest}",
            "description": "\n".join(lines),
            "events": [e.text for e in evs],
            "stats": [("种类", fac.kind), ("成员", str(len(members))),
                      ("辖境", str(len(prov_names))), ("史事", str(len(evs)))],
            "related": related,
        }

    def narrate_site(self, site: Site) -> Dict[str, Any]:
        self._ensure_index()
        region = self.get("region", site.region_id)
        fac = self.get("faction", site.faction_id) if site.faction_id else None
        evs = [e for e in self.events if e.refs.get("site") == site.id]
        evs.sort(key=lambda e: e.year)
        lines = [f"类别：{site.kind}", f"所在：{region.name if region else site.region_id}"]
        if fac:
            lines.append(f"归属：{fac.name}")
        related: List[Tuple[str, str, str]] = []
        if region:
            related.append(("region", region.id, region.name))
        if fac:
            related.append(("faction", fac.id, fac.name))
        for e in evs:
            for kind, eid, label in self.event_related(e):
                if kind in ("figure", "artifact", "faction") and (kind, eid) not in [(k, i) for k, i, _ in related]:
                    related.append((kind, eid, label))
        return {
            "kind": "site", "eid": site.id, "title": site.name,
            "subtitle": f"{site.kind} · {region.name if region else ''}",
            "description": "\n".join(lines),
            "events": [e.text for e in evs],
            "stats": [("类别", site.kind), ("地域", region.name if region else site.region_id),
                      ("史事", str(len(evs)))],
            "related": related,
        }

    def narrate_artifact(self, art: Artifact) -> Dict[str, Any]:
        self._ensure_index()
        evs = [e for e in self.events if e.refs.get("artifact") == art.id]
        evs.sort(key=lambda e: e.year)
        lines = [art.desc] if art.desc else []
        if art.daedra:
            lines.append(f"渊源魔神：{self._daedra_name(art.daedra)}")
        if art.divine:
            lines.append(f"渊源圣灵：{self._divine_name(art.divine)}")
        related: List[Tuple[str, str, str]] = []
        for e in evs:
            for kind, eid, label in self.event_related(e):
                if (kind, eid) not in [(k, i) for k, i, _ in related]:
                    related.append((kind, eid, label))
        return {
            "kind": "artifact", "eid": art.id, "title": art.name,
            "subtitle": f"{art.kind}",
            "description": "\n".join(lines),
            "events": [e.text for e in evs],
            "stats": [("种类", art.kind), ("史事", str(len(evs)))] + (
                [("魔神", self._daedra_name(art.daedra))] if art.daedra else []) + (
                [("圣灵", self._divine_name(art.divine))] if art.divine else []),
            "related": related,
        }

    def narrate_age(self, age: Age) -> Dict[str, Any]:
        self._ensure_index()
        evs = [self.get("event", eid) for eid in age.event_ids if self.get("event", eid)]
        evs.sort(key=lambda e: e.year)
        span = f"{self.year_label(age.start)} — {self.year_label(age.end)}"
        related: List[Tuple[str, str, str]] = []
        for e in evs:
            for kind, eid, label in self.event_related(e):
                if (kind, eid) not in [(k, i) for k, i, _ in related]:
                    related.append((kind, eid, label))
        return {
            "kind": "age", "eid": age.id, "title": age.name,
            "subtitle": f"跨度 {span}",
            "description": age.desc,
            "events": [e.text for e in evs],
            "stats": [("跨度", span), ("史事", str(len(evs)))],
            "related": related,
        }

    def narrate_region(self, region: Region) -> Dict[str, Any]:
        self._ensure_index()
        sites = [s for s in self.sites if s.region_id == region.id]
        evs = [e for e in self.events if e.refs.get("region") == region.id]
        evs.sort(key=lambda e: e.year)
        lines = [region.desc, f"地貌：{region.biome}", f"都城：{region.capital}",
                 f"阵营属性：{region.alignment}"]
        related: List[Tuple[str, str, str]] = []
        for s in sites:
            related.append(("site", s.id, s.name))
        for e in evs:
            for kind, eid, label in self.event_related(e):
                if kind in ("faction", "figure", "artifact") and (kind, eid) not in [(k, i) for k, i, _ in related]:
                    related.append((kind, eid, label))
        return {
            "kind": "region", "eid": region.id, "title": region.name,
            "subtitle": f"{region.en} · {region.biome}",
            "description": "\n".join(lines),
            "events": [e.text for e in evs],
            "stats": [("地貌", region.biome), ("都城", region.capital),
                      ("地点", str(len(sites))), ("史事", str(len(evs)))],
            "related": related,
        }

    def narrate_event(self, ev: HistoricalEvent) -> Dict[str, Any]:
        """史事条目页：展示完整文本、年代/纪元/类型，以及交叉引用。"""
        self._ensure_index()
        era = self.get("era", ev.era_id)
        era_name = era.name if era else ev.era_id
        year_label = self.year_label(ev.year)
        related = self.event_related(ev)
        ref_labels: List[Tuple[str, str, str]] = []
        for key, eid in ev.refs.items():
            if key in LINKABLE_KEYS:
                kind = KEY_TO_KIND[key]
                ent = self.get(kind, eid)
                if ent:
                    ref_labels.append((kind, eid, getattr(ent, "name", eid)))
        return {
            "kind": "event", "eid": ev.id, "title": f"{year_label} · {ev.type}",
            "subtitle": f"{ev.type} · {year_label}",
            "description": ev.text,
            "events": [],
            "stats": [("年代", year_label), ("纪元", era_name), ("类型", ev.type)],
            "related": ref_labels,
        }

    # ───────── 落地页 ─────────
    def landing_categories(self) -> List[Tuple[str, str, int]]:
        return [
            ("figure",  "历史人物",     len(self.figures)),
            ("site",    "地点",         len(self.sites)),
            ("region",  "省份",         len(self.regions)),
            ("faction", "派系",         len(self.factions)),
            ("artifact","神器",         len(self.artifacts)),
            ("event",   "史事",         len(self.events)),
            ("age",     "时代",         len(self.ages)),
            ("map",     "世界地图",     1),
        ]

    # ───────── 名称辅助 ─────────
    def _race_name(self, race_id: str) -> str:
        # race 表不在 WorldModel 内，由 world_gen 注入到 _idx 的 "race" 中（若有）
        r = self.meta.get("race", {}).get(race_id)
        return r if r else race_id

    def _daedra_name(self, daedra_id: str) -> str:
        d = self.meta.get("daedra", {}).get(daedra_id)
        return d if d else daedra_id

    def _divine_name(self, divine_id: str) -> str:
        d = self.meta.get("divine", {}).get(divine_id)
        return d if d else divine_id


def entry_page(world: WorldModel, kind: str, eid: str) -> Optional[Dict[str, Any]]:
    """统一入口：根据 kind 返回对应条目页字典。"""
    world._ensure_index()
    if kind == "figure":
        ent = world.get("figure", eid)
        return world.narrate_figure(ent) if ent else None
    if kind == "faction":
        ent = world.get("faction", eid)
        return world.narrate_faction(ent) if ent else None
    if kind == "site":
        ent = world.get("site", eid)
        return world.narrate_site(ent) if ent else None
    if kind == "artifact":
        ent = world.get("artifact", eid)
        return world.narrate_artifact(ent) if ent else None
    if kind == "age":
        ent = world.get("age", eid)
        return world.narrate_age(ent) if ent else None
    if kind == "region":
        ent = world.get("region", eid)
        return world.narrate_region(ent) if ent else None
    if kind == "event":
        ent = world.get("event", eid)
        return world.narrate_event(ent) if ent else None
    return None
