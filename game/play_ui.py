"""游历模式 —— UI 渲染函数。

将 ECS 游历世界渲染为矮人要塞风格的 View 对象：
- build_play_view: 主游戏视图（地图、行动、日志）
- build_chronicle_view: 编年史复原视图
- build_lore_view: 隐藏剧情视图（分歧解读）
- build_quest_view: 魔神支线任务视图
"""
from __future__ import annotations

from typing import List, Tuple

from dwarf_scrolls.game.legends_view import (
    View, Span,
    LINK_COLOR, SUB_COLOR, DIM, WHITE, MAGENTA,
)
from dwarf_scrolls.game.play_data import (
    _ALIGN_CN, _ALLEGIANCE_CN,
    PROVINCE_COUNT,
    DAEDRIC_PRINCES, HIDDEN_LORE,
    _epilogue_for, _lore_reading, _branch_label,
)
from dwarf_scrolls.game.play_components import (
    Position, Health, Clock, Allegiance, Gear, Satchel,
    Lore, PlayLog, Quests,
)
from dwarf_scrolls.game.legends_view import MAP_GRID, MAP_CHAR_TO_PROV  # 地图渲染


def build_play_view(engine) -> View:
    """把 ECS 游历世界渲染为矮人要塞风格的 View。"""
    # 延迟导入避免循环
    from dwarf_scrolls.game.play_engine import PlayEngine
    engine: PlayEngine = engine

    if engine.overlay == "chronicle":
        return build_chronicle_view(engine)
    if engine.overlay == "lore":
        return build_lore_view(engine)
    if engine.overlay == "quest":
        return build_quest_view(engine)

    p = engine.world.get_entity("player")
    pos = p.get(Position)
    hp = p.get(Health)
    clk = p.get(Clock)
    al = p.get(Allegiance)
    gear = p.get(Gear)
    sat = p.get(Satchel)
    lore = p.get(Lore)
    log = p.get(PlayLog)
    reg = engine.current_region()

    v = View(title="游历模式 · 泰姆瑞尔 (引擎 ECS)")
    v.breadcrumb = ["卷轴庠", "游历模式"]
    if engine.resumed:
        v.breadcrumb.append("续局")

    if engine.dead:
        v.add_line(Span("☠ 你已倒下", "bright_red"))
        v.add_line(Span("返回落地页，重新开启一段旅程。", DIM))
        v.footer = "你已陨落 · 返回 / 落地页"
        return v

    v.add_line(Span(f"位置：{reg.name}  ", SUB_COLOR),
               Span(f"生命 {hp.value}/{hp.max_value}  ", "bright_red"),
               Span(f"第 {clk.day} 天", "bright_yellow"))
    vow_label = _ALLEGIANCE_CN.get(al.kind, al.kind)
    if al.kind == "daedric" and al.prince:
        pname = DAEDRIC_PRINCES.get(al.prince, {}).get("name", al.prince)
        vow_label = f"魔神·{pname}"
    branch = _epilogue_for(al)[0]
    header_spans = [
        Span(f"誓言：{vow_label}  ", MAGENTA),
        Span(f"武器 {gear.weapon}(攻{gear.attack})  ", "bright_cyan"),
        Span(f"卷轴碎片 {len(sat.fragments)}/{PROVINCE_COUNT}", "bright_magenta"),
        Span(f"  隐秘 {len(lore.hidden)}/{PROVINCE_COUNT}", "bright_green"),
    ]
    if al.kind != "none":
        header_spans.append(Span(f"  主线 {branch}", "bright_yellow"))
    v.add_line(*header_spans)
    v.add_line(Span(""))

    # ASCII 地图
    v.add_line(Span("─ 地图 ─", SUB_COLOR))
    adj = set(engine.adjacent_regions())
    for row in MAP_GRID:
        spans: List[Span] = []
        for ch in row:
            pid = MAP_CHAR_TO_PROV.get(ch)
            if pid is None:
                spans.append(Span(ch + " ", DIM))
            elif pid == pos.province:
                spans.append(Span("@ ", "bright_yellow"))
            elif pid in adj and engine.passable(pid):
                spans.append(Span(ch + " ", "bright_black", link=("play", f"move:{pid}")))
            elif pid in adj and not engine.passable(pid):
                spans.append(Span(ch + " ", "red"))
            else:
                spans.append(Span(ch + " ", "bright_black"))
        v.add_line(*spans)
    v.add_line(Span(""))

    # 行动
    v.add_line(Span("─ 行动 ─", SUB_COLOR))
    for pid in engine.adjacent_regions():
        r = engine.model.get("region", pid)
        color = {"good": "cyan", "evil": "red", "neutral": "green"}.get(r.alignment, "white")
        if not engine.passable(pid):
            v.add_line(Span(f"  ▸ {r.name}", DIM),
                       Span(f"   {_ALIGN_CN.get(r.alignment, r.alignment)} · 势力封锁", "red"))
        else:
            v.add_line(Span(f"  ▸ 移动到 {r.name}", LINK_COLOR, link=("play", f"move:{pid}")),
                       Span(f"   {_ALIGN_CN.get(r.alignment, r.alignment)}", color))
    v.add_line(Span("  ▸ 休整", LINK_COLOR, link=("play", "rest")))
    v.add_line(Span("  ▸ 探索", LINK_COLOR, link=("play", "search")))
    v.add_line(Span("  ▸ 查看当前省份", LINK_COLOR, link=("play", "inspect")))
    if al.kind != "aedric":
        v.add_line(Span("  ▸ 向圣灵(Aedra)宣誓", LINK_COLOR, link=("play", "vow:aedric")))
    v.add_line(Span("  ─ 魔神(Daedra)分支 ─", DIM))
    for pid, pr in DAEDRIC_PRINCES.items():
        if al.kind == "daedric" and al.prince == pid:
            v.add_line(Span(f"    已献誓于 {pr['name']}（{pr['title']}）", "red"))
        else:
            tag = "改献誓于" if al.kind == "daedric" else "向"
            v.add_line(Span(f"    ▸ {tag}{pr['name']}（{pr['title']}）", LINK_COLOR,
                           link=("play", f"vow:daedric:{pid}")))
    if al.kind != "none":
        v.add_line(Span("  ▸ 收回誓言（中立）", LINK_COLOR, link=("play", "vow:none")))
    if al.kind == "daedric" and al.prince:
        qs = p.get(Quests).quests.get(al.prince)
        if qs and qs.get("started"):
            q = DAEDRIC_PRINCES[al.prince]["quest"]
            if qs.get("done"):
                v.add_line(Span(f"  支线（{q['name']}）已达成 ✦", "bright_green"))
            else:
                done_n = sum(1 for s in qs["steps"] if s)
                v.add_line(Span(f"  支线（{q['name']}）{done_n}/{len(qs['steps'])}  ", "bright_cyan"),
                           Span("▸ 详情", LINK_COLOR, link=("play", "quest")))
    if al.kind == "daedric":
        v.add_line(Span("  ▸ 查看支线任务", LINK_COLOR, link=("play", "quest")))
    if sat.chronicle_unlocked:
        v.add_line(Span("  ▸ 查看复原的编年史", LINK_COLOR, link=("play", "chronicle")))
    if lore.revealed or lore.hidden:
        v.add_line(Span("  ▸ 查看隐藏剧情", LINK_COLOR, link=("play", "lore")))
    v.add_line(Span(""))

    # 日志
    v.add_line(Span("─ 日志 ─", SUB_COLOR))
    for entry in log.entries[-8:]:
        for seg in _wrap(entry, 62):
            v.add_line(Span("  " + seg, WHITE))

    v.footer = "点击省份或行动超链接游玩 · 返回 / 落地页"
    return v


