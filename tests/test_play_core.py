"""游历模式 ECS 测试 —— 验证 ``PlayEngine`` 长在 allin_engine 的
ECS（World/Entity/Component/System）+ 事件总线（EventBus）+ 固定步长主循环
（FixedTimestepLoop）之上，而非另写一套状态机。

覆盖：
- 引擎装配（GameEngine 的 world / bus / loop 就绪，玩家实体带 6 个组件）；
- 移动 / 休整 / 查看 的命令语义与 HP / 天数结算；
- 事件总线发出 PLAYER_MOVED / MOB_SPAWNED / PLAYER_DIED；
- FixedTimestepLoop.advance 真正驱动 world.update（固定步长切分）；
- 死亡判定的两条路径（hp 归零 / 进入邪恶省受创致死）；
- build_play_view 产出合法 View（仅相邻省可点击移动）；
- dispatch_play_action 兼容函数 与 PlayState 别名。
"""
import itertools

from allin_engine import EventTypes

from dwarf_scrolls.core.world_gen import WorldGenerator
from dwarf_scrolls.core.history_gen import HistoryGenerator
from dwarf_scrolls.core.save_manager import PlaySaveManager
from dwarf_scrolls.game.play_core import (
    PlayEngine, PlayState, build_play_view, build_lore_view, build_quest_view,
    dispatch_play_action,
    ADJACENCY, MAP_CHAR_TO_PROV, PROVINCE_COUNT,
    DAEDRIC_PRINCES, HIDDEN_LORE, HIDDEN_LORE_READING,
    HIDDEN_CHAPTER, AEDRIC_EPILOGUE, PRINCE_EPILOGUE,
    _epilogue_for, _lore_reading, _branch_label, _branch_key,
    Position, Health, Clock, Alignment, Allegiance, Gear, Satchel, Pack,
    Lore, Quests, PlayLog, CommandQueue,
)
from dwarf_scrolls.game.legends_view import collect_links


def _engine(seed: int = 7):
    w = WorldGenerator(seed=seed).generate()
    HistoryGenerator(seed=seed, world=w).generate()
    return PlayEngine(w, seed=seed), w


def _player(e: PlayEngine):
    return e.world.get_entity("player")


def _hp(e: PlayEngine) -> Health:
    return _player(e).get(Health)


def _clk(e: PlayEngine) -> Clock:
    return _player(e).get(Clock)


def _pos(e: PlayEngine) -> Position:
    return _player(e).get(Position)


def _log(e: PlayEngine) -> PlayLog:
    return _player(e).get(PlayLog)


def test_engine_assembly():
    e, _ = _engine()
    # GameEngine 装配了核心层：ECS World + EventBus + FixedTimestepLoop
    assert e.world is not None
    assert e.bus is not None
    assert e.engine.loop is not None
    # 玩家实体带全部 6 个组件
    p = _player(e)
    for comp in (Position, Health, Clock, Alignment, PlayLog, CommandQueue):
        assert p.get(comp) is not None


def test_adjacency_built():
    assert "cyrodiil" in ADJACENCY
    assert len(ADJACENCY["cyrodiil"]) >= 2


def test_move_to_adjacent():
    e, w = _engine()
    target = e.adjacent_regions()[0]
    before_day = _clk(e).day
    cnt = {"moved": 0}
    e.bus.subscribe(EventTypes.PLAYER_MOVED, lambda d: cnt.__setitem__("moved", cnt["moved"] + 1))
    ok = e.move_to(target)
    assert ok
    assert _pos(e).province == target
    assert _clk(e).day == before_day + 1
    assert cnt["moved"] == 1  # 经 EventBus 发出 PLAYER_MOVED


def test_move_to_nonadjacent_fails():
    e, w = _engine()
    ok = e.move_to("nonexistent_province")
    assert ok is False
    assert _pos(e).province == "cyrodiil"
    assert "无法直接抵达" in _log(e).entries[-1]


