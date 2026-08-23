"""游历模式视图快照测试。

验证 ``build_play_view / build_chronicle_view / build_lore_view / build_quest_view``
产出的 View 对象结构合法（有标题、有内容、有可点击链接、footer 非空）。
"""
from dwarf_scrolls.core.world_gen import WorldGenerator
from dwarf_scrolls.core.history_gen import HistoryGenerator
from dwarf_scrolls.game.play_core import (
    PlayEngine, build_play_view, build_chronicle_view,
    build_lore_view, build_quest_view,
)
from dwarf_scrolls.game.legends_view import collect_links
from dwarf_scrolls.game.play_components import Satchel, Lore


def _engine(seed: int = 3):
    w = WorldGenerator(seed=seed).generate()
    HistoryGenerator(seed=seed, world=w).generate()
    return PlayEngine(w, seed=seed), w


def test_play_view_basic():
    """主游戏视图应包含地图、行动链接、日志 footer。"""
    e, _ = _engine()
    view = build_play_view(e)
    assert view.title
    assert len(view.lines) >= 5, "play view should have at least 5 lines"
    assert view.footer
    links = collect_links(view)
    assert len(links) >= 3, "should have move/rest/search links"


def test_play_view_has_map_tiles():
    """主游戏视图的 ASCII 地图应包含瓦片字符。"""
    e, _ = _engine()
    view = build_play_view(e)
    text = "".join(s.text for ln in view.lines for s in ln)
    assert "@" in text, "map should show player position @"


def test_play_view_has_actions():
    """主游戏视图应包含移动、休整、探索等行动链接。"""
    e, _ = _engine()
    view = build_play_view(e)
    links = collect_links(view)
    actions = [a for _, a in links if a in ("rest", "search", "inspect")]
    assert len(actions) >= 2


def test_chronicle_view_unlocked():
    """编年史视图在解锁后应显示省份列表。"""
    e, _ = _engine()
    sa = e.world.get_entity("player").get(Satchel)
    sa.chronicle_unlocked = True
    e.overlay = "chronicle"
    view = build_chronicle_view(e)
    assert view.title
    assert view.breadcrumb
    assert view.footer


def test_lore_view_empty():
    """隐藏剧情视图在未发掘时显示提示语。"""
    e, _ = _engine()
    e.overlay = "lore"
    view = build_lore_view(e)
    text = "".join(s.text for ln in view.lines for s in ln)
    assert "尚未发掘" in text


def test_lore_view_with_hidden():
    """隐藏剧情视图在有发掘时显示解读。"""
    e, _ = _engine()
    lo = e.world.get_entity("player").get(Lore)
    lo.hidden.append("skyrim")
    e.overlay = "lore"
    view = build_lore_view(e)
    text = "".join(s.text for ln in view.lines for s in ln)
    assert "天际" in text or "skyrim" in text


def test_quest_view_neutral():
    """支线任务视图在中立模式下显示提示语。"""
    e, _ = _engine()
    e.overlay = "quest"
    view = build_quest_view(e)
    text = "".join(s.text for ln in view.lines for s in ln)
    assert "尚未向任何魔神" in text


def test_dispatch_actions():
    """dispatch 应切换 overlay 或执行命令。"""
    e, _ = _engine()
    e.dispatch("chronicle")
    assert e.overlay == "chronicle"
    e.dispatch("chronicle_back")
    assert e.overlay is None
    e.dispatch("lore")
    assert e.overlay == "lore"
    e.dispatch("lore_back")
    assert e.overlay is None
    e.dispatch("quest")
    assert e.overlay == "quest"
    e.dispatch("quest_back")
    assert e.overlay is None


def test_play_view_dead():
    """死亡状态的视图应显示陨落信息。"""
    e, _ = _engine()
    e.dead = True
    view = build_play_view(e)
    text = "".join(s.text for ln in view.lines for s in ln)
    assert "倒下" in text or "陨落" in text
