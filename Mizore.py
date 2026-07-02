import os
import shutil
import json
import tkinter as tk
import customtkinter as ctk
import tkinter.font as tkfont
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk

CONFIG_FILE = "config.json"


# ==========================================
# 紧凑、信息分级的高级分类卡片
# ==========================================
class CategoryCard(ctk.CTkFrame):
    def __init__(self, master, cat, font_family, colors, command, show_count=False):
        # 强制设置高度为 48，极大压缩垂直占位
        super().__init__(
            master,
            fg_color=colors["accent"],
            corner_radius=6,
            cursor="hand2",
            height=48,
        )
        self.colors = colors
        self.command = command
        self.show_count = show_count

        # 锁定内部组件不会撑大 Frame
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        name_str = cat["name"]
        if len(name_str) > 11:
            name_str = name_str[:10] + ".."

        self.lbl_name = ctk.CTkLabel(
            self,
            text=name_str,
            font=(font_family, 12, "bold"),
            text_color=colors["btn_text"],
            anchor="w",
        )
        self.lbl_name.grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 0)
        )

        hotkey_text = f"Key: {cat['hotkey'].upper()}"
        self.lbl_hotkey = ctk.CTkLabel(
            self,
            text=hotkey_text,
            font=(font_family, 11, "bold"),
            text_color="#fde047",
            anchor="w",
        )
        self.lbl_hotkey.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))

        if self.show_count and "count" in cat:
            self.lbl_count = ctk.CTkLabel(
                self,
                text=f"Qty: {cat['count']}",
                font=(font_family, 10),
                text_color="#e5e7eb",
                anchor="e",
            )
            self.lbl_count.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 4))

        widgets_to_bind = [self, self.lbl_name, self.lbl_hotkey]
        if hasattr(self, "lbl_count"):
            widgets_to_bind.append(self.lbl_count)

        for widget in widgets_to_bind:
            widget.bind("<Enter>", self.on_enter)
            widget.bind("<Leave>", self.on_leave)
            widget.bind("<Button-1>", self.on_click)

    def update_count(self, new_count):
        """【局部热更新】直接修改数字，不刷新整个面板"""
        if hasattr(self, "lbl_count"):
            self.lbl_count.configure(text=f"Qty: {new_count}")

    def on_enter(self, event):
        self.configure(fg_color=self.colors["accent_hover"])

    def on_leave(self, event):
        self.configure(fg_color=self.colors["accent"])

    def on_click(self, event):
        self.command()


class ImageSorterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mizore Sorter")
        self.geometry("1400x850")
        self.minsize(1000, 700)

        self.available_fonts = self.get_system_fonts()

        self.config = self.load_config()
        self.source_dir = self.config.get("source_dir", r"E:\Setu\Twitter")
        self.categories = self.config.get("categories", [])
        self.theme = self.config.get("theme", "Mizore")
        self.sort_method = self.config.get("sort_method", "default")

        self.font_family = self.config.get("font_family", "Microsoft YaHei")
        if self.font_family not in self.available_fonts:
            self.font_family = (
                "Microsoft YaHei"
                if "Microsoft YaHei" in self.available_fonts
                else self.available_fonts[0]
            )

        self.image_list = []
        self.current_index = 0
        self.current_pil_image = None
        self.main_container = None
        self.undo_stack = []

        self.category_buttons = []
        self.card_map = {}
        self._resize_timer = None
        self.tk_image = None

        # 尺寸锁定变量
        self.locked_w = None
        self.locked_h = None

        self.setup_ui_container()
        self.load_images()
        self.refresh_category_buttons()

        # 全局键盘事件绑定
        self.bind("<Key>", self.on_key_press)
        self.bind("<Control-z>", self.undo_last_move)
        self.bind("<Control-Z>", self.undo_last_move)

        self.update()
        self.show_image()

    def get_system_fonts(self):
        fonts = list(tkfont.families())
        clean_fonts = sorted(
            list(set([f for f in fonts if not f.startswith("@") and f.strip()]))
        )
        return clean_fonts if clean_fonts else ["Arial"]

    def load_config(self):
        default_cfg = {
            "source_dir": r"E:\Setu\Twitter",
            "theme": "Mizore",
            "font_family": "Microsoft YaHei",
            "sort_method": "default",
            "categories": [],
        }
        if not os.path.exists(CONFIG_FILE):
            return default_cfg
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, val in default_cfg.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception:
            return default_cfg

    def save_config(self):
        self.config["source_dir"] = self.source_dir
        self.config["categories"] = self.categories
        self.config["theme"] = self.theme
        self.config["font_family"] = self.font_family
        self.config["sort_method"] = self.sort_method
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get_theme_colors(self):
        if self.theme == "Mizore":
            return {
                "bg": "#f2f7fa",
                "frame_bg": "#ffffff",
                "accent": "#01acc6",
                "accent_hover": "#0091a8",
                "text": "#1a2b32",
                "btn_text": "#ffffff",
                "image_bg": "#111111",
            }
        elif self.theme == "Light":
            return {
                "bg": "#f9f9f9",
                "frame_bg": "#ebebeb",
                "accent": "#1f6aa5",
                "accent_hover": "#144870",
                "text": "#000000",
                "btn_text": "#ffffff",
                "image_bg": "#111111",
            }
        else:  # Dark
            return {
                "bg": "#15161a",
                "frame_bg": "#212226",
                "accent": "#1f6aa5",
                "accent_hover": "#144870",
                "text": "#ffffff",
                "btn_text": "#ffffff",
                "image_bg": "#000000",
            }

    def setup_ui_container(self):
        if self.main_container is not None:
            self.main_container.destroy()

        colors = self.get_theme_colors()
        ctk.set_appearance_mode("Dark" if self.theme == "Dark" else "Light")
        self.configure(fg_color=colors["bg"])

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill=ctk.BOTH, expand=True)
        self.setup_ui(colors)

    def setup_ui(self, colors):
        self.right_frame = ctk.CTkFrame(
            self.main_container,
            width=340,
            fg_color=colors["frame_bg"],
            corner_radius=12,
        )
        self.right_frame.pack_propagate(False)
        self.right_frame.pack(side=ctk.RIGHT, fill=ctk.Y, padx=(0, 15), pady=15)

        self.left_frame = ctk.CTkFrame(
            self.main_container, fg_color=colors["image_bg"], corner_radius=12
        )
        self.left_frame.pack_propagate(False)
        self.left_frame.pack(
            side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=15, pady=15
        )

        # 彻底移除左侧的自动大小监听，完全阻断自动改变产生的Bug
        self.image_canvas = tk.Canvas(
            self.left_frame, bg=colors["image_bg"], highlightthickness=0, bd=0
        )
        self.image_canvas.pack(fill=ctk.BOTH, expand=True)

        # --- 右侧面板内容 ---
        title_label = ctk.CTkLabel(
            self.right_frame,
            text="Mizore Sorter",
            font=(self.font_family, 24, "bold"),
            text_color=colors["accent"],
        )
        title_label.pack(pady=(20, 5))

        src_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        src_frame.pack(fill=ctk.X, padx=20, pady=5)
        ctk.CTkLabel(
            src_frame,
            text="当前图源:",
            font=(self.font_family, 12, "bold"),
            text_color=colors["text"],
        ).pack(side=ctk.LEFT)
        ctk.CTkButton(
            src_frame,
            text="变更路径",
            width=70,
            height=22,
            font=(self.font_family, 11),
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color=colors["btn_text"],
            command=self.change_source_dir,
        ).pack(side=ctk.RIGHT)

        self.src_label = ctk.CTkLabel(
            self.right_frame,
            text=self.source_dir,
            font=(self.font_family, 11),
            text_color="gray",
            wraplength=300,
            justify="left",
        )
        self.src_label.pack(padx=20, pady=(0, 10))

        self.tags_title = ctk.CTkLabel(
            self.right_frame,
            text="快捷标签",
            font=(self.font_family, 13, "bold"),
            text_color=colors["text"],
        )
        self.tags_title.pack(anchor="w", padx=20, pady=(10, 5))

        self.btn_container_frame = ctk.CTkScrollableFrame(
            self.right_frame, fg_color="transparent"
        )
        self.btn_container_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=5)

        sys_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        sys_frame.pack(side=ctk.BOTTOM, fill=ctk.X, padx=15, pady=15)

        # 【新增：手动刷新画面与标签管理并排布局】
        btn_row = ctk.CTkFrame(sys_frame, fg_color="transparent")
        btn_row.pack(fill=ctk.X, pady=(0, 12))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self.refresh_view_btn = ctk.CTkButton(
            btn_row,
            text="刷新画面",
            font=(self.font_family, 13, "bold"),
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color=colors["btn_text"],
            command=self.manual_refresh_image,
        )
        self.refresh_view_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.settings_btn = ctk.CTkButton(
            btn_row,
            text="标签管理",
            font=(self.font_family, 13, "bold"),
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color=colors["btn_text"],
            command=self.open_settings_window,
        )
        self.settings_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        drop_grid = ctk.CTkFrame(sys_frame, fg_color="transparent")
        drop_grid.pack(fill=ctk.X)
        drop_grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            drop_grid,
            text="界面主题:",
            font=(self.font_family, 11),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=5, pady=3, sticky="w")
        theme_menu = ctk.CTkOptionMenu(
            drop_grid,
            values=["Mizore", "Dark", "Light"],
            font=(self.font_family, 11),
            height=24,
            fg_color=colors["accent"],
            button_color=colors["accent"],
            button_hover_color=colors["accent_hover"],
            command=self.change_theme,
            variable=ctk.StringVar(value=self.theme),
        )
        theme_menu.grid(row=0, column=1, padx=5, pady=3, sticky="ew")

        ctk.CTkLabel(
            drop_grid,
            text="全局字体:",
            font=(self.font_family, 11),
            text_color=colors["text"],
        ).grid(row=1, column=0, padx=5, pady=3, sticky="w")
        font_combo = ctk.CTkComboBox(
            drop_grid,
            values=self.available_fonts,
            font=(self.font_family, 11),
            height=24,
            fg_color=colors["frame_bg"],
            border_color=colors["accent"],
            button_color=colors["accent"],
            button_hover_color=colors["accent_hover"],
            command=self.change_font,
            variable=ctk.StringVar(value=self.font_family),
        )
        font_combo.grid(row=1, column=1, padx=5, pady=3, sticky="ew")

        ctk.CTkLabel(
            drop_grid,
            text="标签排序:",
            font=(self.font_family, 11),
            text_color=colors["text"],
        ).grid(row=2, column=0, padx=5, pady=3, sticky="w")
        sort_str = (
            "默认顺序"
            if self.sort_method == "default"
            else "字母排序" if self.sort_method == "alpha" else "图片数量"
        )
        sort_menu = ctk.CTkOptionMenu(
            drop_grid,
            values=["默认顺序", "字母排序", "图片数量"],
            font=(self.font_family, 11),
            height=24,
            fg_color=colors["accent"],
            button_color=colors["accent"],
            button_hover_color=colors["accent_hover"],
            command=self.change_sort,
            variable=ctk.StringVar(value=sort_str),
        )
        sort_menu.grid(row=2, column=1, padx=5, pady=3, sticky="ew")

        self.progress_label = ctk.CTkLabel(
            self.right_frame,
            text="进度统计中...",
            font=(self.font_family, 12, "bold"),
            text_color=colors["text"],
            justify="center",
        )
        self.progress_label.pack(side=ctk.BOTTOM, pady=4)

    def manual_refresh_image(self):
        """完全手动控制：点击刷新时，清除尺寸锁并按照当前窗体大小重新绘制图像"""
        self.locked_w = None
        self.locked_h = None
        self.image_canvas.delete("all")
        self.update_image_display()

    def change_source_dir(self):
        new_dir = filedialog.askdirectory(
            title="选择源图片文件夹", initialdir=self.source_dir
        )
        if new_dir:
            self.source_dir = new_dir
            self.src_label.configure(text=self.source_dir)
            self.save_config()
            self.load_images()
            self.show_image()

    def change_theme(self, new_theme):
        self.theme = new_theme
        self.save_config()
        self.setup_ui_container()
        self.refresh_category_buttons()
        self.show_image()

    def change_font(self, new_font):
        if new_font in self.available_fonts or new_font.strip():
            self.font_family = new_font
            self.save_config()
            self.setup_ui_container()
            self.refresh_category_buttons()
            self.show_image()

    def change_sort(self, choice):
        if choice == "默认顺序":
            self.sort_method = "default"
        elif choice == "字母排序":
            self.sort_method = "alpha"
        elif choice == "图片数量":
            self.sort_method = "count"
        self.save_config()
        self.refresh_category_buttons()

    def refresh_category_buttons(self):
        for btn in self.category_buttons:
            btn.destroy()
        self.category_buttons.clear()
        self.card_map.clear()

        display_categories = []
        for cat in self.categories:
            cat_copy = cat.copy()
            if self.sort_method == "count":
                cat_copy["count"] = self.get_image_count(cat["path"])
            display_categories.append(cat_copy)

        if self.sort_method == "alpha":
            display_categories.sort(key=lambda x: x["name"].lower())
        elif self.sort_method == "count":
            display_categories.sort(key=lambda x: x["count"], reverse=True)

        self.btn_container_frame.grid_columnconfigure(0, weight=1)
        self.btn_container_frame.grid_columnconfigure(1, weight=1)

        colors = self.get_theme_colors()

        for idx, cat in enumerate(display_categories):
            r = idx // 2
            c = idx % 2

            card = CategoryCard(
                master=self.btn_container_frame,
                cat=cat,
                font_family=self.font_family,
                colors=colors,
                command=lambda ct=cat: self.move_image(ct),
                show_count=(self.sort_method == "count"),
            )
            card.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            self.category_buttons.append(card)
            self.card_map[cat["path"]] = card

    def get_image_count(self, path):
        if os.path.exists(path):
            valid_exts = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
            try:
                return sum(
                    1 for f in os.listdir(path) if f.lower().endswith(valid_exts)
                )
            except Exception:
                return 0
        return 0

    def open_settings_window(self):
        GridSettingWindow(self)

    def load_images(self):
        self.undo_stack.clear()
        if not os.path.exists(self.source_dir):
            self.image_list = []
            return
        valid_exts = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
        self.image_list = [
            f for f in os.listdir(self.source_dir) if f.lower().endswith(valid_exts)
        ]
        self.current_index = 0

    def show_image(self):
        self.update_progress_ui()
        self.image_canvas.delete("all")

        cw = self.locked_w if self.locked_w else self.left_frame.winfo_width()
        ch = self.locked_h if self.locked_h else self.left_frame.winfo_height()

        if not self.image_list:
            self.image_canvas.create_text(
                cw // 2,
                ch // 2,
                text="源文件夹中已无可用图片\n请放入新图片或更改图源目录",
                fill="gray",
                font=(self.font_family, 18),
                justify="center",
            )
            return

        if self.current_index >= len(self.image_list):
            self.image_canvas.create_text(
                cw // 2,
                ch // 2,
                text="任务达成！\n源文件夹所有图片已分类完毕！",
                fill="gray",
                font=(self.font_family, 18),
                justify="center",
            )
            return

        img_name = self.image_list[self.current_index]
        img_path = os.path.join(self.source_dir, img_name)

        try:
            self.current_pil_image = Image.open(img_path)
            self.update_image_display()
        except Exception:
            self.current_index += 1
            self.show_image()

    def update_progress_ui(self):
        if not self.image_list:
            self.progress_label.configure(text="待分类: 0  |  已分类: 0\n无图片")
            return
        pending = max(0, len(self.image_list) - self.current_index)
        classified = sum(self.get_image_count(cat["path"]) for cat in self.categories)
        if self.current_index < len(self.image_list):
            img_name = self.image_list[self.current_index]
            self.progress_label.configure(
                text=f"待分类: {pending}  |  已分类: {classified}\n当前文件: {img_name}"
            )
        else:
            self.progress_label.configure(
                text=f"待分类: 0  |  已分类: {classified}\n全部分类结束！"
            )

    def update_image_display(self):
        if not self.current_pil_image:
            return
        self.image_canvas.delete("all")

        if self.locked_w is None or self.locked_h is None:
            self.left_frame.update_idletasks()
            frame_w = self.left_frame.winfo_width()
            frame_h = self.left_frame.winfo_height()

            if frame_w > 10 and frame_h > 10:
                self.locked_w = frame_w
                self.locked_h = frame_h
            else:
                # 只有刚开机没画完时，做一次保底等待
                if self._resize_timer is not None:
                    self.after_cancel(self._resize_timer)
                self._resize_timer = self.after(30, self.update_image_display)
                return

        avail_w = self.locked_w - 30
        avail_h = self.locked_h - 30

        img_w, img_h = self.current_pil_image.size
        ratio = min(avail_w / img_w, avail_h / img_h)
        new_size = (max(1, int(img_w * ratio)), max(1, int(img_h * ratio)))

        resized_img = self.current_pil_image.resize(new_size, Image.Resampling.BILINEAR)
        self.tk_image = ImageTk.PhotoImage(resized_img)

        # 绝对定位：始终以当前锁定的长宽中心为坐标放置图像
        self.image_canvas.create_image(
            self.locked_w // 2, self.locked_h // 2, image=self.tk_image, anchor="center"
        )

    def on_key_press(self, event):
        if event.state & 0x0004:
            return
        pressed_key = event.keysym.lower()
        for cat in self.categories:
            if cat["hotkey"].lower() == pressed_key:
                self.move_image(cat)
                break

    def move_image(self, category):
        if self.current_index >= len(self.image_list):
            return

        img_name = self.image_list[self.current_index]
        src_path = os.path.join(self.source_dir, img_name)
        dest_folder = category["path"]
        dest_path = os.path.join(dest_folder, img_name)

        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        self.undo_stack.append((src_path, dest_path, self.current_index))

        try:
            shutil.move(src_path, dest_path)
            self.current_index += 1

            if self.sort_method == "count":
                new_count = self.get_image_count(dest_folder)
                if dest_folder in self.card_map:
                    self.card_map[dest_folder].update_count(new_count)

            self.show_image()
        except Exception as e:
            self.undo_stack.pop()
            messagebox.showerror("文件移动受阻", f"错误原因:\n{e}")

    def undo_last_move(self, event=None):
        if not self.undo_stack:
            return
        src_path, dest_path, previous_index = self.undo_stack.pop()

        if os.path.exists(dest_path):
            try:
                shutil.move(dest_path, src_path)
                self.current_index = previous_index

                dest_folder = os.path.dirname(dest_path)
                if self.sort_method == "count" and dest_folder in self.card_map:
                    new_count = self.get_image_count(dest_folder)
                    self.card_map[dest_folder].update_count(new_count)

                self.show_image()
            except Exception as e:
                messagebox.showerror("撤销失败", f"无法还原文件:\n{e}")


