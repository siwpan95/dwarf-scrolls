"""《矮人要塞风格的上古卷轴》—— 以矮人要塞 Legends Mode 阅读器形态呈现上古卷轴编年史。

本项目**内置**引擎地基 ``alloy``（物理内联于 ``dwarf_scrolls/alloy/``），
完全自包含、无项目外依赖。``dwarf_scrolls/core/engine_bootstrap.py`` 把本目录注入
sys.path 最前，使 ``import alloy`` 解析到项目内部的 ``dwarf_scrolls/alloy``。
此处仅作项目根标记，不重复引擎初始化逻辑。
"""