def test_rest_heals():
    e, w = _engine()
    _hp(e).value = 10
    before = _clk(e).day
    e.rest()
    assert _hp(e).value > 10
    assert _clk(e).day == before + 1


def test_inspect_logs():
    e, w = _engine()
    before = len(_log(e).entries)
    e.inspect()
    assert len(_log(e).entries) == before + 1


def test_eventbus_mob_spawned_on_evil_enter():
    # 找一个存在 evil 相邻省的 seed
    for sd in itertools.count(1):
        e, w = _engine(sd)
        evil = [pid for pid in e.adjacent_regions() if w.get("region", pid).alignment == "evil"]
        if evil:
            _hp(e).value = 1  # 进入邪恶省必受创致死
            cnt = {"mob": 0, "dead": 0}
            e.bus.subscribe(EventTypes.MOB_SPAWNED, lambda d: cnt.__setitem__("mob", cnt["mob"] + 1))
            e.bus.subscribe(EventTypes.PLAYER_DIED, lambda d: cnt.__setitem__("dead", cnt["dead"] + 1))
            e.move_to(evil[0])
            assert cnt["mob"] >= 1           # EncounterSystem 监听 PLAYER_MOVED -> MOB_SPAWNED
            assert e.dead                    # hp 归零 -> PLAYER_DIED
            break


def test_death_via_hp_zero():
    e, w = _engine()
    cnt = {"dead": 0}
    e.bus.subscribe(EventTypes.PLAYER_DIED, lambda d: cnt.__setitem__("dead", cnt["dead"] + 1))
    _hp(e).value = 0
    e.tick(1.0)  # RestSystem 立即判定死亡（独立于时间流逝）
    assert e.dead
    assert cnt["dead"] == 1
    # 死亡后行动被忽略
    day = _clk(e).day
    e.move_to(e.adjacent_regions()[0])
    assert _clk(e).day == day


def test_advance_drives_fixed_timestep_loop():
    e, w = _engine()
    steps0 = e.engine.loop.stats.fixed_steps
    e.advance(0.25)  # == max_frame_time，不触发钳制
    assert e.engine.loop.stats.fixed_steps > steps0  # 主循环确实切分了固定步
    # 四次 advance(0.25) 累积 1.0 模拟时间 -> 天数 +1（时间尺度统一）
    day0 = _clk(e).day
    for _ in range(4):
        e.advance(0.25)
    assert _clk(e).day == day0 + 1


def test_build_play_view_ecs():
    e, w = _engine()
    v = build_play_view(e)
    assert v.title
    assert v.lines
    # 仅相邻省带 move 链接（非相邻省仅视觉展示，不可点击）
    links = collect_links(v)
    move_pids = {l[1].split(":", 1)[1] for l in links
                 if l[0] == "play" and l[1].startswith("move:")}
    assert move_pids <= set(e.adjacent_regions())
    # 当前省 @ 不带 move 链接
    assert ("play", "move:" + _pos(e).province) not in links


def test_dispatch_play_action_compat():
    e, w = _engine()
    before = _clk(e).day
    dispatch_play_action(e, "move:" + e.adjacent_regions()[0])
    assert _clk(e).day == before + 1


def test_playstate_alias():
    assert PlayState is PlayEngine


# ═══════════════════════════════════════════════════════════════════════════
# 特性 1：战斗深化（CombatSystem）
# ═══════════════════════════════════════════════════════════════════════════

