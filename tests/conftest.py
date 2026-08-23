"""pytest 共享夹具：把项目根目录加入 sys.path 并引导 alloy。

``dwarf_scrolls`` 位于其自身目录（如 D:\\allin\\dwarf_scrolls），引擎 ``alloy``
作为内置地基物理内联于 ``dwarf_scrolls/alloy/``，无项目外依赖。
引导由 ``dwarf_scrolls.core.engine_bootstrap`` 完成（把 dwarf_scrolls 目录注入
sys.path 最前，使 ``import alloy`` 解析到项目内部）。此处仅需确保 dwarf_scrolls
可被导入，再触发引导。
"""
import sys
from pathlib import Path

# tests/ -> dwarf_scrolls/，把项目根加入 sys.path 以便 import dwarf_scrolls
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dwarf_scrolls.core.engine_bootstrap import ensure_engine_loaded  # noqa: E402

# 幂等引导引擎（将 alloy 解析到 dwarf_scrolls/alloy 内部副本）
ensure_engine_loaded()
