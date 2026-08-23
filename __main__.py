"""包入口：``python -m dwarf_scrolls`` 由此启动游戏。

真正的游戏编排实现位于 ``dwarf_scrolls/main.py``（``Game`` 类与 ``main()``）。
本模块只做轻量转发，确保 ``python -m dwarf_scrolls`` 与 ``python main.py``
两种调用方式都指向同一个真实入口。
"""
from dwarf_scrolls.main import main

if __name__ == "__main__":
    main()
