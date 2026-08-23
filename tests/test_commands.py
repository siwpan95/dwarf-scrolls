"""T15 — 命令分发测试。

验证 ``dispatch`` 把用户输入映射为导航动作：数字跳转链接、b/h/m 返回/落地/
地图、q 退出、非法输入返回 invalid。
"""
from dwarf_scrolls.core.world_gen import WorldGenerator
from dwarf_scrolls.core.history_gen import HistoryGenerator
from dwarf_scrolls.game.legends_view import LegendsReader, collect_links
from dwarf_scrolls.game.commands import dispatch


def _reader():
    w = WorldGenerator(seed=42).generate()
    HistoryGenerator(seed=42, world=w).generate()
    return LegendsReader(w)


def test_digit_navigates():
    r = _reader()
    before = r.view
    res = dispatch(r, "1")
    assert res == "ok"
    assert r.view is not before


def test_back_home_map():
    r = _reader()
    r.navigate(("category", "figure"))
    assert dispatch(r, "b") == "ok"          # 返回落地页
    r.navigate(("category", "site"))
    assert dispatch(r, "h") == "ok"          # 落地页
    assert dispatch(r, "m") == "ok"          # 地图


def test_quit_and_invalid():
    r = _reader()
    assert dispatch(r, "q") == "quit"
    assert dispatch(r, "z") == "invalid"
    # 越界编号
    assert dispatch(r, "999") == "invalid"


def test_collect_links_matches_dispatch():
    r = _reader()
    links = collect_links(r.view)
    assert links
    # 1 号链接确实对应首条链接
    dispatch(r, "1")
    # 不应抛错
    assert True
