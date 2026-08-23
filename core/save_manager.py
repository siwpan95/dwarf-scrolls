"""存档 / 读档 —— 把整座编年史世界（WorldModel）序列化为 JSON。

不再是 roguelike 的「玩家+代理+背包」快照，而是「整个世界的历史」本身。
飞蛾祭司（玩家）读到的每一卷上古卷轴，都是这样一份可保存、可重载的档案。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .engine_bootstrap import GAME_ROOT
from .legends import WorldModel


class SaveManager:
    """把 WorldModel 以 JSON 形式存入 saves/ 目录。"""

    def __init__(self, save_dir: Optional[str] = None) -> None:
        self.save_dir = Path(save_dir) if save_dir else (GAME_ROOT / "saves")
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, slot: int) -> Path:
        return self.save_dir / f"scroll_{slot:02d}.json"

    def save(self, world: WorldModel, slot: int = 0) -> bool:
        self._path(slot).write_text(
            world.to_json(indent=1, ensure_ascii=False), encoding="utf-8")
        return True

    def auto_save(self, world: WorldModel) -> bool:
        return self.save(world, slot=99)

    def load(self, slot: int = 0) -> Optional[WorldModel]:
        p = self._path(slot)
        if not p.exists():
            return None
        return WorldModel.from_json(p.read_text(encoding="utf-8"))

    def load_latest(self) -> Optional[WorldModel]:
        saves = self.list_saves()
        if not saves:
            return None
        return WorldModel.from_json(saves[-1].read_text(encoding="utf-8"))

    def list_saves(self) -> List[Path]:
        return sorted(self.save_dir.glob("scroll_*.json"))

    def has_saves(self) -> bool:
        return bool(self.list_saves())


class PlaySaveManager:
    """游历模式独立存档：把 ``PlayEngine.to_snapshot()`` 的 dict 存入 ``saves/play.json``。

    与 ``SaveManager``（存档整座编年史世界）不同，这里只存「玩家这一程的游历进度」
    —— 组件状态 + 种子 + rng 状态，便于下次进入游戏时续上同一段旅程。
    """

    def __init__(self, save_dir: Optional[str] = None) -> None:
        self.save_dir = Path(save_dir) if save_dir else (GAME_ROOT / "saves")
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.save_dir / "play.json"

    def save(self, snapshot: Dict[str, Any]) -> bool:
        self.path.write_text(
            json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        return True

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def has_save(self) -> bool:
        return self.path.exists()

    def clear(self) -> bool:
        if self.path.exists():
            self.path.unlink()
            return True
        return False
