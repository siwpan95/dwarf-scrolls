"""Legends Mode 图形前端 —— 纯鼠标驱动的矮人要塞编年史阅读器/游历器。

设计原则（对应「用鼠标互动替换键盘输入」）：
- **左侧常驻分类栏**（Listbox）：对应矮人要塞 Legends Mode 的左侧目录，鼠标单击直达
  历史人物 / 地点 / 省份 / 派系 / 神器 / 史事 / 时代 / 世界地图；
- **正文区蓝色超链接**：鼠标单击即跳转（复刻矮人要塞 Legends Mode 的彩色高亮交叉引用）；
- **顶栏按钮**：←返回 / ⌂落地页 / 🗺世界地图，全部鼠标点击；
- **无任何键盘依赖**：GUI 自身不绑定任何按键，footer 也只提示鼠标操作。

外观：**复用引擎 ``allin_engine.render.gui_base.Styles``（DARK_PALETTE）调色板与字体**，
不再自建一套配色——颜色来源就是引擎自带的暗底亮色主题。ansi 色名到 tkinter 十六
进制色的适配集中在 ``_ansi_to_hex``（tkinter 需要 hex，ansi 名是引擎控制台概念）。
"""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont

import sys
import traceback

from allin_engine.render.gui_base import Styles  # 引擎：暗底亮色调色板 + 字体
from dwarf_scrolls.core.legends import WorldModel
from dwarf_scrolls.core.save_manager import PlaySaveManager
from dwarf_scrolls.game.legends_view import LegendsReader
from dwarf_scrolls.game.play_core import PlayState, build_play_view, dispatch_play_action
from dwarf_scrolls.game.screenshot import render_view_to_png


def _ansi_to_hex(s: Styles, name: str) -> str:
    """把引擎控制台的 ansi 色名映射到引擎调色板的十六进制色（tkinter 用）。"""
    m = {
        "white": s.TEXT_PRIMARY, "bright_black": s.TEXT_DIM,
        "cyan": s.ACCENT_BLUE, "red": s.ACCENT_RED, "green": s.ACCENT_GREEN,
        "bright_yellow": s.ACCENT_GOLD, "bright_blue": s.ACCENT_BLUE,
        "blue": s.ACCENT_BLUE, "yellow": s.ACCENT_GOLD,
        "magenta": s.ACCENT_PURPLE, "bright_magenta": s.ACCENT_PURPLE,
        "bright_green": s.ACCENT_GREEN, "bright_red": s.ACCENT_RED,
        "brown": s.ACCENT_GOLD,
    }
    return m.get(name, s.TEXT_PRIMARY)