def test_combat_happens_in_evil_province():
    e, w = _engine()
    # 晨风为邪恶省且邻接赛瑞迪尔（起点），非魔神系玩家进入必触发战斗
    cnt = {"combat": 0, "mob": 0, "defeated": 0, "dead": 0}
    e.bus.subscribe(EventTypes.COMBAT_START, lambda d: cnt.__setitem__("combat", cnt["combat"] + 1))
    e.bus.subscribe(EventTypes.MOB_SPAWNED, lambda d: cnt.__setitem__("mob", cnt["mob"] + 1))
    e.bus.subscribe(EventTypes.MOB_DEFEATED, lambda d: cnt.__setitem__("defeated", cnt["defeated"] + 1))
    e.bus.subscribe(EventTypes.PLAYER_DIED, lambda d: cnt.__setitem__("dead", cnt["dead"] + 1))
    _hp(e).value = 30  # 拉满血保证打赢，专测战斗+掉落
    ok = e.move_to("morrowind")
    assert ok
    assert cnt["combat"] >= 1        # CombatSystem 发起战斗
    assert cnt["mob"] >= 1           # EncounterSystem 先发 MOB_SPAWNED
    assert cnt["defeated"] >= 1      # 胜利 -> MOB_DEFEATED
    # 战利品进入背包、武器攻击可能提升
    assert _player(e).get(Pack).items
    assert _player(e).get(Gear).attack >= 3


def test_combat_lethal_when_weak():
    e, w = _engine()
    _hp(e).value = 1
    cnt = {"dead": 0}
    e.bus.subscribe(EventTypes.PLAYER_DIED, lambda d: cnt.__setitem__("dead", cnt["dead"] + 1))
    e.move_to("morrowind")
    assert e.dead
    assert cnt["dead"] >= 1


def test_daedric_immune_in_evil_no_combat():
    e, w = _engine()
    e.vow("daedric")
    cnt = {"combat": 0, "mob": 0}
    e.bus.subscribe(EventTypes.COMBAT_START, lambda d: cnt.__setitem__("combat", cnt["combat"] + 1))
    e.bus.subscribe(EventTypes.MOB_SPAWNED, lambda d: cnt.__setitem__("mob", cnt["mob"] + 1))
    hp0 = _hp(e).value
    e.move_to("morrowind")
    assert cnt["combat"] == 0       # 魔神系免疫，不发起战斗
    assert cnt["mob"] == 0          # 也不发 MOB_SPAWNED
    assert _hp(e).value >= hp0      # 免疫不掉血（可能搜得治愈药剂回血）
    assert "morrowind" in _player(e).get(Satchel).fragments


# ═══════════════════════════════════════════════════════════════════════════
# 特性 2：探索 / 任务（ExplorationSystem）
# ═══════════════════════════════════════════════════════════════════════════

def test_entering_province_collects_fragment():
    e, w = _engine()
    assert "morrowind" not in _player(e).get(Satchel).fragments
    e.move_to("morrowind")
    assert "morrowind" in _player(e).get(Satchel).fragments


def test_all_fragments_unlock_chronicle():
    e, w = _engine()
    sat = _player(e).get(Satchel)
    cnt = {"shard": 0}
    e.bus.subscribe(EventTypes.SHARD_FOUND, lambda d: cnt.__setitem__("shard", cnt["shard"] + 1))
    for pid in MAP_CHAR_TO_PROV.values():
        e.exploration.on_moved({"to": pid})
    assert set(sat.fragments) == set(MAP_CHAR_TO_PROV.values())
    assert sat.chronicle_unlocked
    assert cnt["shard"] == PROVINCE_COUNT
    # 编年史视图可渲染
    e.dispatch("chronicle")
    v = build_play_view(e)
    assert "编年史" in v.title
    e.dispatch("chronicle_back")
    assert e.overlay is None


def test_search_yields_log():
    e, w = _engine()
    before = len(_log(e).entries)
    for _ in range(10):
        e.search()
    assert len(_log(e).entries) > before


# ═══════════════════════════════════════════════════════════════════════════
# 特性 3：势力系统（FactionSystem）
# ═══════════════════════════════════════════════════════════════════════════

def test_aedric_blocks_evil_province():
    e, w = _engine()
    e.vow("aedric")
    assert _player(e).get(Allegiance).kind == "aedric"
    # 晨风（邪恶）邻接却不可通行
    assert "morrowind" in e.adjacent_regions()
    assert e.passable("morrowind") is False
    ok = e.move_to("morrowind")
    assert ok is False
    assert _pos(e).province == "cyrodiil"


