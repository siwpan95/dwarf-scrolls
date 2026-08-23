"""游历模式 —— 游戏数据与常量。

包含省份邻接关系、敌人模板、战利品、魔神王子分支数据、
隐藏剧情文本、终章分歧文本，以及分支查询工具函数。
所有数据由此模块统一管理，各系统按需导入。
"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from dwarf_scrolls.game.legends_view import MAP_CHAR_TO_PROV


# ── 邻接关系 ──
# 显式定义，贴合 TES 真实地理。视觉地图仅作装饰，
# 邻接以本表为权威，与渲染解耦。
ADJACENCY: Dict[str, Set[str]] = {
    "summerset":  {"valenwood"},
    "valenwood":  {"summerset", "cyrodiil", "elsweyr"},
    "elsweyr":    {"valenwood", "cyrodiil", "black_marsh"},
    "high_rock":  {"skyrim", "hammerfell"},
    "skyrim":     {"high_rock", "hammerfell", "cyrodiil", "morrowind"},
    "hammerfell": {"high_rock", "skyrim", "cyrodiil"},
    "cyrodiil":   {"valenwood", "elsweyr", "skyrim", "hammerfell", "morrowind", "black_marsh"},
    "morrowind":  {"skyrim", "cyrodiil", "black_marsh"},
    "black_marsh":{"morrowind", "cyrodiil", "elsweyr"},
}

# 省份总数（卷轴碎片目标）
PROVINCE_COUNT = len(MAP_CHAR_TO_PROV)

# 阵营中文
_ALIGN_CN = {"good": "善良", "evil": "邪恶", "neutral": "中立"}
# 誓言中文
_ALLEGIANCE_CN = {"none": "中立", "aedric": "圣灵(Aedra)", "daedric": "魔神(Daedra)"}

# ── 敌人与随机遭遇 ──
# 每省至少 1 种敌人模板，贴合 TES 设定
ENEMIES: Dict[str, List[Dict[str, Any]]] = {
    "summerset": [
        {"name": "晶塔守卫",   "hp": 8,  "atk": 3, "desc": "高等精灵的奥术造物，晶化躯体折射阳光。"},
        {"name": "奥术仲裁者", "hp": 7,  "atk": 4, "desc": "被驱逐的先祖飞蛾祭司，奥术之怒不灭。"},
    ],
    "valenwood": [
        {"name": "树皮巨魔",   "hp": 12, "atk": 2, "desc": "林间古树被魔神低语唤醒，根须化为利爪。"},
        {"name": "影林猎手",   "hp": 9,  "atk": 3, "desc": "木精灵叛誓者，弓箭如林间落叶无声。"},
    ],
    "elsweyr": [
        {"name": "沙丘掠袭者", "hp": 9,  "atk": 3, "desc": "猫人沙漠旅团中堕落的哨兵，弯刀染毒。"},
        {"name": "月影狂徒",   "hp": 11, "atk": 2, "desc": "双月满盈之夜被魔神驱使的猫人，双眼如冷火。"},
    ],
    "high_rock": [
        {"name": "断誓骑士",   "hp": 10, "atk": 3, "desc": "曾对圣灵起誓的布莱顿骑士，誓言已碎，长剑未折。"},
        {"name": "废塔术士",   "hp": 8,  "atk": 4, "desc": "精灵废墟中的布莱顿术士，唤出古老的守护咒。"},
    ],
    "skyrim": [
        {"name": "霜喉巨魔",   "hp": 12, "atk": 2, "desc": "冬堡以北的巨魔，每息吐霜，皮厚如冻土。"},
        {"name": "尸鬼霸主",   "hp": 10, "atk": 4, "desc": "古墓中的诺德尸鬼，龙吼的碎片仍嵌在喉中。"},
    ],
    "hammerfell": [
        {"name": "坠星剑士",   "hp": 9,  "atk": 4, "desc": "红卫剑术大师，剑如坠星——快、烈、无处可逃。"},
        {"name": "沙暴亡灵",   "hp": 11, "atk": 2, "desc": "阿力克尔沙漠中的怨灵，风沙裹挟着未竟的誓言。"},
    ],
    "cyrodiil": [
        {"name": "帝国逃兵",   "hp": 8,  "atk": 3, "desc": "白金塔兵团中叛逃的百夫长，剑法仍存军团之严。"},
        {"name": "湮灭裂隙兽", "hp": 14, "atk": 3, "desc": "从帝国腹地的裂隙爬出的湮灭造物，甲壳如黑曜石。"},
    ],
    "morrowind": [
        {"name": "灰烬魔像",   "hp": 10, "atk": 3, "desc": "红山灰烬中凝聚的魔像，每一步都洒落灼尘。"},
        {"name": "第六家族刺客", "hp": 7, "atk": 5, "desc": "达格斯·乌尔的残党，短刃浸过疫病。"},
    ],
    "black_marsh": [
        {"name": "沼鳞猎手",   "hp": 9,  "atk": 2, "desc": "亚龙人沼地猎手，鳞甲融入泥沼，毒吹箭无声。"},
        {"name": "古希斯特树灵", "hp": 13, "atk": 3, "desc": "被遗忘的希斯特树，根须化为人形行走沼泽。"},
    ],
}

# ── 中立省随机遭遇（非战斗） ──
RANDOM_ENCOUNTERS: Dict[str, List[Dict[str, Any]]] = {
    "merchant":  {"name": "流浪商队",  "hp": 0, "atk": 0, "kind": "heal",
                   "texts": ["一队布莱顿商旅与你分享药草", "猫人商队用月糖换你的故事", "红卫兵器商人修好了你的装备"]},
    "pilgrim":   {"name": "朝圣者",    "hp": 0, "atk": 0, "kind": "heal",
                   "texts": ["朝圣者为你吟诵圣灵咒文", "先祖飞蛾祭司在路边驻足祝福", "圣灵修女递来一瓶圣泉之水"]},
    "storm":     {"name": "自然灾害",  "hp": 2, "atk": 0, "kind": "damage",
                   "texts": ["暴风雪将你困在隘口一夜", "沙暴剐过铠甲，你失了些气血", "沼泽瘴气弥漫，你咳出黑色的唾沫"]},
    "ruin":      {"name": "古遗迹",    "hp": 0, "atk": 0, "kind": "loot",
                   "texts": ["你在精灵废墟中拾得古籍", "矮人遗迹的管道里存着药膏", "诺德古墓的外室堆着补给"]},
}

LOOT_WEAPONS: List[Tuple[str, int]] = [
    ("符文长剑", 3), ("龙牙匕首", 4), ("寒铁战斧", 5), ("圣灵权杖", 6),
]
HEAL_POTION: Tuple[str, int] = ("治愈药剂", 6)

# ── 魔神分支 ──
DAEDRIC_PRINCES: Dict[str, Dict[str, Any]] = {
    "azura": {"name": "阿祖拉", "title": "黄昏与黎明的魔神",
              "blurb": "揭示隐秘，使 hostile 虚弱一分", "atk_mod": 0,
              "evil_atk_mod": 0, "enemy_atk_mod": -1, "loot_chance": 0.7,
              "dominate": 0.0, "chaos": False,
              "quest": {"name": "黄昏朝圣",
                        "brief": "巡礼暮色之地，于魔神所偏爱的边境揭示被封存的隐秘。",
                        "steps": [{"type": "visit", "prov": "morrowind"},
                                   {"type": "lore", "prov": "morrowind"},
                                   {"type": "visit", "prov": "black_marsh"},
                                   {"type": "lore", "prov": "black_marsh"}],
                        "reward": {"name": "黎明之戒", "atk": 2, "maxhp": 0, "heal": 0,
                                   "text": "你指间多了阿祖拉的黎明之戒——两面之真实于你眼前同时展开。"}}},
    "dagon": {"name": "梅鲁涅斯·大衮", "title": "毁灭之魔神",
              "blurb": "毁灭之力加持攻击与战利品", "atk_mod": 1,
              "evil_atk_mod": 0, "enemy_atk_mod": 0, "loot_chance": 0.8,
              "dominate": 0.0, "chaos": False,
              "quest": {"name": "毁灭远征",
                        "brief": "踏过刀痕遍地的北境，于焦土中拾起大衮遗落的符文。",
                        "steps": [{"type": "visit", "prov": "skyrim"},
                                   {"type": "visit", "prov": "hammerfell"},
                                   {"type": "lore", "prov": "skyrim"},
                                   {"type": "lore", "prov": "hammerfell"}],
                        "reward": {"name": "毁灭符文", "atk": 3, "maxhp": 0, "heal": 0,
                                   "text": "大衮的毁灭符文烙入你掌——凡所指处，伪史皆焚。"}}},
    "molag": {"name": "莫拉格·巴尔", "title": "支配与奴役之魔神",
              "blurb": "有几率直接支配并碾碎敌人", "atk_mod": 0,
              "evil_atk_mod": 0, "enemy_atk_mod": 0, "loot_chance": 0.6,
              "dominate": 0.3, "chaos": False,
              "quest": {"name": "支配之链",
                        "brief": "巡行帝国旧座，将圣灵所立的秩序之链亲手缚紧。",
                        "steps": [{"type": "visit", "prov": "high_rock"},
                                   {"type": "lore", "prov": "high_rock"},
                                   {"type": "visit", "prov": "cyrodiil"},
                                   {"type": "lore", "prov": "cyrodiil"}],
                        "reward": {"name": "支配锁链", "atk": 0, "maxhp": 5, "heal": 5,
                                   "text": "莫拉格·巴尔的锁链缠上你腕——凡你所至，皆成受其缚的疆土。"}}},
    "sheo":  {"name": "谢戈拉思", "title": "疯神",
              "blurb": "战斗充满混沌的随机加成", "atk_mod": 0,
              "evil_atk_mod": 0, "enemy_atk_mod": 0, "loot_chance": 0.6,
              "dominate": 0.0, "chaos": True,
              "quest": {"name": "混沌巡游",
                        "brief": "在疯神最爱的乱序之地游走，把「正经」这件事彻底走丢。",
                        "steps": [{"type": "visit", "prov": "elsweyr"},
                                   {"type": "lore", "prov": "elsweyr"},
                                   {"type": "visit", "prov": "valenwood"},
                                   {"type": "lore", "prov": "valenwood"}],
                        "reward": {"name": "混沌权杖", "atk": 2, "maxhp": 0, "heal": 3,
                                   "text": "谢戈拉思的混沌权杖在你手中咯咯作响——下一击是祝福还是灾难？谁知道。"}}},
    "mora":  {"name": "赫玛攸斯·莫拉", "title": "知识与命运之魔神",
              "blurb": "知识加持，对邪恶省攻击 +1", "atk_mod": 0,
              "evil_atk_mod": 1, "enemy_atk_mod": 0, "loot_chance": 0.6,
              "dominate": 0.0, "chaos": False,
              "quest": {"name": "命运研读",
                        "brief": "在知识的源头与秩序的中心之间往返，翻动那本无字的命运之书。",
                        "steps": [{"type": "visit", "prov": "summerset"},
                                   {"type": "lore", "prov": "summerset"},
                                   {"type": "visit", "prov": "cyrodiil"},
                                   {"type": "lore", "prov": "cyrodiil"}],
                        "reward": {"name": "命运卷册", "atk": 1, "maxhp": 3, "heal": 0,
                                   "text": "莫拉将无字之书的注脚交你——kalpic 的真名，自此只在你眸中显形。"}}},
}

# ── 隐藏剧情 ──
HIDDEN_LORE: Dict[str, str] = {
    "summerset":  "夏暮岛的隐秘：先祖飞蛾并非虫豸，而是被封入琥珀的时间本身。",
    "valenwood":  "威木省的隐秘：林间每片落叶都记着一句未被诵出的 kalpic 预言。",
    "elsweyr":    "艾斯维尔的隐秘：两月当空之夜，猫人听见的是湮灭的低语而非风声。",
    "high_rock":  "高岩的隐秘：残破的精灵塔下，圣灵与魔神曾于同一次黎明天平分泰姆瑞尔。",
    "skyrim":     "天际的隐秘：世界咽喉的吼声能震落时间，松加德语者只是偶然拾得碎片。",
    "hammerfell": "落锤的隐秘：红卫人的剑术源自坠星，每一柄都是一颗熄灭的星。",
    "cyrodiil":   "赛瑞迪尔的隐秘：白金塔并非建筑，而是阿卡托什钉住时间的第一根钉。",
    "morrowind":  "晨风的隐秘：红山之下压着被遗忘的第六次轮回，魔神以免其苏醒。",
    "black_marsh":"黑沼的隐秘：沼泽吞没的不仅是旅人，还有 Aedra 不愿承认的错误。",
}

# 隐秘文本的分支「解读」
HIDDEN_LORE_READING: Dict[str, Dict[str, str]] = {
    "summerset": {
        "neutral": "你以旁观之眼记下：飞蛾封存时间，仅此而已。",
        "aedric": "圣灵之徒释然——被封的时间是 Aedra 留给后世的秩序之种。",
        "azura": "阿祖拉低语：非封存，而是折叠；两面皆为真实。",
        "dagon": "大衮嗤笑：时间不过是待焚的旧纸，落灰即新章。",
        "molag": "莫拉格·巴尔冷语：时间早被缚为奴，飞蛾只是狱卒。",
        "sheo": "谢戈拉思咯咯笑：时间从未被封，是你在折纸里迷了路。",
        "mora": "莫拉翻动无字之书：封存的不是时间，是「时间的名字」。",
    },
    "valenwood": {
        "neutral": "你记下：每片落叶都记着一句未诵出的预言。",
        "aedric": "圣灵解曰：预言早在秩序中写下，落叶只是复述。",
        "azura": "阿祖拉叹：落叶所记，是黄昏与黎明之间的第三种预言。",
        "dagon": "大衮叱：预言该被焚尽，唯余你亲手写下的那句。",
        "molag": "莫拉格·巴尔锁链响：预言是缚住命运的绳，落叶即绳结。",
        "sheo": "谢戈拉思笑：哪句才是真？落叶自己都忘了。",
        "mora": "莫拉低语：预言无字，落叶不过借风翻书。",
    },
    "elsweyr": {
        "neutral": "你记下：两月当空之夜，猫人听见湮灭的低语。",
        "aedric": "圣灵抚慰：那是魔神伪声，坚守净域即可不闻。",
        "azura": "阿祖拉眸光微动：低语非伪，是湮灭也在寻它的黎明。",
        "dagon": "大衮亢奋：低语即号角，焚开净域之门！",
        "molag": "莫拉格·巴尔冷笑：低语是锁链另一端的牵引。",
        "sheo": "谢戈拉思拍手：两月？我数到七个月亮！",
        "mora": "莫拉凝视：猫人所闻，是命运之书的扉页耳语。",
    },
    "high_rock": {
        "neutral": "你记下：残塔下，圣灵与魔神曾于同一次黎明平分泰姆瑞尔。",
        "aedric": "圣灵肃然：那平分之约仍在，守护它便是我们的责。",
        "azura": "阿祖拉轻笑：平分非妥协，是两面同照一图。",
        "dagon": "大衮怒：平分当破，唯余毁灭独掌乾坤。",
        "molag": "莫拉格·巴尔阴沉：平分不过是更早的臣服。",
        "sheo": "谢戈拉思歪头：同一次黎明？我那次有十三种。",
        "mora": "莫拉翻页：那约书早已被吞入无字之库。",
    },
    "skyrim": {
        "neutral": "你记下：世界咽喉的吼声能震落时间，松加德语者只是拾得碎片。",
        "aedric": "圣灵颔首：碎片亦出自创世之喉，当珍而述之。",
        "azura": "阿祖拉低吟：震落的时间两面皆在，松加只拾其一。",
        "dagon": "大衮咆哮：何不震碎时间，重写一切？",
        "molag": "莫拉格·巴尔讥：拾得碎片者，不过是锁链的下一环。",
        "sheo": "谢戈拉思大笑：我吼一声，时间打喷嚏了！",
        "mora": "莫拉淡然：所拾碎片，皆是无字之书的注脚。",
    },
    "hammerfell": {
        "neutral": "你记下：红卫人的剑术源自坠星，每柄剑都是一颗熄灭的星。",
        "aedric": "圣灵赞许：熄星之辉化入剑意，正合秩序之美。",
        "azura": "阿祖拉望天：星非熄，是落入两面之间的黄昏。",
        "dagon": "大衮渴战：那就让更多星，在我的火里熄灭。",
        "molag": "莫拉格·巴尔冷语：每柄剑，都是缚星之链的一段。",
        "sheo": "谢戈拉思眨眼：星星掉下来，是想参加我的茶会。",
        "mora": "莫拉低语：剑名即星名，星名载于命运之书。",
    },
    "cyrodiil": {
        "neutral": "你记下：白金塔非建筑，而是阿卡托什钉住时间的第一根钉。",
        "aedric": "圣灵庄严：那金钉正是我们钉下的秩序之锚。",
        "azura": "阿祖拉幽光：钉住一面，另一面便在黄昏里游走。",
        "dagon": "大衮狞笑：拔钉！让时间洪流吞没这伪史。",
        "molag": "莫拉格·巴尔锁链响：钉亦是链，泰姆瑞尔早被缚于塔下。",
        "sheo": "谢戈拉思咯咯：钉子歪了，时间一直在偷偷抖腿。",
        "mora": "莫拉凝视：钉名无人知晓，它只在无字之书里。",
    },
    "morrowind": {
        "neutral": "你记下：红山之下压着被遗忘的第六次轮回，魔神以免其苏醒。",
        "aedric": "圣灵警惕：那轮回若醒，秩序须以净域镇之。",
        "azura": "阿祖拉悲悯：第六次轮回两面皆存，魔神只是看守。",
        "dagon": "大衮狂喜：何不唤醒它，看世界再焚一次？",
        "molag": "莫拉格·巴尔冷笑：轮回本就是被缚的囚，红山即牢。",
        "sheo": "谢戈拉思雀跃：第六次？我排到第九次了！",
        "mora": "莫拉翻页：第六次轮回的页码，在无字之书正中。",
    },
    "black_marsh": {
        "neutral": "你记下：沼泽吞没的不仅是旅人，还有 Aedra 不愿承认的错误。",
        "aedric": "圣灵赧然：纵有缺漏，净域仍容得下悔改。",
        "azura": "阿祖拉轻叹：错误两面皆有，沼泽只是沉下了黄昏那面。",
        "dagon": "大衮狞笑：错误该焚尽，沼泽不过提前替我收尸。",
        "molag": "莫拉格·巴尔阴冷：吞没即是缚，沼泽是天然的牢。",
        "sheo": "谢戈拉思哼曲：错误？我最喜欢那种带泥味的。",
        "mora": "莫拉低语：那错误被写入无字之书，成了注脚。",
    },
}

# ── 终章分歧 ──
HIDDEN_CHAPTER = (
    "（kalpic 终章）当九省隐秘尽数归于掌心，你方知飞蛾祭司不过是湮灭写给人间的信使。"
    "Aedra 与 Daedra 的争执从不是善恶，而是对「故事该由谁讲述」的争夺——"
    "而你，已成了那个把卷轴重新装订的人。"
)

AEDRIC_EPILOGUE = (
    "（圣灵之线）圣灵之光中，九省隐秘归位为有序的 kalpic——飞蛾祭司是 Aedra 派遣的抄写天使，"
    "将泰姆瑞尔的创世秩序一笔笔录下；湮灭之叙述，自此被净域隔绝在史册之外。"
)

PRINCE_EPILOGUE: Dict[str, str] = {
    "azura": (
        "（阿祖拉之线）你以黄昏与黎明之眼俯瞰，终见 kalpic 并非单线史册，而是两面交叠的叙事；"
        "飞蛾祭司原是先秦观星人，借琥珀封存了「被讲述的另一种可能」。"
    ),
    "dagon": (
        "（大衮之线）毁灭之火焚尽九省伪史，你于灰烬中重建 kalpic——它不再只是记录，"
        "而是一道劈开湮灭的裂隙；毁灭，是最古老的叙述。"
    ),
    "molag": (
        "（莫拉格·巴尔之线）你以支配之链串起九省隐秘，kalpic 终成被缚的卷轴——"
        "飞蛾祭司不过是替你誊写囚徒传记的抄吏，真正的叙述者，是握锁链之人。"
    ),
    "sheo": (
        "（谢戈拉思之线）疯神的笑声里，九省隐秘在脑中打乱重排——kalpic 没有终章，"
        "只有无数个同时发生的你；飞蛾祭司的真相，是「真相本就疯癫」。"
    ),
    "mora": (
        "（莫拉之线）赫玛攸斯·莫拉将九省隐秘摊开为无字之书，你以知识之指翻动命运——"
        "飞蛾祭司原是档案馆的门房，而 kalpic 的真名，唯有被吞入黑暗者方知。"
    ),
}


# ── 分支查询工具函数 ──

def _branch_key(al: "Allegiance") -> str:
    """把誓言解析为解读/任务分支键：圣灵→aedric，魔神→王子 id，其余→neutral。"""
    # 延迟导入避免循环依赖
    from dwarf_scrolls.game.play_components import Allegiance as AL
    if al.kind == "aedric":
        return "aedric"
    if al.kind == "daedric" and al.prince:
        return al.prince
    return "neutral"


def _lore_reading(pid: str, al: "Allegiance") -> str:
    """返回当前誓言分支下，某省隐秘卷轴的「解读」文本（缺失回退 neutral）。"""
    branch = _branch_key(al)
    readings = HIDDEN_LORE_READING.get(pid, {})
    return readings.get(branch) or readings.get("neutral") or ""


def _branch_label(al: "Allegiance") -> str:
    """返回当前誓言分支的展示名（圣灵 / 某魔神王子 / 中立）。"""
    if al.kind == "aedric":
        return "圣灵"
    if al.kind == "daedric" and al.prince:
        return DAEDRIC_PRINCES.get(al.prince, {}).get("name", "魔神")
    return "中立"


def _epilogue_for(al: "Allegiance") -> Tuple[str, str]:
    """按誓言返回主线终章的分歧版本（圣灵 / 五大魔神 / 中立）。"""
    if al.kind == "aedric":
        return ("圣灵之线", AEDRIC_EPILOGUE)
    if al.kind == "daedric" and al.prince:
        pr = DAEDRIC_PRINCES.get(al.prince)
        if pr:
            return (f"{pr['name']}之线", PRINCE_EPILOGUE.get(al.prince, HIDDEN_CHAPTER))
    return ("中立之线", HIDDEN_CHAPTER)