def build_chronicle_view(engine) -> View:
    """九省卷轴碎片聚齐后复原的 kalpic 编年史视图。"""
    p = engine.world.get_entity("player")
    sat = p.get(Satchel)
    v = View(title="复原的编年史 · kalpic 全卷")
    v.breadcrumb = ["卷轴庠", "游历模式", "编年史"]
    v.add_line(Span("九省卷轴碎片已在你掌中聚齐。先祖飞蛾之仪下，kalpic 史册的扉页为你展开：", DIM))
    v.add_line(Span(""))
    v.add_line(Span(f"  你以飞蛾祭司之身，踏遍 {len(sat.fragments)} 省，录下泰姆瑞尔既往与未然。", WHITE))
    v.add_line(Span(""))
    v.add_line(Span("─ 已复原省份 ─", SUB_COLOR))
    for pid in sat.fragments:
        reg = engine.model.get("region", pid)
        color = {"good": "cyan", "evil": "red", "neutral": "green"}.get(reg.alignment, "white")
        v.add_line(Span(f"  ▸ {reg.name}", color),
                   Span(f"   {_ALIGN_CN.get(reg.alignment, reg.alignment)}", DIM))
    v.add_line(Span(""))
    v.add_line(Span("  返回游历", LINK_COLOR, link=("play", "chronicle_back")))
    v.footer = "返回游历"
    return v