def test_daedric_blocks_good_province():
    e, w = _engine()
    e.move_to("skyrim")            # 先到天际（中立，可通行）
    e.vow("daedric")
    # 高岩省（善良）邻接天际，魔神系应被封锁
    assert "high_rock" in e.adjacent_regions()
    assert e.passable("high_rock") is False
    ok = e.move_to("high_rock")
    assert ok is False
    assert _pos(e).province == "skyrim"


def test_neutral_all_passable():
    e, w = _engine()
    for pid in e.adjacent_regions():
        assert e.passable(pid) is True


def test_aedric_heals_more_in_good():
    e, w = _engine()
    e.vow("aedric")                # 起点赛瑞迪尔，直接宣誓圣灵
    _hp(e).value = 10
    # 威木省（善良）邻接赛瑞迪尔，圣灵系进入应治疗且多于基础 1~3
    e.move_to("valenwood")
    assert _hp(e).value > 10 + 2  # 基础 1~3 + 圣灵加成 2（保证多于中立）


# ═══════════════════════════════════════════════════════════════════════════
# 特性 4：游历独立存档（Snapshotable + PlaySaveManager）
# ═══════════════════════════════════════════════════════════════════════════

def test_snapshot_roundtrip_in_memory():
    e, w = _engine()
    e.move_to("morrowind")
    e.vow("aedric")
    e.search()
    snap = e.to_snapshot()
    e2 = PlayEngine.from_snapshot(w, snap)
    assert _pos(e2).province == "morrowind"
    assert _hp(e2).value == _hp(e).value
    assert _player(e2).get(Allegiance).kind == "aedric"
    assert set(_player(e2).get(Satchel).fragments) == set(_player(e).get(Satchel).fragments)
    assert _player(e2).get(Gear).weapon == _player(e).get(Gear).weapon
    assert e2.dead == e.dead
    # rng 状态续上：下一步随机一致
    assert e.rng.random() == e2.rng.random()


def test_snapshot_file_roundtrip(tmp_path):
    e, w = _engine()
    e.move_to("morrowind")
    mgr = PlaySaveManager(save_dir=str(tmp_path))
    e.save_to(str(mgr.path))
    assert mgr.has_save()
    e3 = PlayEngine.load_from(w, str(mgr.path))
    assert e3 is not None
    assert _pos(e3).province == "morrowind"
    assert _player(e3).get(Satchel).fragments == _player(e).get(Satchel).fragments
    mgr.clear()
    assert not mgr.has_save()
    assert PlayEngine.load_from(w, str(mgr.path)) is None


def test_loaded_engine_still_playable():
    e, w = _engine()
    e.move_to("morrowind")
    snap = e.to_snapshot()
    e2 = PlayEngine.from_snapshot(w, snap)
    # 续局后系统已重新装配，仍可继续移动
    target = e2.adjacent_regions()[0]
    ok = e2.move_to(target)
    assert ok
    assert _pos(e2).province == target


# ═══════════════════════════════════════════════════════════════════════════
# 修复：邻接对齐（显式 ADJACENCY，贴合 TES 真实地理）
# ═══════════════════════════════════════════════════════════════════════════

def test_adjacency_explicit_geography():
    # hammerfell 不再只连 high_rock（旧去空格压缩导致的列错位 bug）
    assert "hammerfell" in ADJACENCY["skyrim"]
    assert "hammerfell" in ADJACENCY["cyrodiil"]
    # cyrodiil 作为中心省接壤六省
    assert len(ADJACENCY["cyrodiil"]) == 6
    # 图对称 + 全连通
    for a, nbrs in ADJACENCY.items():
        for b in nbrs:
            assert a in ADJACENCY[b]
    allp = set(MAP_CHAR_TO_PROV.values())
    seen = set()
    stack = ["cyrodiil"]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(ADJACENCY[n])
    assert seen == allp


# ═══════════════════════════════════════════════════════════════════════════
# 特性 2 扩展：探索 / 隐藏剧情（Lore）
# ═══════════════════════════════════════════════════════════════════════════

