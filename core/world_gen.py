"""TES 世界生成器 —— 把 content/*.json 渲染成一座可载入卷轴的泰姆瑞尔。

按种子可复现地生成：
- 纪元（cosmology）
- 九省（provinces）
- 地点（每省都城 + 塔 + 若干神殿/要塞/遗迹）
- 派系（factions）
- 历史人物（神话人物 / 巨龙 / 各派系英杰，依种族命名风格程序化生成）
- 神器（artifacts）

生成的是「世界骨架」，史事与时代由 ``history_gen.HistoryGenerator`` 叠加。
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List

from .engine_bootstrap import GAME_ROOT
from .legends import (
    WorldModel, Era, Region, Site, Faction, Figure, Artifact,
)

SITE_WORDS = ["古墓", "边境要塞", "残破神殿", "商栈", "瞭望塔", "祭坛",
              "藏书塔", "龙冢", "坠星坑", "枯井", "哨站", "圣井"]

# 省（中文名）→ 该省境内之塔（来自 cosmology.towers 的 place）
TOWER_PROVINCE = {
    "夏暮岛": "summerset",
    "晨风":   "morrowind",
    "天际":   "skyrim",
    "赛瑞迪尔": "cyrodiil",
    "黑沼":   "black_marsh",
}

ERA_WEIGHTS = [("dawn", 0.05), ("merethic", 0.15), ("1e", 0.25),
               ("2e", 0.25), ("3e", 0.20), ("4e", 0.10)]

MAJOR_FACTIONS = {"aldmeri_dominion", "daggerfall_covenant", "ebonheart_pact", "empire"}


class WorldGenerator:
    """按种子生成泰姆瑞尔世界模型。"""

    def __init__(self, seed: int = 0, content_dir: Any = None) -> None:
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.content_dir = Path(content_dir) if content_dir else (GAME_ROOT / "content")
        self.cosmo = self._load("cosmology.json")
        self.provinces = self._load("provinces.json")["provinces"]
        self.races = self._load("races.json")["races"]
        self.names = self._load("names.json")
        self.factions_data = self._load("factions.json")["factions"]
        self.artifacts_data = self._load("artifacts.json")["artifacts"]

    # ── 内容加载 ──
    def _load(self, name: str) -> Any:
        return json.loads((self.content_dir / name).read_text(encoding="utf-8"))

    def _province_faction(self, pid: str) -> Any:
        for f in self.factions_data:
            if pid in f.get("provinces", []):
                return f["id"]
        return None

    def _style_for(self, race_id: str) -> Dict[str, Any]:
        race = next((r for r in self.races if r["id"] == race_id), None)
        style_key = race["name_style"] if race else "generic"
        return self.names["styles"].get(style_key, self.names["styles"]["generic"])

    def _random_name(self, race_id: str) -> tuple:
        style = self._style_for(race_id)
        given = self.rng.choice(style["given"])
        if self.rng.random() < 0.5:
            name = f"{given}·{self.rng.choice(style['house'])}"
        else:
            name = given
        title = self.rng.choice(style["epithet"])
        return name, title

    def _random_born(self) -> int:
        eras = self.cosmo["eras"]
        ids = [e["id"] for e in eras]
        weights = [w for (i, w) in ERA_WEIGHTS if i in ids]
        era_id = self.rng.choices(ids, weights=weights, k=1)[0]
        era = next(e for e in eras if e["id"] == era_id)
        # 下一纪元起点（用于把 local 控制在当前纪元内）
        idx = ids.index(era_id)
        nxt = eras[idx + 1]["start"] if idx + 1 < len(eras) else era["start"] + 400
        span = max(20, nxt - era["start"] - 1)
        return era["start"] + self.rng.randint(1, span)

    # ── 生成 ──
    def generate(self) -> WorldModel:
        rng = self.rng
        eras = [Era(**e) for e in self.cosmo["eras"]]
        regions = [Region(**p) for p in self.provinces]
        factions = [Faction(**f) for f in self.factions_data]
        artifacts = [Artifact(**a) for a in self.artifacts_data]

        # 地点
        sites: List[Site] = []
        sid = 0
        province_faction = {}
        for p in self.provinces:
            fid = self._province_faction(p["id"])
            province_faction[p["id"]] = fid
            # 都城
            sites.append(Site(id=f"site_{sid:03d}", name=p["capital"],
                              region_id=p["id"], kind="city", faction_id=fid))
            sid += 1
            # 塔
            if p["name"] in TOWER_PROVINCE:
                tower = next((t for t in self.cosmo["towers"] if t["place"] == p["name"]), None)
                if tower and not (p["id"] == "cyrodiil"):  # 帝都自身即白金塔
                    sites.append(Site(id=f"site_{sid:03d}", name=tower["name"],
                                      region_id=p["id"], kind="tower", faction_id=fid))
                    sid += 1
            # 其余地点
            for _ in range(2):
                kind = rng.choice(["temple", "fortress", "ruin", "market"])
                sname = f"{p['name']}{rng.choice(SITE_WORDS)}"
                sites.append(Site(id=f"site_{sid:03d}", name=sname,
                                  region_id=p["id"], kind=kind, faction_id=fid))
                sid += 1

        # 历史人物
        figures: List[Figure] = []
        fid = 0

        def add_figure(name, race, faction_id, born, died=-1, title="",
                       mythic=False, dragon=False):
            nonlocal fid
            fig = Figure(id=f"fig_{fid:03d}", name=name, race=race,
                         faction_id=faction_id, born_year=born, died_year=died,
                         title=title, is_mythic=mythic, is_dragon=dragon)
            figures.append(fig)
            fid += 1
            return fig

        # 神话人物（生于黎明）
        dawn_start = self.cosmo["eras"][0]["start"]
        for nm in self.names.get("figures_mythic", []):
            race = "divine"
            if nm in ("奥杜因", "帕图纳克斯") or nm.endswith("崴尔") or "龙" in nm:
                race = "dragon"
            add_figure(nm, race, "empire", dawn_start + self.rng.randint(0, 30),
                       died=-1, mythic=True, dragon=(race == "dragon"))
        # 巨龙
        for nm in self.names.get("dragons", []):
            add_figure(nm, "dragon", "", dawn_start + self.rng.randint(0, 50),
                       died=-1, dragon=True)

        # 各派系英杰
        for f in self.factions_data:
            count = 9 if f["id"] in MAJOR_FACTIONS else 4
            for _ in range(count):
                nm, title = self._random_name(f["race"] or "generic")
                # 多数生于较近纪元，少数远古
                born = self._random_born()
                add_figure(nm, f["race"] or "generic", f["id"], born, died=-1, title=title)

        # 元名称表
        meta = {
            "race": {r["id"]: r["name"] for r in self.races},
            "daedra": {d["id"]: d["name"] for d in self.cosmo["daedra"]},
            "divine": {dv["id"]: dv["name"] for dv in self.cosmo["divines"]},
        }
        meta["race"]["dragon"] = "巨龙"
        meta["race"]["divine"] = "神祇"

        world = WorldModel(
            seed=self.seed,
            title="上古卷轴 · 泰姆瑞尔编年史",
            eras=eras,
            regions=regions,
            sites=sites,
            figures=figures,
            factions=factions,
            artifacts=artifacts,
            events=[],
            ages=[],
            meta=meta,
        )
        world.build_indexes()
        return world