class LegendsGuiWindow:
    def __init__(self, world: WorldModel) -> None:
        self.world = world
        self.reader = LegendsReader(world)
        self.play_save = PlaySaveManager()
        # 续局：若检测到存档则载入同一段旅程，否则开新局
        self.play_state = self._load_or_new()
        self.mode = "read"  # "read" | "play"
        self.root = tk.Tk()
        self.root.title("上古卷轴 · 泰姆瑞尔编年史 (Legends Mode)")
        self.root.geometry("1000x680")
        self.styles = Styles(theme="dark")  # 引擎调色板/字体（需 root 已建以创建字体）
        self.s = self.styles
        self.root.configure(bg=self.s.BG_DARKEST)
        f = self.s.fonts
        self.base_font = f["body"]
        self.bold_font = f["heading"]
        self._nav_keys: list[str] = []
        self._play_timer = None
        self._play_running = False
        self._build()
        self.render()

    # ── 构建 ──
    def _build(self) -> None:
        s, f = self.s, self.s.fonts
        _BTN = dict(bg=s.BTN_BG, fg=s.BTN_TEXT, activebackground=s.BTN_ACTIVE,
                    activeforeground=s.TEXT_BRIGHT, font=f["button"],
                    relief=tk.FLAT, padx=8, pady=3)

        # 顶栏：标题 + 导航按钮（纯鼠标）
        top = tk.Frame(self.root, bg=s.BG_DARK)
        top.pack(side=tk.TOP, fill=tk.X, padx=6, pady=4)
        tk.Label(top, text="上古卷轴 · 泰姆瑞尔编年史 (Legends Mode)",
                 fg=s.TEXT_SECONDARY, bg=s.BG_DARK, font=self.bold_font
                 ).pack(side=tk.LEFT)
        for txt, cmd in [("🎮游历", self._toggle_mode),
                         ("🆕新游戏", self._new_game),
                         ("🗺世界地图", self.reader.show_map),
                         ("←返回", self.reader.back),
                         ("⌂落地页", self.reader.home),
                         ("📷截图", self._screenshot)]:
            tk.Button(top, text=txt, command=cmd, **_BTN).pack(side=tk.RIGHT, padx=2)

        # 主体：左侧分类栏 + 中央文本区
        body = tk.Frame(self.root, bg=s.BG_DARKEST)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 左侧常驻分类栏
        side = tk.Frame(body, bg=s.BG_DARK, width=180)
        side.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)
        side.pack_propagate(False)
        tk.Label(side, text="— 分类 —", fg=s.TEXT_DIM, bg=s.BG_DARK,
                 font=f["small"], anchor="w"
                 ).pack(side=tk.TOP, fill=tk.X, padx=6, pady=(4, 2))
        self.nav_list = tk.Listbox(
            side, bg=s.BG_MEDIUM, fg=s.TEXT_PRIMARY, selectbackground=s.BTN_ACTIVE,
            selectforeground=s.TEXT_BRIGHT, relief=tk.FLAT, borderwidth=0,
            font=f["body"], activestyle=tk.NONE,
        )
        self.nav_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=2)
        for key, label, count in self.world.landing_categories():
            self._nav_keys.append(key)
            self.nav_list.insert(tk.END, f"  {label}  ({count})")
        self.nav_list.bind("<<ListboxSelect>>", self._on_nav)

        # 中央文本区
        text_frame = tk.Frame(body, bg=s.BG_DARKEST)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text = tk.Text(
            text_frame, bg=s.BG_DARKEST, fg=s.TEXT_PRIMARY, font=self.base_font,
            wrap=tk.WORD, relief=tk.FLAT, borderwidth=0,
            insertbackground=s.TEXT_PRIMARY, state=tk.DISABLED,
            padx=12, pady=8, spacing1=2, spacing3=2,
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=4)
        sb = tk.Scrollbar(text_frame, command=self.text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=sb.set)

        # 底部：鼠标操作提示（无键盘提示）
        self.footer = tk.Label(
            self.root, text="鼠标浏览：单击左侧分类，或单击正文中的蓝色超链接跳转",
            bg=s.BG_DARK, fg=s.TEXT_SECONDARY, font=f["small"], anchor="w")
        self.footer.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)

    # ── 导航 ──
    def _go(self, link) -> None:
        kind = link[0]
        if kind == "play":
            dispatch_play_action(self.play_state, link[1])
            self.render()
            return
        self.reader.navigate(link)
        self.render()

    # ── 存档续局 ──
    def _load_or_new(self) -> "PlayState":
        seed = self.world.meta.get("seed", 0)
        if self.play_save.has_save():
            try:
                st = PlayState.load_from(self.world, str(self.play_save.path))
                if st is not None:
                    st.save_path = str(self.play_save.path)
                    return st
            except Exception:
                print("[dwarf_scrolls] 续局存档读取失败，开新局：", file=sys.stderr)
                traceback.print_exc()
        st = PlayState(self.world, seed=seed)
        st.save_path = str(self.play_save.path)
        return st

    def _new_game(self) -> None:
        """清档重开一程全新的游历。"""
        self.play_save.clear()
        seed = self.world.meta.get("seed", 0)
        self.play_state = PlayState(self.world, seed=seed)
        self.play_state.save_path = str(self.play_save.path)
        if self.mode == "play":
            self.render()
        else:
            self.render()

    def _toggle_mode(self) -> None:
        if self.mode == "read":
            self.mode = "play"
            self.nav_list.config(state=tk.DISABLED)
            self._start_play_loop()
        else:
            self.mode = "read"
            self.nav_list.config(state=tk.NORMAL)
            self._stop_play_loop()
        self.render()

    # ── 游历主循环：引擎 FixedTimestepLoop 挂到 GUI 事件循环 ──
    def _start_play_loop(self) -> None:
        self._play_running = True
        self._play_tick()

    def _stop_play_loop(self) -> None:
        self._play_running = False
        if self._play_timer is not None:
            self.root.after_cancel(self._play_timer)
            self._play_timer = None

    def _play_tick(self) -> None:
        """每 250ms 经引擎 FixedTimestepLoop 推进世界时间，使生命/天数缓慢流动。"""
        if not self._play_running or self.play_state.dead:
            self._play_running = False
            return
        self.play_state.advance(0.25)
        self.render()
        self._play_timer = self.root.after(250, self._play_tick)

    def _current_view(self):
        if self.mode == "play":
            return build_play_view(self.play_state)
        return self.reader.view

    def _on_nav(self, event) -> None:
        sel = self.nav_list.curselection()
        if not sel:
            return
        key = self._nav_keys[sel[0]]
        if key == "map":
            self.reader.show_map()
        else:
            self.reader.navigate(("category", key))
        self.render()

    def _screenshot(self) -> None:
        """把当前画面（阅读或游历）截图保存到 shots/（程序内截图自检）。"""
        shot_dir = Path(__file__).resolve().parents[1] / "shots"
        shot_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = shot_dir / f"shot_{ts}.png"
        render_view_to_png(self._current_view(), str(path))
        self.footer.config(text=f"已截图：{path.name}")

    # ── 渲染 ──
    def render(self) -> None:
        s = self.s
        view = self._current_view()
        if self.mode == "play":
            self.footer.config(text="游历模式：点击省份或行动超链接游玩 · 截图 / 返回 / 落地页")
        else:
            self.footer.config(text="阅读模式：单击左侧分类，或单击正文中的蓝色超链接跳转")
        t = self.text
        for tag in t.tag_names():
            if tag.startswith(("c_", "l")):
                t.tag_delete(tag)
        t.config(state=tk.NORMAL)
        t.delete("1.0", tk.END)

        t.insert(tk.END, view.title + "\n", "title")
        t.tag_config("title", foreground=s.ACCENT_GOLD, font=self.bold_font)
        t.insert(tk.END, "\n")

        link_no = [0]
        for line in view.lines:
            for sp in line:
                self._insert_span(t, sp, link_no)
            t.insert(tk.END, "\n")
        t.config(state=tk.DISABLED)
        t.see("1.0")

    def _insert_span(self, t, sp, link_no) -> None:
        if sp.text == "":
            return
        start = t.index(tk.END)
        t.insert(tk.END, sp.text)
        end = t.index(tk.END)
        color = sp.color or "white"
        ctag = "c_" + color
        if ctag not in t.tag_names():
            t.tag_config(ctag, foreground=_ansi_to_hex(self.s, color))
        t.tag_add(ctag, start, end)
        if sp.is_link():
            link_no[0] += 1
            ltag = f"l{link_no[0]}"
            t.tag_config(ltag, foreground=self.s.ACCENT_BLUE, underline=True)
            t.tag_add(ltag, start, end)
            link = sp.link
            t.tag_bind(ltag, "<Button-1>", lambda e, l=link: self._go(l))
            t.tag_bind(ltag, "<Enter>", lambda e: t.config(cursor="hand2"))
            t.tag_bind(ltag, "<Leave>", lambda e: t.config(cursor=""))

    def run(self) -> None:
        self.root.mainloop()