def test_search_discovers_hidden_lore():
    e, w = _engine()
    # 起点赛瑞迪尔，原地探索应发掘其隐藏卷轴
    e.search()
    lore = _player(e).get(Lore)
    assert "cyrodiil" in lore.hidden
    # 同一省再探索不重复收集
    e.search()
    assert lore.hidden.count("cyrodiil") == 1


def test_all_hidden_lore_reveals_chapter():
    e, w = _engine()
    p = _player(e)
    cnt = {"hidden": 0}
    e.bus.subscribe(EventTypes.SHARD_HIDDEN,
                    lambda d: cnt.__setitem__("hidden", cnt["hidden"] + 1))
    for pid in MAP_CHAR_TO_PROV.values():
        p.get(Position).province = pid
        e.exploration.discover_hidden(p)
    lore = p.get(Lore)
    assert set(lore.hidden) == set(MAP_CHAR_TO_PROV.values())
    assert lore.revealed
    assert cnt["hidden"] == PROVINCE_COUNT
    # 隐藏剧情视图可渲染
    e.dispatch("lore")
    v = build_play_view(e)
    assert "隐藏剧情" in v.title
    e.dispatch("lore_back")
    assert e.overlay is None


# ═══════════════════════════════════════════════════════════════════════════
# 特性 3 扩展：势力系统 · 魔神(Daedra)多分支（五大王子）
# ═══════════════════════════════════════════════════════════════════════════

def test_daedric_prince_vow_sets_branch():
    e, w = _engine()
    for pid, pr in DAEDRIC_PRINCES.items():
        e.vow("daedric", pid)
        al = _player(e).get(Allegiance)
        assert al.kind == "daedric"
        assert al.prince == pid
        assert al.faction_id == f"cult_{pid}"
        # 任一魔神分支都封锁善良省
        assert e.passable("high_rock") is False


def test_daedric_prince_combat_resolves():
    # 每个魔神王子下进入邪恶省仍免疫（不发起战斗），且搜得战利品
    for pid in DAEDRIC_PRINCES:
        e, w = _engine()
        e.vow("daedric", pid)
        _hp(e).value = 30
        cnt = {"combat": 0, "mob": 0}
        e.bus.subscribe(EventTypes.COMBAT_START, lambda d: cnt.__setitem__("combat", cnt["combat"] + 1))
        e.bus.subscribe(EventTypes.MOB_SPAWNED, lambda d: cnt.__setitem__("mob", cnt["mob"] + 1))
        e.move_to("morrowind")
        assert cnt["combat"] == 0
        assert cnt["mob"] == 0
        assert _player(e).get(Pack).items  # 免疫时仍搜得战利品


def test_snapshot_roundtrip_includes_lore_and_prince():
    e, w = _engine()
    e.vow("daedric", "dagon")
    e.search()  # 收集当前省隐秘
    snap = e.to_snapshot()
    e2 = PlayEngine.from_snapshot(w, snap)
    al = _player(e2).get(Allegiance)
    assert al.kind == "daedric" and al.prince == "dagon"
    assert _player(e2).get(Lore).hidden == _player(e).get(Lore).hidden
    assert e2.dead == e.dead


# ═══════════════════════════════════════════════════════════════════════════
# 主线分歧：集齐九省隐秘后，kalpic 终章依誓言（圣灵 / 五大魔神 / 中立）分流
# ═══════════════════════════════════════════════════════════════════════════

def _view_text(v) -> str:
    parts = []
    for line in v.lines:
        for span in line:
            parts.append(span.text)
    return "\n".join(parts)


def _reveal_all(e: PlayEngine) -> None:
    p = _player(e)
    p.get(Lore).hidden = list(MAP_CHAR_TO_PROV.values())
    p.get(Lore).revealed = True


def test_epilogue_neutral_default():
    e, w = _engine()
    _reveal_all(e)
    v = build_lore_view(e)
    assert "中立之线" in v.title
    assert HIDDEN_CHAPTER[:14] in _view_text(v)


