"""加载 dwarf_scrolls 内置引擎地基 alloy（位于本项目的 ``dwarf_scrolls/alloy/``）。

架构：dwarf_scrolls 以 alloy 为地基**自包含**构建，引擎代码物理内联于
``dwarf_scrolls/alloy/``，不依赖任何项目外目录。

实现：把 ``GAME_ROOT``（dwarf_scrolls 目录）注入 ``sys.path`` 最前，使
``import alloy`` 解析到项目内部的 ``dwarf_scrolls/alloy`` 包，
而非其它位置的同名包。这样游戏侧既保持 ``from alloy import ...`` 的写法，
又完全脱离外部 ``D:\\allin\\alloy`` 等任何项目外依赖。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 游戏侧根目录（本文件位于 dwarf_scrolls/core/engine_bootstrap.py）
GAME_ROOT = Path(__file__).resolve().parents[1]          # D:\allin\dwarf_scrolls

# 引擎包根目录（项目内置地基；2026-08-23 起引擎改名 alloy，
# 旧名 alloy 由 shim 重定向到本目录）
ENGINE_ROOT = GAME_ROOT / "alloy"

# 确保 ``import alloy`` 始终解析到项目内部的 dwarf_scrolls/alloy：
# 把 GAME_ROOT 提到 sys.path **最前**，并清除可能已缓存的外部同名引擎，
# 使内联引擎在所有环境下都优先、真正自包含。
_gp = str(GAME_ROOT)
if _gp in sys.path:
    sys.path.remove(_gp)
sys.path.insert(0, _gp)
for _k in list(sys.modules):
    if _k == "alloy" or _k.startswith("alloy.") or _k == "alloy" or _k.startswith("alloy."):
        del sys.modules[_k]


def ensure_engine_loaded() -> None:
    """导入项目内置引擎包 alloy（幂等）。

    解析到 ``dwarf_scrolls/alloy/__init__.py``，无任何项目外依赖。
    约定返回 None（保持与既有测试一致）。
    """
    import alloy  # noqa: F401  -> D:\allin\dwarf_scrolls\alloy
    return None
