# Dwarf Scrolls — 矮人要塞风格的上古卷轴

以 **矮人要塞（Dwarf Fortress）的像素/ASCII 终端画风** 呈现 **上古卷轴（The Elder Scrolls）**：既有矮人要塞式的 **Legends Mode（历史卷轴阅读器）**，也有一套 **鼠标驱动的游历模式（可玩）**——在程序生成的泰姆瑞尔世界地图上移动、遭遇敌对势力、休整、记录日志。程序还能把任意一屏渲染成 PNG，实现「内部截图自检」。

> 这是一座**程序化生成的泰姆瑞尔世界**。它的历史——战争、王朝、巨龙、湮灭入侵、龙破、巨塔兴衰——被写成矮人要塞式的编年史档案；而你也可以扮演一名英雄，用鼠标点击地图省份与行动超链接，在 DF 画风中游历这片土地。
>
> 「上古卷轴」在设定里本就是记载泰姆瑞尔一切历史的预言书——矮人要塞的
> Legends Mode 正是把历史当档案读；矮人要塞本身则有可玩的 Fortress Mode。
> 两者结合：阅读 + 游历，鼠标驱动，DF 画风。

## 为什么这么设计（终结「杂交」困惑）

早期版本把「矮人要塞」当作 roguelike（移动 / 战斗 / 采集 / 制造），却套了
上古卷轴的标题——成了四不像的「杂交版」。问题不在「玩法」，而在**画风和主题错位**：
看起来是 dwarves，玩的却是通用 roguelike，没利用上古卷轴世界。

本版把它拉回来：
- **矮人要塞 = 画风 + 双模式**：Legends Mode（阅读）和可玩的游历模式（移动/互动）。
- **上古卷轴 = 主题**：泰姆瑞尔 9 省、10 种族、九圣灵、十七迪德拉、三大同盟、
  神器、龙破、kalpic 历史全部来自 TES 设定。
- **输入 = 鼠标**：GUI 中左侧分类栏、正文蓝色超链接、世界地图瓦片、游历行动链，全部鼠标单击，无键盘依赖。
- **截图 = 自检**：把任意一屏（阅读 / 地图 / 游历）渲染成 PNG 保存，无需外部工具。

## 运行

```bash
# 推荐入口（自动推演世界并启动阅读器）
python -m dwarf_scrolls        # 或： python main.py

# 指定种子以复现同一部历史
DWARF_SCROLLS_SEED=42 python -m dwarf_scrolls
```

- 有显示器且安装 `tkinter` → 启动 **图形界面**：
- 左侧是分类目录，正文是蓝色可点击超链接；
- 顶栏有 **阅读/游历** 模式切换、返回、落地页、世界地图、**截图** 按钮；
- 游历模式：地图上的 `@` 是你的位置，点击相邻省份或「移动/休整/查看」超链接即可游玩。

无 `tkinter` / 无显示器 → 自动回退 **终端阅读器**（编号跳转、B/H/M/Q 命令）。

### 终端阅读器操作

```
[1]..[8]   跳转到对应分类 / 条目（彩色编号即超链接）
[B]         返回上一页        [H] 落地页（分类总览）
[M]         世界地图（省份瓦片着色：善/恶/中立）
[Q]         退出（「愿你的名字也被写进某一卷。」）
```

落地页分类：历史人物 · 地点 · 省份 · 派系 · 神器 · 史事 · 时代 · 世界地图。

## 项目结构

