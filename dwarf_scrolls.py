"""dwarf_scrolls — 包名桥（仓名 dwarf-scrolls ↔ Python 包名 dwarf_scrolls）

一仓一目录治理下本地目录为 ``G:\\repos\\dwarf-scrolls``（连字符，与 gitee 仓名一致），
而应用代码沿用历史包名 ``dwarf_scrolls.*``（``from dwarf_scrolls.core.legends import ...``）。
迁仓时目录被拍平（core/、game/ 直接在仓库根），包名导入随之失效（2026-08-27 阶段 4
勘查发现，README 治理期间未运行应用故未暴露）。

本模块以 sys.modules 注册方式把 ``dwarf_scrolls.core`` / ``dwarf_scrolls.game`` /
``dwarf_scrolls.main`` 别名到仓库根下的同名模块，使全部老导入路径在拍平布局下可用；
不移动任何代码。``python -m dwarf_scrolls`` 等价于 ``python main.py``。

记账（借鉴必记账）：本桥为仓名/包名不一致的布局修复，非规则接入。
"""
import sys

import core as _core
import game as _game

sys.modules.setdefault("dwarf_scrolls.core", _core)
sys.modules.setdefault("dwarf_scrolls.game", _game)

import main as _main  # noqa: E402  注册 dwarf_scrolls.main（main.py 依赖上面的别名）

sys.modules.setdefault("dwarf_scrolls.main", _main)

if __name__ == "__main__":
    from dwarf_scrolls.main import main

    main()