def build_lore_view(engine) -> View:
    """九省隐秘卷轴聚齐后揭示的 kalpic 隐藏剧情视图（终章依誓言分流）。"""
    p = engine.world.get_entity("player")
    lore = p.get(Lore)
    al = p.get(Allegiance)
    branch, epilogue = _epilogue_for(al)
    v = View(title=f"隐藏剧情 · {branch}")
    v.breadcrumb = ["卷轴庠", "游历模式", "隐藏剧情", branch]
    if not lore.hidden:
        v.add_line(Span("你尚未发掘任何隐藏卷轴。在各省「探索」以揭开 kalpic 的隐秘。", DIM))
    else:
        v.add_line(Span(f"已发掘 {len(lore.hidden)}/{PROVINCE_COUNT} 段隐秘卷轴。", WHITE))
        v.add_line(Span(""))
        for pid in lore.hidden:
            reg = engine.model.get("region", pid)
            color = {"good": "cyan", "evil": "red", "neutral": "green"}.get(reg.alignment, "white")
            snippet = HIDDEN_LORE.get(pid, "")
            v.add_line(Span(f"  ▸ {reg.name}", color))
            for seg in _wrap(snippet, 56):
                v.add_line(Span("      " + seg, DIM))
            reading = _lore_reading(pid, al)
            if reading:
                label = _branch_label(al)
                v.add_line(Span(f"      → {label}解读：", "bright_yellow"))
                for seg in _wrap(reading, 52):
                    v.add_line(Span("        " + seg, "bright_white"))
        if lore.revealed:
            v.add_line(Span(""))
            v.add_line(Span(f"─ kalpic 终章 · {branch} ─", "bright_yellow"))
            for seg in _wrap(epilogue, 56):
                v.add_line(Span("  " + seg, "bright_white"))
    v.add_line(Span(""))
    v.add_line(Span("  返回游历", LINK_COLOR, link=("play", "lore_back")))
    v.footer = "返回游历"
    return v


def build_quest_view(engine) -> View:
    """五大魔神王子独立支线任务一览（仅魔神系可见）。"""
    p = engine.world.get_entity("player")
    al = p.get(Allegiance)
    quests = p.get(Quests).quests
    v = View(title="支线任务 · 魔神王子")
    v.breadcrumb = ["卷轴庠", "游历模式", "支线任务"]
    if al.kind != "daedric":
        v.add_line(Span("你尚未向任何魔神王子献誓。", DIM))
        v.add_line(Span("向某位魔神（Daedra）献誓，即可开启其独立支线任务。", DIM))
    else:
        pr = DAEDRIC_PRINCES.get(al.prince, {})
        v.add_line(Span(f"当前献誓：{pr.get('name', al.prince)}（{pr.get('title', '')}）", MAGENTA))
        v.add_line(Span(""))
    for pid, pr in DAEDRIC_PRINCES.items():
        q = pr.get("quest")
        st = quests.get(pid)
        active = (al.kind == "daedric" and al.prince == pid)
        head_color = "bright_cyan" if active else "white"
        if st is None:
            status = "未开启"
        elif st.get("done"):
            status = "已达成"
        else:
            status = "进行中"
        v.add_line(Span(f"  ▸ {pr['name']} — {q['name']}（{status}）", head_color))
        v.add_line(Span(f"      {q['brief']}", DIM))
        if st is not None and not st.get("done"):
            for i, step in enumerate(q["steps"]):
                mark = "✔" if st["steps"][i] else "○"
                prov = step["prov"]
                reg = engine.model.get("region", prov)
                label = {"visit": f"抵达 {reg.name}",
                         "lore": f"发掘 {reg.name} 的隐秘卷轴"}.get(step["type"], step["type"])
                c = "bright_green" if st["steps"][i] else "white"
                v.add_line(Span(f"        {mark} {label}", c))
        elif st is not None and st.get("done"):
            rw = q.get("reward", {})
            v.add_line(Span(f"      奖励：{rw.get('name', '')} — {rw.get('text', '')}", "bright_green"))
    v.add_line(Span(""))
    v.add_line(Span("  返回游历", LINK_COLOR, link=("play", "quest_back")))
    v.footer = "返回游历"
    return v


def _wrap(text: str, width: int) -> List[str]:
    if not text:
        return [""]
    out: List[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if len(cur) >= width:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def dispatch_play_action(engine, action: str) -> None:
    """兼容旧 import 的便捷函数。"""
    engine.dispatch(action)
