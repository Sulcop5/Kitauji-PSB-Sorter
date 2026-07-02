# ==============
# Nozomi Viewer
# ==============

import os
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from collections import OrderedDict
from PIL import Image, ImageTk

# --- 高清修复：强制开启 Windows 硬件级 High-DPI 高清字形渲染 ---
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

ROOT_DIR = r"E:\Setu"
# 修正后缀名
VALID_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")

# --- 完美对齐 Sorter 主题配色 ---
THEMES = {
    "Nozomi": {
        "bg_main": "#f2f7fa",
        "bg_panel": "#ffffff",
        "bg_tag": "#e8f3f7",
        "text_main": "#1a2b32",
        "text_muted": "#657b85",
        "accent": "#01acc6",
        "tag_selected": "#d0eff4",
    },
    "Light": {
        "bg_main": "#f9f9f9",
        "bg_panel": "#ebebeb",
        "bg_tag": "#ffffff",
        "text_main": "#000000",
        "text_muted": "#7f8c8d",
        "accent": "#1f6aa5",
        "tag_selected": "#d4e6f1",
    },
    "Dark": {
        "bg_main": "#15161a",
        "bg_panel": "#212226",
        "bg_tag": "#2d2e33",
        "text_main": "#ffffff",
        "text_muted": "#8a8b91",
        "accent": "#1f6aa5",
        "tag_selected": "#2a3a4a",
    },
}


class LRUCache:
    """简易的容量受限的LRU缓存，防止图片加载过多撑爆内存"""

    def __init__(self, capacity=500):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()


class NozomiViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nozomi Viewer")
        self.geometry("1340x840")
        self.minsize(1000, 700)

        self.current_theme_name = "Nozomi"
        self.current_images = []
        self.current_index = 0
        self.view_mode = "single"  # 【新特性】默认以单图模式启动
        self.card_size = 160
        self.selected_tag_path = ""

        self.tags_data = []
        self.scanned_tags_data = []

        self.thumb_cache = LRUCache(capacity=600)
        self.full_img_cache = LRUCache(capacity=10)

        self.loaded_limit = 0
        self.current_rendered = 0
        self.sort_method = "默认顺序"
        self._resize_job = None

        if not os.path.exists(ROOT_DIR):
            messagebox.showerror("错误", f"找不到目录: {ROOT_DIR}")
            self.destroy()
            return

        self.scan_tags_and_counts()
        self.setup_ui()
        self.apply_theme(self.current_theme_name)
        self.bind_global_events()

    def scan_tags_and_counts(self):
        self.tags_data = []
        for root, dirs, files in os.walk(ROOT_DIR):
            img_count = sum(1 for f in files if f.lower().endswith(VALID_EXTENSIONS))
            if img_count > 0:
                folder_name = os.path.basename(root) if root != ROOT_DIR else "根目录"
                self.tags_data.append((root, folder_name, img_count))

        self.scanned_tags_data = list(self.tags_data)
        self.sort_tags()

    def sort_tags(self):
        if self.sort_method == "字母排序":
            self.tags_data.sort(key=lambda x: x[1].lower())
        elif self.sort_method == "图片数量":
            self.tags_data.sort(key=lambda x: x[2], reverse=True)
        else:
            self.tags_data = list(self.scanned_tags_data)

    def refresh_data(self):
        """【新特性】全局刷新机制：硬盘文件变动后同步数据"""
        self.scan_tags_and_counts()
        self.render_rounded_tags()

        if self.selected_tag_path and os.path.exists(self.selected_tag_path):
            # 重新读取当前文件夹
            scanned_images = [
                os.path.join(self.selected_tag_path, f)
                for f in os.listdir(self.selected_tag_path)
                if f.lower().endswith(VALID_EXTENSIONS)
            ]
            scanned_images.sort(key=lambda x: os.path.basename(x).lower(), reverse=True)
            self.current_images = scanned_images

            if self.current_images:
                # 限制索引越界
                self.current_index = min(
                    self.current_index, len(self.current_images) - 1
                )
                if self.view_mode == "gallery":
                    self.show_gallery()
                else:
                    self.show_single_image(self.current_index)
            else:
                self.clear_content_frame()
        else:
            self.clear_content_frame()

    def get_thumbnail(self, path, size):
        """【性能革命】画廊极速加载模式：使用 draft 和 NEAREST 算法"""
        cache_key = f"{path}_{size}"
        thumb = self.thumb_cache.get(cache_key)
        if not thumb:
            try:
                with Image.open(path) as img:
                    # draft机制：让解码器只读取指定大小的数据（对JPEG速度提升极其恐怖）
                    img.draft("RGB", (size, size))
                    # NEAREST是最快的缩放算法，适用于小画廊卡片
                    img.thumbnail((size, size), Image.Resampling.NEAREST)
                    thumb = ImageTk.PhotoImage(img)
                    self.thumb_cache.put(cache_key, thumb)
            except Exception:
                return None
        return thumb

    def get_full_image(self, path):
        """单图模式：保留高质量原始数据加载"""
        img = self.full_img_cache.get(path)
        if not img:
            try:
                img = Image.open(path)
                self.full_img_cache.put(path, img)
            except Exception:
                return None
        return img

    def setup_ui(self):
        # -- 右侧控制面板 --
        self.right_panel = tk.Frame(self, width=280)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_panel.pack_propagate(False)

        # 1. 主题栏
        self.theme_bar = tk.Frame(self.right_panel, height=45)
        self.theme_bar.pack(side=tk.TOP, fill=tk.X, pady=5)
        for t_name in THEMES.keys():
            btn = tk.Button(
                self.theme_bar,
                text=t_name,
                font=("Microsoft YaHei", 9),
                bd=0,
                cursor="hand2",
                command=lambda n=t_name: self.apply_theme(n),
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=2, pady=2)

        # 2. 排序与刷新栏 (并排布局)
        self.sort_bar = tk.Frame(self.right_panel, height=35)
        self.sort_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 5), padx=10)

        self.btn_refresh = tk.Button(
            self.sort_bar,
            text="⟳ 刷新",
            font=("Microsoft YaHei", 9, "bold"),
            bd=0,
            cursor="hand2",
            command=self.refresh_data,
        )
        self.btn_refresh.pack(side=tk.RIGHT, padx=(5, 0), ipadx=8)

        self.sort_var = tk.StringVar(value="默认顺序")
        self.sort_combo = ttk.Combobox(
            self.sort_bar,
            textvariable=self.sort_var,
            values=["默认顺序", "字母排序", "图片数量"],
            state="readonly",
            font=("Microsoft YaHei", 9),
        )
        self.sort_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.sort_combo.bind("<<ComboboxSelected>>", self.on_sort_changed)

        # 3. 标签画布
        self.tag_canvas = tk.Canvas(self.right_panel, highlightthickness=0)
        self.tag_scrollbar = ttk.Scrollbar(
            self.right_panel,
            orient="vertical",
            command=self.tag_canvas.yview,
            style="Custom.Vertical.TScrollbar",
        )
        self.tag_container = tk.Frame(self.tag_canvas)
        self.tag_container.bind(
            "<Configure>",
            lambda e: self.tag_canvas.configure(
                scrollregion=self.tag_canvas.bbox("all")
            ),
        )
        self.tag_canvas.create_window(
            (0, 0), window=self.tag_container, anchor="nw", width=260
        )
        self.tag_canvas.configure(yscrollcommand=self.tag_scrollbar.set)
        self.tag_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.tag_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # -- 左侧工作区 (重构以支持顶部常驻控制条) --
        self.left_frame = tk.Frame(self)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.top_control_bar = tk.Frame(self.left_frame, height=45)
        self.top_control_bar.pack(side=tk.TOP, fill=tk.X)
        self.top_control_bar.pack_propagate(False)

        self.lbl_tag_title = tk.Label(
            self.top_control_bar,
            text="Nozomi Viewer - 就绪",
            font=("Microsoft YaHei", 12, "bold"),
        )
        self.lbl_tag_title.pack(side=tk.LEFT, padx=20)

        self.btn_toggle_mode = tk.Button(
            self.top_control_bar,
            text="⊞ 画廊模式",
            font=("Microsoft YaHei", 9, "bold"),
            bd=0,
            cursor="hand2",
            command=self.toggle_view_mode,
        )
        self.btn_toggle_mode.pack(side=tk.RIGHT, padx=20, pady=8, ipadx=10)

        self.content_frame = tk.Frame(self.left_frame)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 鼠标滚动事件分发
        self.tag_canvas.bind("<Enter>", lambda e: self.bind_wheel(self.on_tags_scroll))
        self.tag_canvas.bind("<Leave>", lambda e: self.unbind_wheel())
        self.content_frame.bind(
            "<Enter>", lambda e: self.bind_wheel(self.on_gallery_scroll)
        )
        self.content_frame.bind("<Leave>", lambda e: self.unbind_wheel())

    def bind_wheel(self, command):
        self.bind_all("<MouseWheel>", command)
        self.bind_all("<Button-4>", command)
        self.bind_all("<Button-5>", command)

    def unbind_wheel(self):
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def on_sort_changed(self, event=None):
        self.sort_method = self.sort_var.get()
        self.sort_tags()
        self.render_rounded_tags()

    def toggle_view_mode(self):
        """【新特性】一键丝滑切换查看模式"""
        if not self.current_images:
            return
        if self.view_mode == "single":
            self.show_gallery()
        else:
            self.show_single_image(self.current_index)

    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.lbl_tag_title.config(text="无内容")

    def apply_theme(self, theme_name):
        self.current_theme_name = theme_name
        c = THEMES[theme_name]

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Custom.Vertical.TScrollbar",
            troughcolor=c["bg_panel"],
            background=c["bg_tag"],
            arrowcolor=c["accent"],
            bordercolor=c["bg_panel"],
            shadowcolor=c["bg_panel"],
            darkcolor=c["bg_panel"],
            lightcolor=c["bg_panel"],
            gripthickness=0,
            borderwidth=0,
        )
        style.configure(
            "TCombobox",
            fieldbackground=c["bg_tag"],
            background=c["bg_panel"],
            foreground=c["text_main"],
            arrowcolor=c["accent"],
            bordercolor=c["bg_panel"],
        )
        style.map("TCombobox", fieldbackground=[("readonly", c["bg_tag"])])
        style.map("TCombobox", selectbackground=[("readonly", c["bg_tag"])])
        style.map("TCombobox", selectforeground=[("readonly", c["text_main"])])

        self.configure(bg=c["bg_main"])
        self.right_panel.configure(bg=c["bg_panel"])
        self.theme_bar.configure(bg=c["bg_panel"])
        self.sort_bar.configure(bg=c["bg_panel"])
        self.tag_canvas.configure(bg=c["bg_panel"])
        self.tag_container.configure(bg=c["bg_panel"])
        self.left_frame.configure(bg=c["bg_main"])
        self.top_control_bar.configure(bg=c["bg_panel"])
        self.content_frame.configure(bg=c["bg_main"])
        self.lbl_tag_title.configure(bg=c["bg_panel"], fg=c["accent"])
        self.btn_toggle_mode.configure(
            bg=c["bg_tag"],
            fg=c["text_main"],
            activebackground=c["accent"],
            activeforeground=c["bg_panel"],
        )
        self.btn_refresh.configure(
            bg=c["accent"], fg=c["bg_panel"], activebackground=c["accent"]
        )

        for widget in self.theme_bar.winfo_children():
            if widget.cget("text") == theme_name:
                widget.configure(
                    bg=c["accent"], fg=c["bg_panel"], activebackground=c["accent"]
                )
            else:
                widget.configure(
                    bg=c["bg_tag"], fg=c["text_main"], activebackground=c["bg_tag"]
                )

        self.render_rounded_tags()
        if self.current_images:
            if self.view_mode == "gallery":
                self.show_gallery()
            else:
                self.show_single_image(self.current_index)

    def draw_rounded_rectangle(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius,
            y1,
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def render_rounded_tags(self):
        """【UI优化】彻底剔除 Emoji 和多余符号，采用现代极简扁平排版"""
        for widget in self.tag_container.winfo_children():
            widget.destroy()

        c = THEMES[self.current_theme_name]
        for idx, (path, name, count) in enumerate(self.tags_data):
            tag_cv = tk.Canvas(
                self.tag_container,
                height=42,
                bg=c["bg_panel"],
                highlightthickness=0,
                cursor="hand2",
            )
            tag_cv.pack(fill=tk.X, pady=4, padx=5)

            is_selected = path == self.selected_tag_path
            bg_color = c["tag_selected"] if is_selected else c["bg_tag"]
            text_color = c["accent"] if is_selected else c["text_main"]

            self.draw_rounded_rectangle(
                tag_cv, 2, 2, 248, 38, radius=12, fill=bg_color, outline=""
            )

            # 纯净文本截断，无乱码隐患
            display_text = name[:18] + ("..." if len(name) > 18 else "")

            tag_cv.create_text(
                15,
                20,
                text=display_text,
                anchor="w",
                fill=text_color,
                font=("Microsoft YaHei", 10, "bold"),
            )
            tag_cv.create_text(
                235,
                20,
                text=f"[{count}]",
                anchor="e",
                fill=c["text_muted"],
                font=("Consolas", 10, "bold"),
            )

            tag_cv.bind(
                "<Button-1>", lambda e, p=path, n=name: self.on_tag_clicked(p, n)
            )

    def on_tag_clicked(self, path, name):
        self.selected_tag_path = path
        self.thumb_cache.clear()
        self.render_rounded_tags()

        scanned_images = [
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.lower().endswith(VALID_EXTENSIONS)
        ]
        scanned_images.sort(key=lambda x: os.path.basename(x).lower(), reverse=True)

        self.current_images = scanned_images
        self.lbl_tag_title.config(text=f"📁 {name}  ({len(self.current_images)}张)")

        if self.current_images:
            self.loaded_limit = 40
            self.current_rendered = 0
            # 【新特性】初次点进标签，强行使用单图模式秒开
            self.show_single_image(0)
        else:
            self.clear_content_frame()

    def get_wheel_delta(self, event):
        if event.num == 4:
            return -1
        if event.num == 5:
            return 1
        return int(-1 * (event.delta / 120))

    def on_tags_scroll(self, event):
        self.tag_canvas.yview_scroll(self.get_wheel_delta(event), "units")

    def on_gallery_scroll(self, event):
        if self.view_mode != "gallery":
            return
        if not (event.state & 0x0004):
            self.gal_canvas.yview_scroll(self.get_wheel_delta(event), "units")
            self.check_lazy_load()

    def on_canvas_scroll(self, *args):
        self.gal_scrollbar.set(*args)
        self.check_lazy_load()

    def check_lazy_load(self):
        if self.view_mode != "gallery" or not hasattr(self, "gal_canvas"):
            return
        try:
            _, bottom = self.gal_canvas.yview()
            if bottom >= 0.85 and self.current_rendered < len(self.current_images):
                self.loaded_limit = min(
                    self.loaded_limit + 40, len(self.current_images)
                )
                self.render_gallery_append()
        except Exception:
            pass

    def on_ctrl_wheel_zoom(self, event):
        if self.view_mode != "gallery":
            return
        delta = self.get_wheel_delta(event)
        if delta < 0:
            self.card_size = min(400, self.card_size + 20)
        else:
            self.card_size = max(80, self.card_size - 20)
        self.render_gallery_full()

    def on_left_frame_resize(self, event):
        if self.view_mode == "gallery" and self.current_images:
            if hasattr(self, "_resize_job") and self._resize_job:
                self.after_cancel(self._resize_job)
            self._resize_job = self.after(150, self.render_gallery_full)

    def show_gallery(self):
        self.view_mode = "gallery"
        self.btn_toggle_mode.config(text="🖽 单图模式")

        for widget in self.content_frame.winfo_children():
            widget.destroy()
        c = THEMES[self.current_theme_name]

        if not self.current_images:
            return

        self.gal_canvas = tk.Canvas(
            self.content_frame, bg=c["bg_main"], highlightthickness=0
        )
        self.gal_scrollbar = ttk.Scrollbar(
            self.content_frame,
            orient="vertical",
            command=self.gal_canvas.yview,
            style="Custom.Vertical.TScrollbar",
        )
        self.gal_container = tk.Frame(self.gal_canvas, bg=c["bg_main"])
        self.gal_container.bind(
            "<Configure>",
            lambda e: self.gal_canvas.configure(
                scrollregion=self.gal_canvas.bbox("all")
            ),
        )

        self.gal_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.gal_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas_window_id = self.gal_canvas.create_window(
            (0, 0), window=self.gal_container, anchor="n"
        )
        self.gal_canvas.configure(yscrollcommand=self.on_canvas_scroll)

        self.render_gallery_full()

    def render_gallery_full(self):
        if self.view_mode != "gallery" or not hasattr(self, "gal_container"):
            return

        self.update_idletasks()
        w = self.content_frame.winfo_width()
        available_w = w if w > 10 else 950
        self.gal_canvas.coords(self.canvas_window_id, available_w // 2, 0)
        self.gal_canvas.itemconfig(self.canvas_window_id, width=available_w)

        for widget in self.gal_container.winfo_children():
            widget.destroy()
        self.current_rendered = 0
        self.render_gallery_append(available_w)

    def render_gallery_append(self, available_w=None):
        if available_w is None:
            available_w = self.content_frame.winfo_width()

        padding = 12
        columns = max(1, available_w // (self.card_size + padding * 2))
        for col in range(columns):
            self.gal_container.grid_columnconfigure(col, weight=1)

        bg_color = THEMES[self.current_theme_name]["bg_main"]
        start_idx = self.current_rendered
        end_idx = min(self.loaded_limit, len(self.current_images))

        for idx in range(start_idx, end_idx):
            img_path = self.current_images[idx]
            photo = self.get_thumbnail(img_path, self.card_size)
            if not photo:
                continue

            cell = tk.Frame(self.gal_container, bg=bg_color, cursor="hand2")
            cell.grid(
                row=idx // columns,
                column=idx % columns,
                padx=padding,
                pady=padding,
                sticky="nsew",
            )

            lbl = tk.Label(cell, image=photo, bg=bg_color)
            lbl.image = photo
            lbl.pack(expand=True)
            lbl.bind("<Button-1>", lambda e, i=idx: self.show_single_image(i))

        self.current_rendered = end_idx

    def show_single_image(self, index):
        if not self.current_images or index < 0 or index >= len(self.current_images):
            return
        self.view_mode = "single"
        self.current_index = index
        self.btn_toggle_mode.config(text="⊞ 画廊模式")

        for widget in self.content_frame.winfo_children():
            widget.destroy()
        c = THEMES[self.current_theme_name]
        img_path = self.current_images[index]

        self.canvas_single = tk.Canvas(
            self.content_frame, bg=c["bg_main"], highlightthickness=0
        )
        self.canvas_single.pack(fill=tk.BOTH, expand=True)

        bot_bar = tk.Frame(self.content_frame, bg=c["bg_panel"], height=42)
        bot_bar.pack(side=tk.BOTTOM, fill=tk.X)
        bot_bar.pack_propagate(False)

        # 单图模式底部的快捷切换按钮
        tk.Button(
            bot_bar,
            text="⊞ 切换画廊",
            font=("Microsoft YaHei", 9),
            bg=c["bg_tag"],
            fg=c["text_main"],
            bd=0,
            cursor="hand2",
            command=self.show_gallery,
        ).pack(side=tk.LEFT, padx=15, pady=5)

        filename = os.path.basename(img_path)
        tk.Label(
            bot_bar,
            text=f"[{index+1}/{len(self.current_images)}]  {filename}",
            bg=c["bg_panel"],
            fg=c["text_muted"],
            font=("Consolas", 9),
        ).pack(side=tk.LEFT, padx=25)

        tk.Button(
            bot_bar,
            text="纠错移动 ➔",
            font=("Microsoft YaHei", 9, "bold"),
            bg=c["bg_tag"],
            fg=c["accent"],
            bd=0,
            cursor="hand2",
            command=lambda: self.quick_move_image(img_path),
        ).pack(side=tk.RIGHT, padx=15, pady=5)

        self.canvas_single.bind(
            "<Configure>",
            lambda e: self.resize_single_image(img_path, e.width, e.height),
        )

    def resize_single_image(self, img_path, w, h):
        """单图模式：高画质重采样渲染"""
        if w <= 10 or h <= 10:
            return
        try:
            img = self.get_full_image(img_path)
            if img is None:
                return

            img_w, img_h = img.size
            ratio = min((w - 20) / img_w, (h - 20) / img_h)
            new_size = (max(1, int(img_w * ratio)), max(1, int(img_h * ratio)))

            resized = img.resize(new_size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized)

            self.canvas_single.delete("all")
            self.canvas_single.create_image(
                w // 2, h // 2, image=photo, anchor="center"
            )
            self.canvas_single.image = photo
        except Exception:
            pass

    def prev_image(self):
        if self.view_mode == "single":
            self.show_single_image(self.current_index - 1)

    def next_image(self):
        if self.view_mode == "single":
            self.show_single_image(self.current_index + 1)

    def quick_move_image(self, src_path):
        c = THEMES[self.current_theme_name]
        move_win = tk.Toplevel(self)
        move_win.title("移动纠错")
        move_win.geometry("360x460")
        move_win.configure(bg=c["bg_panel"])
        move_win.grab_set()

        tk.Label(
            move_win,
            text="选择正确的目标标签",
            bg=c["bg_panel"],
            fg=c["text_main"],
            font=("Microsoft YaHei", 11, "bold"),
        ).pack(pady=15)
        f_list = tk.Frame(move_win, bg=c["bg_panel"])
        f_list.pack(fill=tk.BOTH, expand=True, padx=20)

        sb = ttk.Scrollbar(
            f_list, orient="vertical", style="Custom.Vertical.TScrollbar"
        )
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(
            f_list,
            yscrollcommand=sb.set,
            font=("Microsoft YaHei", 10),
            bg=c["bg_main"],
            fg=c["text_main"],
            selectbackground=c["bg_tag"],
            selectforeground=c["accent"],
            borderwidth=0,
            highlightthickness=0,
        )
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=lb.yview)

        # 同样剥离表情符号
        for _, name, _ in self.tags_data:
            lb.insert(tk.END, f"  {name}")

        def do_move():
            sel = lb.curselection()
            if not sel:
                return
            dest_path = os.path.join(
                self.tags_data[sel[0]][0], os.path.basename(src_path)
            )
            if os.path.exists(dest_path):
                messagebox.showwarning(
                    "提示", "目标位置已存在同名文件", parent=move_win
                )
                return

            try:
                shutil.move(src_path, dest_path)
                move_win.destroy()

                self.current_images.pop(self.current_index)

                # 移动完顺便全局刷新一下侧边栏数字
                self.scan_tags_and_counts()
                self.render_rounded_tags()

                if not self.current_images:
                    self.clear_content_frame()
                else:
                    self.show_single_image(
                        min(self.current_index, len(self.current_images) - 1)
                    )
            except Exception as e:
                messagebox.showerror("错误", f"移动失败: {e}", parent=move_win)

        tk.Button(
            move_win,
            text="确 认 移 动",
            font=("Microsoft YaHei", 10, "bold"),
            bg=c["accent"],
            fg=c["bg_panel"],
            bd=0,
            cursor="hand2",
            command=do_move,
        ).pack(pady=20, ipadx=20, ipady=5)
        lb.bind("<Double-1>", lambda e: do_move())

    def bind_global_events(self):
        self.bind("<Control-c>", self.copy_to_clipboard)
        self.bind("<Control-C>", self.copy_to_clipboard)
        self.bind("<Left>", lambda e: self.prev_image())
        self.bind("<Right>", lambda e: self.next_image())
        self.bind("<Control-MouseWheel>", self.on_ctrl_wheel_zoom)
        self.bind("<Configure>", self.on_left_frame_resize)

    def copy_to_clipboard(self, event=None):
        if self.view_mode != "single":
            return
        c = THEMES[self.current_theme_name]
        try:
            subprocess.run(
                [
                    "powershell",
                    "-command",
                    f"Set-Clipboard -Path '{self.current_images[self.current_index]}'",
                ],
                check=True,
                creationflags=0x08000000,
            )
            toast = tk.Label(
                self.content_frame,
                text="已复制到剪贴板",
                bg=c["bg_panel"],
                fg=c["accent"],
                font=("Microsoft YaHei", 9),
                padx=10,
                pady=5,
            )
            toast.place(relx=0.03, rely=0.88)
            self.after(1200, toast.destroy)
        except Exception:
            pass


if __name__ == "__main__":
    app = NozomiViewer()
    app.mainloop()
