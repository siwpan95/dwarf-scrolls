"""《矮人要塞风格的上古卷轴》—— 游戏入口。

以矮人要塞 Legends Mode（历史卷轴阅读器）的形态，承载 The Elder Scrolls 的
kalpic 编年史：程序化生成一座泰姆瑞尔世界，逐年推演其战争、王朝、巨龙、
湮灭入侵与龙破，再由「先祖飞蛾祭司」（你）以矮人要塞式的彩色编年史阅读。

启动：``python main.py``（在 dwarf_scrolls/ 目录下执行）。
可用环境变量 ``DWARF_SCROLLS_SEED`` 指定种子以复现同一部历史。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── 路径保障：使 dwarf_scrolls 包可被导入，并触发内联引擎优先 ──
_PKG_ROOT = Path(__file__).resolve().parent           # 仓库根（G:\repos\dwarf-scrolls）
_PARENT = _PKG_ROOT.parent                            # 仓库父目录
# 2026-08-27（阶段 4 勘查修复）：仓库按一仓一目录命名为 dwarf-scrolls（连字符），
# 包名桥 dwarf_scrolls.py 位于仓库根——须把仓库根（而非仅父目录）加入 sys.path。
for _p in (_PKG_ROOT, _PARENT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# engine_bootstrap 是侧效导入：模块级代码把 GAME_ROOT 注入 sys.path 最前、
# 清除已缓存的外部 alloy，确保内联引擎优先（与 play_core.py 模式一致）。
import dwarf_scrolls.core.engine_bootstrap  # noqa: E402

from dwarf_scrolls.core.world_gen import WorldGenerator       # noqa: E402
from dwarf_scrolls.core.history_gen import HistoryGenerator   # noqa: E402
from dwarf_scrolls.core.save_manager import SaveManager       # noqa: E402


def build_world(seed: int):
    """生成并推演一座完整的泰姆瑞尔编年史世界。"""
    world = WorldGenerator(seed=seed).generate()
    HistoryGenerator(seed=seed, world=world).generate()
    return world


def main() -> None:
    seed = 0
    env_seed = os.environ.get("DWARF_SCROLLS_SEED")
    if env_seed is not None:
        try:
            seed = int(env_seed)
        except ValueError:
            seed = 0

    print(f"[info] 正在推演泰姆瑞尔编年史（种子 0x{seed & 0xFFFFFFFF:x}）……")
    world = build_world(seed)
    SaveManager().auto_save(world)
    print(f"[info] 史事 {len(world.events)} 条 · 人物 {len(world.figures)} 位 · "
          f"地点 {len(world.sites)} 处 · 时代 {len(world.ages)} 个。")

    try:
        import tkinter  # noqa: F401
        from dwarf_scrolls.game.legends_gui import LegendsGuiWindow
        LegendsGuiWindow(world).run()
    except Exception:
        # 无 tkinter / 无显示器 → 终端回退
        from dwarf_scrolls.game.legends_cli import run_cli
        run_cli(world)


if __name__ == "__main__":
    main()
