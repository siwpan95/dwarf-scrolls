# alloy API — 游戏侧稳定接口

> 本文档标注 dwarf_scrolls 游戏代码依赖的 alloy 接口。
> 这些接口被视为「稳定可用」；其余引擎模块为内部实现细节，接口可能漂移。

---

## Layer 0 — Core（核心架构）

| 接口 | 路径 | 用途 | 稳定性 |
|------|------|------|--------|
| `Component` | `alloy.core.ecs` | ECS 组件基类 | ✅ 稳定 |
| `System` | `alloy.core.ecs` | ECS 系统基类，带 priority | ✅ 稳定 |
| `World` | `alloy.core.ecs` | ECS 世界容器 + 系统调度 | ✅ 稳定 |
| `Entity` | `alloy.core.ecs` | 实体（add/get 组件） | ✅ 稳定 |
| `EventBus` | `alloy.core.event_bus` | 事件总线（subscribe/emit） | ✅ 稳定 |
| `EventTypes` | `alloy` (__init__) | 事件类型枚举 | ✅ 稳定 |
| `FixedTimestepLoop` | `alloy.core.game_loop` | 固定步长主循环 + advance | ✅ 稳定 |

### ECS 常用操作

```python
from alloy.core.ecs import Component, System, World

# 组件定义
@dataclass
class Health(Component):
    value: int = 10

# 系统定义
class HealSystem(System):
    priority = 50  # 数值越大越靠后执行（play 系统约定）

    def update(self, world, dt):
        player = world.get_entity("player")
        ...

# 实体操作
p = world.create_entity("player")
p.add(Health(20))
hp = p.get(Health)
```

### EventBus 用法

```python
from alloy import EventTypes

# 订阅
bus.subscribe(EventTypes.PLAYER_MOVED, self.on_moved)

# 发射
bus.emit(EventTypes.PLAYER_MOVED, {"to": "skyrim", "alignment": "good"})

# 事件类型常量
PLAYER_MOVED, MOB_SPAWNED, MOB_DEFEATED, COMBAT_START, PLAYER_DIED, SHARD_FOUND, SHARD_HIDDEN, QUEST_COMPLETE
```

---

## Layer 1 — Engine Assembler

| 接口 | 路径 | 用途 | 稳定性 |
|------|------|------|--------|
| `GameEngine` | `alloy` (__init__) | 引擎装配器（add_core/advance） | ✅ 稳定 |

```python
from alloy import GameEngine

engine = GameEngine().add_core()
world = engine.world   # ECS World
bus   = engine.bus     # EventBus
loop  = engine.loop    # FixedTimestepLoop
engine.advance(dt)     # 驱动 loop.update
```

---

## Layer 2 — Render

| 接口 | 路径 | 用途 | 稳定性 |
|------|------|------|--------|
| `ConsoleRenderer` | `alloy.render.console_renderer` | ANSI 终端渲染 | ⚠️ 游戏通过 legends_cli 间接使用 |
| `Styles` | `alloy.render.gui_base` | tkinter 调色板 + 字体 | ✅ 稳定（legends_gui 直接使用） |

```python
from alloy.render.gui_base import Styles

s = Styles(theme="dark")
s.BG_DARKEST, s.TEXT_PRIMARY, s.ACCENT_BLUE, s.ACCENT_GOLD, ...
s.fonts["body"], s.fonts["heading"], s.fonts["button"]
```

---

## 引擎模块层级概览

```
alloy/
├── __init__.py          ← GameEngine, EventTypes 入口
├── core/                ← ECS + EventBus + Loop（Layer 0）✅ 稳定
│   ├── ecs.py
│   ├── event_bus.py
│   └── game_loop.py
├── world/               ← GameState/MapData/Item/Character
│   └── map_data.py      ← MapData（截图功能用）
├── systems/             ← 战斗/背包/谜题/命令/存档/Mod
├── render/              ← 控制台/GUI/动画/颜色/公式
│   ├── console_renderer.py
│   └── gui_base.py      ← Styles（✅ 稳定）
├── audio/               ← 音频系统（游戏未使用）
├── ai/                  ← 叙事/对话/决策引擎
├── fx/                  ← 粒子特效
├── test/                ← 引擎内置测试
└── utils/               ← 字体/JSON/日志/文本
```

---

## 游戏侧使用约定

1. **稳定接口**：上表中标记 ✅ 的接口在 minor 版本内保持兼容。
2. **内部细节**：其余模块（systems/ai/fx/audio 的具体实现类、render 的 Animation/FormulaEngine 等）
   接口可能随引擎演化而漂移——游戏代码应避免直接 import 不受 `@stable` 标记的引擎内部模块。
3. **新增依赖**：当游戏需要新的引擎能力时，先在此文档记录并评估稳定性。