def test_epilogue_aedric_branch():
    e, w = _engine()
    e.vow("aedric")
    _reveal_all(e)
    v = build_lore_view(e)
    assert "圣灵之线" in v.title
    assert AEDRIC_EPILOGUE[:14] in _view_text(v)


def test_epilogue_daedric_princes_diverge():
    # 每个魔神王子给出各自独立的主线终章
    for pid, pr in DAEDRIC_PRINCES.items():
        e, w = _engine()
        e.vow("daedric", pid)
        _reveal_all(e)
        v = build_lore_view(e)
        assert f"{pr['name']}之线" in v.title
        assert PRINCE_EPILOGUE[pid][:14] in _view_text(v)
    # 不同王子终章文本确实不同（分歧存在）
    e1, _ = _engine(); e1.vow("daedric", "azura")
    e2, _ = _engine(); e2.vow("daedric", "dagon")
    _reveal_all(e1); _reveal_all(e2)
    assert _epilogue_for(_player(e1).get(Allegiance))[1] != \
           _epilogue_for(_player(e2).get(Allegiance))[1]


def test_play_view_header_shows_branch():
    e, w = _engine()
    e.vow("daedric", "sheo")
    v = build_play_view(e)
    assert "谢戈拉思之线" in _view_text(v)  # 头部「主线 谢戈拉思之线」
    # 中立时不显示主线分支标签
    e2, _ = _engine()
    assert "主线" not in _view_text(build_play_view(e2))


# ═══════════════════════════════════════════════════════════════════════════
# 隐秘文本分支解读：九省隐秘卷轴本身也按誓言给出不同「解读」
# ═══════════════════════════════════════════════════════════════════════════

def test_hidden_lore_reading_built():
    for pid in MAP_CHAR_TO_PROV.values():
        assert pid in HIDDEN_LORE_READING
        assert "neutral" in HIDDEN_LORE_READING[pid]

def test_lore_reading_diverges_by_branch():
    al_neutral = Allegiance("none")
    al_aedric = Allegiance("aedric")
    al_azura = Allegiance("daedric", prince="azura")
    # 同一省的解读在不同分支下应不同（分歧存在）
    r_neu = _lore_reading("morrowind", al_neutral)
    r_aed = _lore_reading("morrowind", al_aedric)
    r_azu = _lore_reading("morrowind", al_azura)
    assert r_neu and r_aed and r_azu
    assert r_neu != r_aed or r_neu != r_azu  # 至少有一对不同

def test_branch_label_helpers():
    assert _branch_label(Allegiance("none")) == "中立"
    assert _branch_label(Allegiance("aedric")) == "圣灵"
    assert _branch_label(Allegiance("daedric", prince="azura")) == "阿祖拉"
    assert _branch_key(Allegiance("none")) == "neutral"
    assert _branch_key(Allegiance("aedric")) == "aedric"
    assert _branch_key(Allegiance("daedric", prince="dagon")) == "dagon"

def test_lore_view_shows_branch_reading():
    e, w = _engine()
    e.vow("daedric", "mora")
    # 发掘当前省（赛瑞迪尔）的隐藏卷轴
    e.search()
    e.dispatch("lore")
    v = build_play_view(e)
    text = _view_text(v)
    assert "莫拉解读" in text or "莫拉" in text    # 至少出现魔神名字
    # 回退到游历模式
    e.dispatch("lore_back")
    assert e.overlay is None


# ═══════════════════════════════════════════════════════════════════════════
# 五魔神王子独立支线任务（QuestSystem + Quests 组件）
# ═══════════════════════════════════════════════════════════════════════════

def test_quest_starts_on_vow():
    e, w = _engine()
    qs = _player(e).get(Quests).quests
    assert "azura" not in qs
    e.vow("daedric", "azura")
    assert "azura" in qs
    assert qs["azura"]["started"] is True
    assert qs["azura"]["done"] is False
    # 回填：已在赛瑞迪尔（起点），该 step 应直接判完成
    # 支线 azura 的步骤不涉及赛瑞迪尔，所以 step 0 不一定完成
    # 但起点 province=cyrodiil 不在 azura quest 里，故不变
    assert len(qs["azura"]["steps"]) == 4