# ==========================================
# 标签管理窗口
# ==========================================
class GridSettingWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Mizore Sorter - 标签管理")
        self.geometry("880x600")
        self.grab_set()

        self.font_family = parent.font_family
        self.colors = parent.get_theme_colors()
        self.configure(fg_color=self.colors["bg"])

        self.dragged_row = None
        self.drag_start_y = 0

        title = ctk.CTkLabel(
            self,
            text="标签管理 (按住 [ = ] 可拖拽排序)",
            font=(self.font_family, 18, "bold"),
            text_color=self.colors["accent"],
        )
        title.pack(pady=15)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=5)

        self.scroll_frame.grid_columnconfigure(0, weight=0, minsize=40)
        self.scroll_frame.grid_columnconfigure(1, weight=3)
        self.scroll_frame.grid_columnconfigure(2, weight=1)
        self.scroll_frame.grid_columnconfigure(3, weight=5)
        self.scroll_frame.grid_columnconfigure(4, weight=1)
        self.scroll_frame.grid_columnconfigure(5, weight=1)

        headers = [
            "排序",
            "分类项目名称",
            "触发快捷键",
            "目标文件夹存放路径",
            "路径浏览",
            "操作",
        ]
        for i, h in enumerate(headers):
            lbl = ctk.CTkLabel(
                self.scroll_frame,
                text=h,
                font=(self.font_family, 12, "bold"),
                text_color=self.colors["text"],
            )
            lbl.grid(row=0, column=i, padx=5, pady=5, sticky="w" if 1 <= i <= 3 else "")

        self.table_rows = []
        for cat in self.parent.categories:
            self.add_row_to_grid(cat["name"], cat["hotkey"], cat["path"])
        if not self.parent.categories:
            self.add_row_to_grid("", "", "")

        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(fill=ctk.X, padx=20, pady=15)

        add_btn = ctk.CTkButton(
            bottom_bar,
            text="插入新标签行",
            font=(self.font_family, 12, "bold"),
            fg_color="#2fa572",
            hover_color="#107c41",
            command=lambda: self.add_row_to_grid("", "", ""),
        )
        add_btn.pack(side=ctk.LEFT, padx=5)

        save_btn = ctk.CTkButton(
            bottom_bar,
            text="保存并刷新系统",
            font=(self.font_family, 12, "bold"),
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color=self.colors["btn_text"],
            command=self.save_and_apply_grid,
        )
        save_btn.pack(side=ctk.RIGHT, padx=5)

    def redraw_grid(self):
        for index, row in enumerate(self.table_rows):
            actual_row = index + 1
            row["drag_widget"].grid(row=actual_row, column=0, padx=4, pady=4)
            row["name_widget"].grid(
                row=actual_row, column=1, padx=4, pady=4, sticky="ew"
            )
            row["hotkey_widget"].grid(
                row=actual_row, column=2, padx=4, pady=4, sticky="ew"
            )
            row["path_widget"].grid(
                row=actual_row, column=3, padx=4, pady=4, sticky="ew"
            )
            row["br_btn"].grid(row=actual_row, column=4, padx=4, pady=4)
            row["del_btn"].grid(row=actual_row, column=5, padx=4, pady=4)

    def on_drag_start(self, event, row_record):
        self.dragged_row = row_record
        self.drag_start_y = event.y_root
        row_record["drag_widget"].configure(text_color=self.colors["accent"])

    def on_drag_motion(self, event):
        if not self.dragged_row:
            return
        y_offset = event.y_root - self.drag_start_y
        row_height = 36
        current_idx = self.table_rows.index(self.dragged_row)

        if y_offset > row_height and current_idx < len(self.table_rows) - 1:
            self.table_rows[current_idx], self.table_rows[current_idx + 1] = (
                self.table_rows[current_idx + 1],
                self.table_rows[current_idx],
            )
            self.drag_start_y += row_height
            self.redraw_grid()
        elif y_offset < -row_height and current_idx > 0:
            self.table_rows[current_idx], self.table_rows[current_idx - 1] = (
                self.table_rows[current_idx - 1],
                self.table_rows[current_idx],
            )
            self.drag_start_y -= row_height
            self.redraw_grid()

    def on_drag_release(self, event):
        if self.dragged_row:
            self.dragged_row["drag_widget"].configure(text_color="gray")
            self.dragged_row = None

    def add_row_to_grid(self, name="", hotkey="", path=""):
        row_record = {}
        drag_lbl = ctk.CTkLabel(
            self.scroll_frame,
            text="[ = ]",
            font=(self.font_family, 14, "bold"),
            text_color="gray",
            cursor="hand2",
        )
        drag_lbl.bind("<Button-1>", lambda e, r=row_record: self.on_drag_start(e, r))
        drag_lbl.bind("<B1-Motion>", self.on_drag_motion)
        drag_lbl.bind("<ButtonRelease-1>", self.on_drag_release)

        name_ent = ctk.CTkEntry(self.scroll_frame, font=(self.font_family, 12))
        name_ent.insert(0, name)

        hk_ent = ctk.CTkEntry(
            self.scroll_frame, font=(self.font_family, 12), justify="center"
        )
        hk_ent.insert(0, hotkey)

        path_ent = ctk.CTkEntry(self.scroll_frame, font=(self.font_family, 12))
        path_ent.insert(0, path)

        br_btn = ctk.CTkButton(
            self.scroll_frame,
            text="浏览...",
            width=55,
            height=26,
            font=(self.font_family, 11),
            fg_color="#5c6b73",
            hover_color="#3d4a50",
            command=lambda pe=path_ent: self.browse_row_path(pe),
        )

        del_btn = ctk.CTkButton(
            self.scroll_frame,
            text="删除行",
            width=55,
            height=26,
            font=(self.font_family, 11),
            fg_color="#c42b1c",
            hover_color="#a80000",
            command=lambda rr=row_record: self.delete_row_from_grid(rr),
        )

        row_record.update(
            {
                "drag_widget": drag_lbl,
                "name_widget": name_ent,
                "hotkey_widget": hk_ent,
                "path_widget": path_ent,
                "br_btn": br_btn,
                "del_btn": del_btn,
                "all_widgets": [drag_lbl, name_ent, hk_ent, path_ent, br_btn, del_btn],
            }
        )

        self.table_rows.append(row_record)
        self.redraw_grid()

    def browse_row_path(self, path_entry):
        folder = filedialog.askdirectory(title="选择对应的图片存放目标文件夹")
        if folder:
            path_entry.delete(0, ctk.END)
            path_entry.insert(0, folder)

    def delete_row_from_grid(self, row_record):
        for w in row_record["all_widgets"]:
            w.destroy()
        self.table_rows.remove(row_record)
        self.redraw_grid()

    def save_and_apply_grid(self):
        updated_categories = []
        used_hotkeys = set()
        for row in self.table_rows:
            name = row["name_widget"].get().strip()
            hotkey = row["hotkey_widget"].get().strip().lower()
            path = row["path_widget"].get().strip()

            if not name and not hotkey and not path:
                continue
            if not name or not hotkey or not path:
                messagebox.showerror(
                    "保存失败",
                    "每一行中的 [名称]、[快捷键] 和 [路径] 必须同时填写完整！",
                )
                return
            if hotkey in used_hotkeys:
                messagebox.showerror(
                    "热键冲突",
                    f"快捷键 '{hotkey.upper()}' 在列表中被重复分配，请修正！",
                )
                return

            used_hotkeys.add(hotkey)
            updated_categories.append({"name": name, "hotkey": hotkey, "path": path})

        self.parent.categories = updated_categories
        self.parent.save_config()
        self.parent.refresh_category_buttons()
        self.parent.update_progress_ui()
        messagebox.showinfo("成功", "配置已保存")
        self.destroy()


if __name__ == "__main__":
    app = ImageSorterApp()
    app.mainloop()