```
dwarf_scrolls/
├── main.py                  # 入口：生成世界 → 推演历史 → 启动阅读器（CLI/GUI 回退）
├── core/
│   ├── legends.py           # WorldModel 数据模型 + DF 风格叙事（narrate_*）
│   ├── world_gen.py         # TES 世界骨架生成（省份/地点/派系/人物/神器/时代）
│   ├── history_gen.py       # 程序化 kalpic 历史推演（事件 + 时代）
│   ├── save_manager.py      # 整座世界序列化为 scroll_NN.json
│   └── engine_bootstrap.py  # 加载内置引擎地基 alloy（零项目外依赖）
├── game/
│   ├── legends_view.py      # 共享视图层（View/Span）+ LegendsReader 导航栈 + ASCII 地图
│   ├── play_core.py         # 游历模式：可玩状态机（移动/休整/战斗/日志）
│   ├── screenshot.py        # 把任意 View 渲染为 PNG（程序内截图自检）
│   ├── commands.py          # 终端命令分发（数字/B/H/M/Q）
│   ├── legends_cli.py       # 终端阅读器（ConsoleRenderer 上色）
│   └── legends_gui.py       # tkinter 图形界面（阅读+游历双模式、纯鼠标、截图）
├── content/                 # 主题内容数据（cosmology/provinces/races/names/factions/artifacts/events）
├── saves/                   # 世界存档（scroll_NN.json）
├── shots/                   # 程序内截图输出（*.png）
├── alloy/            # 内置引擎地基（自包含，零项目外依赖）
├── tests/                   # pytest 测试套件
└── pyproject.toml
```

## 架构要点

- **引擎即地基，非死副本**：`alloy` 物理内联于 `dwarf_scrolls/alloy/`，
  运行时由 `core/engine_bootstrap.py` 把 `dwarf_scrolls` 注入 `sys.path` 最前，使
  `import alloy` 解析到项目内部副本，**完全脱离**任何外部项目路径依赖。
- **三层分工**：`core/`（数据 + 生成 + 叙事）→ `game/legends_view.py`（视图/导航）
  → `game/legends_cli.py | legends_gui.py`（表现）。CLI 与 GUI 共用同一套
  `LegendsReader` 与 `View`，仅渲染层不同。
- **一切皆数据**：整座世界是 `WorldModel`（可 JSON 序列化）。历史推演只往里追加
  `HistoricalEvent` 与 `Age`，条目页由 `narrate_*` 即时从数据生成，无隐藏状态。
- **确定性**：同一 `seed` 产出同一部历史（人物、史事、时代均可复现）。

## 内容数据

`content/*.json` 是易于编辑的主题素材，覆盖 TES 设定骨架：

| 文件 | 内容 |
|------|------|
| `cosmology.json` | 纪元 / 九圣灵（Aedra）/ 十七迪德拉亲王 / 巨塔 |
| `provinces.json` | 泰姆瑞尔九省（瓦片字符 / 阵营属性 / 着色） |
| `races.json` | 十种族及其命名风格 |
| `names.json` | 各族名式（名/氏族/称号）+ 神话人物 + 巨龙 |
| `factions.json` | 三大同盟 + 教团/公会/修会（替代旧 dwarf 公会） |
| `artifacts.json` | 上古卷轴 / 迪德拉 / 圣灵 神器 |
| `events.json` | 各类型史事的 DF 风格叙事模板 |

## 测试

```bash
python -m pytest tests/ -q
```

覆盖：世界生成、历史推演（断链/事件分布/确定性）、数据模型与序列化、
存档往返、视图层导航、命令分发、引擎引导。

## Python 版本

Python 3.10+

## 许可

MIT

## 规则内核接入判定（R2 · 2026-08-27）

勘查结论：本作数值均为 `random.Random(seed)` 区间随机（世界/编年史生成、休整骰
3-6 等），无 D&D/GURPS 骰系（d20/3d6/难度表）——alloy.trpg 无同构原语可接；按
「只接同构原语、绝不破坏行为契约」原则**不接入**（记账声明）。将来若引入检定：
`from alloy.trpg import roll_3d6, gurps_success_chance`（接入模式参照
running-group-simulator 的 `core/dice.py`）。

**附带修复（阶段 4 勘查）**：迁仓拍平后应用曾无法导入——仓名 dwarf-scrolls（连字符）
与历史包名 dwarf_scrolls 不一致，新增仓库根 `dwarf_scrolls.py` 包名桥
（sys.modules 别名，见文件内记账）；`main.py` 路径保障与 `pytest.ini` 同步修正；
测试 86/86 全绿。