def test_quest_progresses_on_moved():
    e, w = _engine()
    e.vow("daedric", "azura")
    _hp(e).value = 30
    # 移动至晨风（azura 支线第 0 步：visit morrowind）
    e.move_to("morrowind")
    st = _player(e).get(Quests).quests["azura"]
    assert st["steps"][0] is True        # visit morrowind done
    assert st["steps"][1] is False       # lore morrowind 尚未发掘

def test_quest_progresses_on_lore():
    e, w = _engine()
    e.vow("daedric", "azura")
    _hp(e).value = 30
    e.move_to("morrowind")
    # 在晨风原地探索，发掘隐秘卷轴（azura 支线第 1 步：lore morrowind）
    e.search()
    st = _player(e).get(Quests).quests["azura"]
    assert st["steps"][0] is True   # visit
    assert st["steps"][1] is True   # lore

def test_quest_completes_with_reward():
    """完整走通一条支线（azura）：mor + lore + bm + lore → 达成 + 奖励。"""
    e, w = _engine()
    e.vow("daedric", "azura")
    hp = _player(e).get(Health)
    hp.value = 30
    hp.max_value = 30
    last_atk = _player(e).get(Gear).attack
    cnt = {"complete": 0}
    e.bus.subscribe(EventTypes.QUEST_COMPLETE, lambda d: cnt.__setitem__("complete", cnt["complete"] + 1))
    # step 0: visit morrowind
    e.move_to("morrowind")
    # step 1: lore morrowind
    e.search()
    # step 2: visit black_marsh
    e.move_to("black_marsh")
    # step 3: lore black_marsh
    e.search()
    st = _player(e).get(Quests).quests["azura"]
    assert st["done"] is True
    assert all(st["steps"])
    # 奖励：黎明之戒 atk+2
    assert _player(e).get(Gear).attack >= last_atk + 2
    assert "黎明之戒" in _player(e).get(Pack).items
    assert cnt["complete"] == 1

def test_quests_independent():
    """两条支线互不干扰：切换王子保留旧进度、开启新进度。"""
    e, w = _engine()
    _hp(e).value = 30
    e.vow("daedric", "azura")
    e.move_to("morrowind")      # azura step 0 done
    e.search()                   # azura step 1 done
    # 改献大衮
    e.vow("daedric", "dagon")
    qs = _player(e).get(Quests).quests
    # azura 进度保留
    assert "azura" in qs
    assert qs["azura"]["steps"][0] and qs["azura"]["steps"][1]  # 已完成两步
    assert not qs["azura"]["done"]
    # dagon 新开
    assert "dagon" in qs
    assert qs["dagon"]["started"] and not qs["dagon"]["done"]
    # dagon 回填：起点赛瑞迪尔不在 quest 中，步 0 不变
    # 移动至天际（dagon step 0: visit skyrim）
    e.move_to("skyrim")
    assert qs["dagon"]["steps"][0] is True

def test_quest_snapshot_roundtrip():
    e, w = _engine()
    _hp(e).value = 30
    e.vow("daedric", "azura")
    e.move_to("morrowind")
    snap = e.to_snapshot()
    e2 = PlayEngine.from_snapshot(w, snap)
    qs2 = _player(e2).get(Quests).quests
    assert "azura" in qs2
    assert qs2["azura"]["steps"] == _player(e).get(Quests).quests["azura"]["steps"]
    # 续局后仍可推进
    e2.search()
    assert qs2["azura"]["steps"][1] is True

def test_quest_view_renders():
    e, w = _engine()
    e.vow("daedric", "sheo")
    e.dispatch("quest")
    v = build_play_view(e)
    assert "支线任务" in v.title
    assert "谢戈拉思" in _view_text(v)
    assert "混沌巡游" in _view_text(v)
    e.dispatch("quest_back")
    assert e.overlay is None
