"""Headless self-check for Dwarf Scrolls.

Exercises the whole non-GUI pipeline: TES world generation, procedural history
generation, world JSON round trip + save slots, and the shared Legends Mode
view/reader navigation. tkinter, the GUI window and the CLI loop are never
imported.

Usage: python selfcheck.py
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Same path bootstrap as main.py: the repo directory must be importable so the
# dwarf_scrolls.py package-name bridge resolves dwarf_scrolls.core / .game.
for _p in (ROOT, ROOT.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


class Checker:
    """Collects failures so every check runs before exiting."""

    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed: list[str] = []

    def check(self, label: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed.append(label)
            print(f"  ok   {label}")
        else:
            message = f"{label}: {detail}" if detail else label
            self.failures.append(message)
            print(f"  FAIL {message}")

    def section(self, title: str) -> None:
        print(f"[{title}]")


def check_world(c: Checker, mods: dict) -> object:
    """World generation must be complete and reproducible by seed."""
    c.section("world generation")
    WorldGenerator = mods["WorldGenerator"]
    LINKABLE_KEYS = mods["LINKABLE_KEYS"]
    KEY_TO_KIND = mods["KEY_TO_KIND"]

    world = WorldGenerator(seed=7).generate()
    twin = WorldGenerator(seed=7).generate()
    other = WorldGenerator(seed=99).generate()

    c.check(
        "content JSONs produce 9 provinces and the full skeleton",
        len(world.regions) == 9 and len(world.eras) >= 6
        and len(world.factions) >= 3 and len(world.artifacts) >= 3
        and len(world.sites) >= 9 and len(world.figures) >= 50,
        f"regions={len(world.regions)} sites={len(world.sites)} "
        f"figures={len(world.figures)} factions={len(world.factions)}",
    )
    c.check(
        "every site points at a real region",
        all(s.region_id in {r.id for r in world.regions} for s in world.sites),
        "dangling site.region_id",
    )
    c.check(
        "every figure points at a real faction (or none)",
        all(f.faction_id == "" or f.faction_id in {x.id for x in world.factions}
            for f in world.figures),
        "dangling figure.faction_id",
    )
    c.check(
        "the same seed reproduces the same figures and sites",
        [f.name for f in world.figures] == [f.name for f in twin.figures]
        and [s.name for s in world.sites] == [s.name for s in twin.sites]
        and world.to_dict() == twin.to_dict(),
        "seed 7 produced two different worlds",
    )
    c.check(
        "a different seed produces a different world",
        [f.name for f in world.figures] != [f.name for f in other.figures],
        "seed 99 matched seed 7",
    )
    c.check(
        "indexes resolve entities by id",
        world.get("figure", world.figures[0].id) is not None
        and world.get("region", world.regions[0].id) is not None,
        "index lookup failed",
    )
    c.check(
        "year labels are computed relative to their era",
        world.year_label(world.eras[1].start) == f"{world.eras[1].prefix} 0",
        f"got {world.year_label(world.eras[1].start)!r}",
    )
    c.check(
        "landing categories match the model sizes",
        [count for _k, _l, count in world.landing_categories()]
        == [len(world.figures), len(world.sites), len(world.regions),
            len(world.factions), len(world.artifacts), len(world.events),
            len(world.ages), 1],
        "category counts drifted",
    )
    return world


def check_history(c: Checker, mods: dict, world, twin) -> object:
    """History simulation must be ordered, deterministic and self-consistent."""
    c.section("history generation")
    HistoryGenerator = mods["HistoryGenerator"]
    LINKABLE_KEYS = mods["LINKABLE_KEYS"]
    KEY_TO_KIND = mods["KEY_TO_KIND"]

    HistoryGenerator(seed=7, world=world).generate()
    HistoryGenerator(seed=7, world=twin).generate()

    c.check(
        "history produces a full chronicle and ages",
        len(world.events) > 100 and len(world.ages) >= 2,
        f"events={len(world.events)} ages={len(world.ages)}",
    )
    c.check(
        "events are sorted by year",
        [e.year for e in world.events] == sorted(e.year for e in world.events),
        "event years not monotonic",
    )
    c.check(
        "the same seed reproduces the same events",
        [(e.id, e.type, e.year, e.text) for e in world.events]
        == [(e.id, e.type, e.year, e.text) for e in twin.events],
        "history is not deterministic",
    )

    dangling = []
    for ev in world.events:
        for key, eid in ev.refs.items():
            if key not in LINKABLE_KEYS:
                continue
            if world.get(KEY_TO_KIND[key], eid) is None:
                dangling.append((ev.id, key, eid))
    c.check(
        "every event cross-reference resolves to a real entity",
        not dangling,
        f"dangling refs: {dangling[:3]}",
    )
    c.check(
        "every event has non-empty narrative text and a known era",
        all(ev.text.strip() and world.get("era", ev.era_id) is not None
            for ev in world.events),
        "empty text or unknown era",
    )

    myth_start = world.eras[1].start
    c.check(
        "the mythic prologue lands in the dawn era",
        any(ev.year < myth_start and ev.type in ("tower_activated", "dragon_war")
            for ev in world.events),
        "no dawn-era prologue event",
    )

    ages = world.ages
    contiguous = all(ages[i].end == ages[i + 1].start for i in range(len(ages) - 1))
    aged = sum(len(a.event_ids) for a in ages)
    expected = sum(1 for e in world.events if e.year >= myth_start)
    c.check(
        "ages are contiguous and cover the post-dawn events",
        contiguous and ages[0].start == myth_start and aged == expected,
        f"contiguous={contiguous} covered={aged} expected={expected}",
    )
    c.check(
        "age event ids all resolve",
        all(world.get("event", eid) is not None
            for age in ages for eid in age.event_ids),
        "age references a missing event",
    )
    c.check(
        "event pages render the stored narrative text",
        mods["entry_page"](world, "event", world.events[0].id)["description"]
        == world.events[0].text,
        "event page text differs",
    )
    return world


def check_serialization(c: Checker, mods: dict, world) -> None:
    """World JSON and save slots must round trip losslessly."""
    c.section("serialization")
    WorldModel = mods["WorldModel"]
    SaveManager = mods["SaveManager"]
    PlaySaveManager = mods["PlaySaveManager"]

    payload = world.to_json(indent=1, ensure_ascii=False)
    back = WorldModel.from_json(payload)
    c.check(
        "WorldModel JSON round trip keeps every collection",
        back.seed == world.seed and back.title == world.title
        and (len(back.eras), len(back.regions), len(back.sites), len(back.figures),
             len(back.factions), len(back.artifacts), len(back.events), len(back.ages))
        == (len(world.eras), len(world.regions), len(world.sites), len(world.figures),
            len(world.factions), len(world.artifacts), len(world.events), len(world.ages)),
        "collection sizes changed across JSON",
    )
    c.check(
        "reloaded world rebuilds its indexes",
        back.get("figure", world.figures[0].id) is not None
        and back.get("event", world.events[-1].id) is not None,
        "indexes empty after reload",
    )
    c.check(
        "event refs and meta survive the round trip",
        [e.refs for e in back.events] == [e.refs for e in world.events]
        and back.meta.get("race") == world.meta.get("race"),
        "refs/meta changed",
    )

    with tempfile.TemporaryDirectory(prefix="dwarf-scrolls-selfcheck-") as tmpdir:
        saves = SaveManager(save_dir=tmpdir)
        c.check("save() writes a slot", saves.save(world, slot=3) is True)
        c.check(
            "list_saves sees the written slot",
            [p.name for p in saves.list_saves()] == ["scroll_03.json"],
            f"got {[p.name for p in saves.list_saves()]}",
        )
        loaded = saves.load(3)
        c.check(
            "load(slot) restores the chronicle",
            loaded is not None and len(loaded.events) == len(world.events)
            and len(loaded.figures) == len(world.figures)
            and loaded.seed == world.seed,
            "loaded world differs",
        )
        c.check(
            "load_latest and has_saves agree with the slot",
            saves.has_saves() and saves.load_latest() is not None,
            "latest save not found",
        )

        play = PlaySaveManager(save_dir=tmpdir)
        snapshot = {"seed": 7, "turn": 12, "log": ["moved"]}
        play.save(snapshot)
        c.check(
            "play-mode snapshot round trips and clears",
            play.load() == snapshot and play.has_save()
            and play.clear() is True and play.load() is None,
            "play save/clear failed",
        )


def check_views(c: Checker, mods: dict, world) -> None:
    """The shared Legends view must build pages and navigate correctly."""
    c.section("legends views")
    LegendsReader = mods["LegendsReader"]
    collect_links = mods["collect_links"]
    build_list = mods["build_list"]
    build_map = mods["build_map"]
    MAP_GRID = mods["MAP_GRID"]

    reader = LegendsReader(world)
    landing_links = collect_links(reader.view)
    c.check(
        "landing page lists every category plus the map",
        ("category", "figure") in landing_links
        and ("category", "event") in landing_links
        and ("map", "root") in landing_links
        and len(reader.view.lines) > 5,
        f"links={len(landing_links)}",
    )

    reader.navigate(("category", "figure"))
    figure_links = [link for link in collect_links(reader.view) if link[0] == "figure"]
    c.check(
        "navigating to a category lists its entries as links",
        len(figure_links) == len(world.figures)
        and reader.view.title
        and len(reader.stack) == 1,
        f"links={len(figure_links)} figures={len(world.figures)}",
    )

    target = world.figures[0]
    reader.navigate(("figure", target.id))
    page = mods["entry_page"](world, "figure", target.id)
    first_body = page["description"].split("\n")[0][:12]
    c.check(
        "entry page keeps the figure title and body",
        reader.view.title == page["title"] and target.name in reader.view.title
        and len(reader.view.lines) > 3
        and any(first_body in sp.text for line in reader.view.lines for sp in line),
        f"title={reader.view.title!r} page={page['title']!r}",
    )

    reader.back()
    c.check(
        "back() restores the previous list view",
        len(reader.stack) == 1 and len(reader.view.lines) > 3,
        f"stack={len(reader.stack)}",
    )
    reader.home()
    c.check(
        "home() resets to the landing page",
        reader.stack == [] and collect_links(reader.view) == landing_links,
        "home did not restore the landing page",
    )

    map_view = build_map(world)
    map_links = collect_links(map_view)
    region_ids = {r.id for r in world.regions}
    c.check(
        "the map grid is an engine MapData of the expected shape",
        map_view.map_data is not None
        and map_view.map_data.rows == len(MAP_GRID)
        and map_view.map_rows == len(MAP_GRID)
        and map_view.map_row_end - map_view.map_row_start == len(MAP_GRID)
        and all(len(row) == map_view.map_data.cols for row in map_view.map_data.grid),
        f"rows={getattr(map_view.map_data, 'rows', None)}",
    )
    c.check(
        "every map tile links to an existing province",
        ("region", "skyrim") in map_links
        and all(link[1] in region_ids for link in map_links if link[0] == "region")
        and {link[1] for link in map_links if link[0] == "region"} == region_ids,
        f"map links={map_links}",
    )

    c.check(
        "a category view exposes ids that open as entries",
        all(mods["entry_page"](world, kind, eid) is not None
            for kind, eid in collect_links(build_list(world, "faction"))[:5]),
        "faction list link is not openable",
    )


def main() -> int:
    c = Checker()
    try:
        # Side-effect import: makes the inlined allin_engine resolve first,
        # exactly like main.py does.
        import dwarf_scrolls.core.engine_bootstrap  # noqa: F401
        from dwarf_scrolls.core.history_gen import HistoryGenerator
        from dwarf_scrolls.core.legends import (
            KEY_TO_KIND, LINKABLE_KEYS, WorldModel, entry_page,
        )
        from dwarf_scrolls.core.save_manager import PlaySaveManager, SaveManager
        from dwarf_scrolls.core.world_gen import WorldGenerator
        from dwarf_scrolls.game.legends_view import (
            MAP_GRID, LegendsReader, build_list, build_map, collect_links,
        )

        mods = {
            "HistoryGenerator": HistoryGenerator,
            "WorldModel": WorldModel,
            "SaveManager": SaveManager,
            "PlaySaveManager": PlaySaveManager,
            "WorldGenerator": WorldGenerator,
            "LegendsReader": LegendsReader,
            "build_map": build_map,
            "build_list": build_list,
            "collect_links": collect_links,
            "entry_page": entry_page,
            "MAP_GRID": MAP_GRID,
            "KEY_TO_KIND": KEY_TO_KIND,
            "LINKABLE_KEYS": LINKABLE_KEYS,
        }

        world = check_world(c, mods)
        twin = WorldGenerator(seed=7).generate()
        check_history(c, mods, world, twin)
        check_serialization(c, mods, world)
        check_views(c, mods, world)
    except Exception as exc:  # noqa: BLE001 - report any crash as a failure
        print(f"FAIL unexpected {type(exc).__name__}: {exc}")
        return 1

    if c.failures:
        print(f"FAIL {len(c.failures)} check(s) failed: {c.failures[0]}")
        return 1

    print(
        f"selfcheck ok: {len(c.passed)} checks - seeded TES world generation, "
        "deterministic history + cross-reference/age integrity, world JSON and save-slot "
        "round trip, Legends view/reader navigation and map"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
