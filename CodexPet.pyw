from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
import random
import sys
import traceback
from pathlib import Path

import tkinter as tk
from PIL import Image, ImageTk


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = BASE_DIR

ASSET_DIR = RESOURCE_DIR / "assets"
SPRITESHEET = ASSET_DIR / "spritesheet.webp"
STATE_FILE = BASE_DIR / "pet-state.json"
LOG_FILE = BASE_DIR / "pet-error.log"

TRANSPARENT_COLOR = "#ff00ff"
COLS = 8
STATES = [
    ("idle", 180),
    ("running-right", 80),
    ("running-left", 80),
    ("waving", 110),
    ("jumping", 110),
    ("failed", 170),
    ("waiting", 180),
    ("running", 115),
    ("review", 150),
]
RANDOM_STATES = ["waving", "jumping", "waiting", "running", "review"]
RANDOM_INTERVAL_MS = 60_000
RANDOM_DURATION_MS = 4_000
MIN_SCALE = 0.5
MAX_SCALE = 2.0
ALPHA_THRESHOLD = 18
LIVE_SCALE_QUANTUM = 0.01
FRAME_CACHE_LIMIT = 16

RESIZE_HANDLE_SIZE = 30
RESIZE_HANDLE_RADIUS = 11
RESIZE_NEAR_MARGIN = 54
RESIZE_POLL_MS = 90

MENU_WIDTH = 236
MENU_PADDING = 10
MENU_ITEM_HEIGHT = 36
MENU_SEPARATOR_HEIGHT = 10
MENU_RADIUS = 22
MENU_BG = "#f7f8fb"
MENU_BORDER = "#d8dce5"
MENU_HOVER = "#ffffff"
MENU_TEXT = "#141820"
MENU_MUTED = "#5b6472"


class ACCENTPOLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint32),
        ("AnimationId", ctypes.c_int),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def set_dpi_aware() -> None:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def set_rounded_window(window: tk.Toplevel, width: int, height: int, radius: int) -> None:
    try:
        hwnd = wintypes.HWND(window.winfo_id())
        region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, radius, radius)
        if region:
            ctypes.windll.user32.SetWindowRgn(hwnd, region, True)
    except Exception:
        pass


def enable_acrylic(window: tk.Toplevel, alpha: int = 210) -> bool:
    try:
        setter = ctypes.windll.user32.SetWindowCompositionAttribute
        hwnd = wintypes.HWND(window.winfo_id())
        accent = ACCENTPOLICY()
        accent.AccentState = 4
        accent.AccentFlags = 2
        accent.GradientColor = (alpha << 24) | (248 << 16) | (248 << 8) | 248
        accent.AnimationId = 0

        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)
        return bool(setter(hwnd, ctypes.byref(data)))
    except Exception:
        return False


def create_round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs):
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **kwargs)


def claim_single_instance():
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, "CodexPetStandalone_eoe_un")
        if handle and kernel32.GetLastError() == 183:
            sys.exit(0)
        return handle
    except Exception:
        return None


def log_error() -> None:
    try:
        LOG_FILE.write_text(traceback.format_exc(), encoding="utf-8")
    except Exception:
        pass


def load_settings() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(settings: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except Exception:
        pass


def frame_has_pixels(frame: Image.Image) -> bool:
    return frame.getchannel("A").getbbox() is not None


def clean_frame_for_tk(frame: Image.Image) -> Image.Image:
    rgba = frame.convert("RGBA")
    r, g, b, a = rgba.split()
    mask = a.point(lambda value: 255 if value > ALPHA_THRESHOLD else 0)
    transparent_bg = Image.new("RGBA", rgba.size, (255, 0, 255, 0))
    opaque = Image.merge("RGBA", (r, g, b, mask))
    return Image.composite(opaque, transparent_bg, mask)


def scan_sheet() -> dict:
    if not SPRITESHEET.exists():
        raise FileNotFoundError(f"Missing sprite sheet: {SPRITESHEET}")

    sheet = Image.open(SPRITESHEET).convert("RGBA")
    if sheet.width % COLS != 0 or sheet.height % len(STATES) != 0:
        raise ValueError(f"Unexpected sprite sheet size: {sheet.size}")

    cell_w = sheet.width // COLS
    cell_h = sheet.height // len(STATES)
    counts = {}
    for row, (state, _speed) in enumerate(STATES):
        count = 0
        for col in range(COLS):
            box = (col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h)
            if frame_has_pixels(sheet.crop(box)):
                count += 1
        counts[state] = count

    return {
        "spritesheet": str(SPRITESHEET),
        "size": [sheet.width, sheet.height],
        "cell": [cell_w, cell_h],
        "states": counts,
    }


class PetApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.scale = float(self.settings.get("scale", 1.0))
        self.scale = min(MAX_SCALE, max(MIN_SCALE, self.scale))
        self.sheet = Image.open(SPRITESHEET).convert("RGBA")
        self.source_frames: dict[str, list[Image.Image]] = {}
        self.frames: dict[str, list[ImageTk.PhotoImage]] = {}
        self.frame_cache: dict[tuple[int, str, str], dict[str, list[ImageTk.PhotoImage]]] = {}
        self.frame_cache_order: list[tuple[int, str, str]] = []
        self.frames_quality = "final"
        self.speeds = {state: speed for state, speed in STATES}
        self.state = "idle"
        self.frame_index = 0
        self.revert_job = None
        self.random_job = None
        self.random_enabled = bool(self.settings.get("random_actions", True))
        self.drag_origin = None
        self.root_origin = None
        self.dragging = False
        self.resize_origin = None
        self.resize_start_scale = self.scale
        self.resize_start_geometry = None
        self.resize_handle = None
        self.resize_handle_canvas = None
        self.resize_handle_visible = False
        self.pointer_job = None
        self.menu_window = None
        self.menu_canvas = None
        self.menu_hover_index = None
        self.menu_layout = []

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Codex Pet")
        self.root.configure(bg=TRANSPARENT_COLOR)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.wm_attributes("-toolwindow", True)
        except tk.TclError:
            pass
        try:
            self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        except tk.TclError:
            pass

        self.label = tk.Label(self.root, bg=TRANSPARENT_COLOR, bd=0, highlightthickness=0)
        self.label.pack()

        self.prepare_source_frames()
        self.load_frames()
        self.setup_menu()
        self.bind_events()
        self.place_window()
        self.setup_resize_handle()

    def prepare_source_frames(self) -> None:
        sheet = self.sheet
        self.cell_w = sheet.width // COLS
        self.cell_h = sheet.height // len(STATES)
        self.source_frames = {}
        for row, (state, _speed) in enumerate(STATES):
            state_frames = []
            for col in range(COLS):
                box = (
                    col * self.cell_w,
                    row * self.cell_h,
                    (col + 1) * self.cell_w,
                    (row + 1) * self.cell_h,
                )
                frame = sheet.crop(box)
                if frame_has_pixels(frame):
                    state_frames.append(frame)
            self.source_frames[state] = state_frames

    def remember_frame_cache(self, cache_key: tuple[int, str, str], frames: dict[str, list[ImageTk.PhotoImage]]) -> None:
        self.frame_cache[cache_key] = frames
        self.frame_cache_order.append(cache_key)
        while len(self.frame_cache_order) > FRAME_CACHE_LIMIT:
            old_key = self.frame_cache_order.pop(0)
            if old_key != cache_key:
                self.frame_cache.pop(old_key, None)

    def load_frames(self, live: bool = False) -> None:
        quality = "live" if live else "final"
        scale_key = int(round(self.scale * (100 if live else 1000)))
        live_state = self.state if live and self.source_frames.get(self.state) else "idle"
        cache_key = (scale_key, quality, live_state if live else "all")
        self.window_w = int(round(self.cell_w * self.scale))
        self.window_h = int(round(self.cell_h * self.scale))
        if cache_key in self.frame_cache:
            self.frames = self.frame_cache[cache_key]
            self.frames_quality = quality
            return

        scaled_frames = {}
        resample = Image.Resampling.BILINEAR if live else Image.Resampling.LANCZOS
        state_names = [live_state] if live else [state for state, _speed in STATES]
        for state in state_names:
            state_frames = []
            for source in self.source_frames.get(state, []):
                frame = source
                if self.scale != 1.0:
                    frame = frame.resize((self.window_w, self.window_h), resample)
                frame = clean_frame_for_tk(frame)
                state_frames.append(ImageTk.PhotoImage(frame))
            scaled_frames[state] = state_frames

        if live and live_state != "idle":
            scaled_frames["idle"] = scaled_frames.get(live_state, [])

        if not scaled_frames.get("idle") and "idle" in state_names:
            first_state = next((name for name, frames in scaled_frames.items() if frames), None)
            if not first_state:
                raise ValueError("Sprite sheet has no visible frames.")
            scaled_frames["idle"] = scaled_frames[first_state]

        self.remember_frame_cache(cache_key, scaled_frames)
        self.frames = scaled_frames
        self.frames_quality = quality

    def setup_menu(self) -> None:
        self.menu_items = [
            {"kind": "command", "label": "\u95f2\u7f6e", "action": "idle"},
            {"kind": "command", "label": "\u62db\u624b", "action": "wave"},
            {"kind": "command", "label": "\u5de5\u4f5c", "action": "work"},
            {"kind": "command", "label": "\u5ba1\u9605", "action": "review"},
            {"kind": "command", "label": "\u7b49\u5f85", "action": "waiting"},
            {"kind": "separator"},
            {"kind": "check", "label": "\u6bcf\u5206\u949f\u968f\u673a\u52a8\u4f5c", "action": "random"},
            {"kind": "separator"},
            {"kind": "command", "label": "\u6253\u5f00\u6587\u4ef6\u5939", "action": "open"},
            {"kind": "command", "label": "\u9000\u51fa", "action": "quit"},
        ]

    def bind_events(self) -> None:
        for widget in (self.root, self.label):
            widget.bind("<ButtonPress-1>", self.on_left_down)
            widget.bind("<B1-Motion>", self.on_drag)
            widget.bind("<ButtonRelease-1>", self.on_left_up)
            widget.bind("<Double-Button-1>", lambda _event: self.play_once("waving", 2600))
            widget.bind("<Button-3>", self.show_menu)

    def setup_resize_handle(self) -> None:
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=TRANSPARENT_COLOR)
        win.attributes("-topmost", True)
        try:
            win.wm_attributes("-toolwindow", True)
        except tk.TclError:
            pass
        try:
            win.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        except tk.TclError:
            pass
        try:
            win.attributes("-alpha", 0.92)
        except tk.TclError:
            pass

        canvas = tk.Canvas(
            win,
            width=RESIZE_HANDLE_SIZE,
            height=RESIZE_HANDLE_SIZE,
            bg=TRANSPARENT_COLOR,
            bd=0,
            highlightthickness=0,
            cursor="sizing",
        )
        canvas.pack()
        self.resize_handle = win
        self.resize_handle_canvas = canvas
        self.draw_resize_handle(active=False)

        for widget in (win, canvas):
            widget.bind("<ButtonPress-1>", self.on_resize_handle_down)
            widget.bind("<B1-Motion>", self.on_resize_handle_drag)
            widget.bind("<ButtonRelease-1>", self.on_resize_handle_up)
            widget.bind("<Button-3>", self.show_menu)

        self.monitor_pointer()

    def draw_resize_handle(self, active: bool) -> None:
        if not self.resize_handle_canvas:
            return
        canvas = self.resize_handle_canvas
        canvas.delete("all")
        fill = "#ffffff" if active else "#f8fafc"
        outline = "#4b5563" if active else "#7b8493"
        create_round_rect(
            canvas,
            2,
            2,
            RESIZE_HANDLE_SIZE - 2,
            RESIZE_HANDLE_SIZE - 2,
            RESIZE_HANDLE_RADIUS,
            fill=fill,
            outline=outline,
            width=1,
        )
        for offset in (9, 14, 19):
            canvas.create_line(
                RESIZE_HANDLE_SIZE - offset,
                RESIZE_HANDLE_SIZE - 5,
                RESIZE_HANDLE_SIZE - 5,
                RESIZE_HANDLE_SIZE - offset,
                fill="#596273",
                width=1,
            )

    def place_window(self) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = self.settings.get("x")
        y = self.settings.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            x = screen_w - self.window_w - 80
            y = screen_h - self.window_h - 120
        x = min(max(0, x), max(0, screen_w - self.window_w))
        y = min(max(0, y), max(0, screen_h - self.window_h))
        self.root.geometry(f"{self.window_w}x{self.window_h}+{x}+{y}")
        self.root.deiconify()

    def animate(self) -> None:
        frames = self.frames.get(self.state) or self.frames["idle"]
        self.label.configure(image=frames[self.frame_index % len(frames)])
        self.frame_index += 1
        self.root.after(self.speeds.get(self.state, 150), self.animate)

    def set_state(self, state: str) -> None:
        if state not in self.frames or not self.frames[state]:
            state = "idle"
        if self.revert_job is not None:
            self.root.after_cancel(self.revert_job)
            self.revert_job = None
        self.state = state
        self.frame_index = 0

    def play_once(self, state: str, duration_ms: int, return_state: str = "idle") -> None:
        self.set_state(state)
        self.revert_job = self.root.after(duration_ms, lambda: self.set_state(return_state))

    def apply_scale(self, scale: float, anchor: str = "center", save: bool = True, live: bool = False, force: bool = False) -> None:
        clamped = min(MAX_SCALE, max(MIN_SCALE, scale))
        if live:
            new_scale = round(round(clamped / LIVE_SCALE_QUANTUM) * LIVE_SCALE_QUANTUM, 2)
        else:
            new_scale = round(clamped, 3)
        if not force and abs(new_scale - self.scale) < 0.001 and self.frames_quality == ("live" if live else "final"):
            return

        old_w = self.window_w
        old_h = self.window_h
        old_x = self.root.winfo_x()
        old_y = self.root.winfo_y()

        self.scale = new_scale
        self.load_frames(live=live)
        if anchor == "top_left":
            x = old_x
            y = old_y
        else:
            x = int(round(old_x + (old_w - self.window_w) / 2))
            y = int(round(old_y + (old_h - self.window_h) / 2))

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = min(max(0, x), max(0, screen_w - self.window_w))
        y = min(max(0, y), max(0, screen_h - self.window_h))
        self.root.geometry(f"{self.window_w}x{self.window_h}+{x}+{y}")
        self.label.configure(image=(self.frames.get(self.state) or self.frames["idle"])[0])
        self.frame_index = 0
        self.settings["scale"] = self.scale
        self.position_resize_handle()
        if save:
            self.save_position()

    def on_left_down(self, event) -> None:
        self.hide_menu()
        self.drag_origin = (event.x_root, event.y_root)
        self.root_origin = (self.root.winfo_x(), self.root.winfo_y())
        self.dragging = False

    def on_drag(self, event) -> None:
        if not self.drag_origin or not self.root_origin:
            return
        dx = event.x_root - self.drag_origin[0]
        dy = event.y_root - self.drag_origin[1]
        self.dragging = abs(dx) > 2 or abs(dy) > 2
        self.root.geometry(f"+{self.root_origin[0] + dx}+{self.root_origin[1] + dy}")
        self.position_resize_handle()
        if abs(dx) > 3:
            self.set_state("running-right" if dx > 0 else "running-left")

    def on_left_up(self, _event) -> None:
        self.save_position()
        if self.dragging:
            self.set_state("idle")
        else:
            self.play_once("waving", 2200)
        self.drag_origin = None
        self.root_origin = None
        self.dragging = False

    def on_resize_handle_down(self, event) -> None:
        self.hide_menu()
        self.resize_origin = (event.x_root, event.y_root)
        self.resize_start_scale = self.scale
        self.resize_start_geometry = (
            self.root.winfo_x(),
            self.root.winfo_y(),
            self.window_w,
            self.window_h,
        )
        self.draw_resize_handle(active=True)

    def on_resize_handle_drag(self, event) -> None:
        if not self.resize_origin:
            return
        dx = event.x_root - self.resize_origin[0]
        dy = event.y_root - self.resize_origin[1]
        divisor = max(240, self.cell_w + self.cell_h)
        self.apply_scale(self.resize_start_scale + (dx + dy) / divisor, anchor="top_left", save=False, live=True)

    def on_resize_handle_up(self, _event) -> None:
        if self.resize_origin is not None:
            self.apply_scale(self.scale, anchor="top_left", save=False, live=False, force=True)
        self.resize_origin = None
        self.resize_start_geometry = None
        self.draw_resize_handle(active=False)
        self.save_position()

    def pointer_near_pet(self, x: int, y: int) -> bool:
        left = self.root.winfo_x() - RESIZE_NEAR_MARGIN
        top = self.root.winfo_y() - RESIZE_NEAR_MARGIN
        right = self.root.winfo_x() + self.window_w + RESIZE_NEAR_MARGIN
        bottom = self.root.winfo_y() + self.window_h + RESIZE_NEAR_MARGIN
        return left <= x <= right and top <= y <= bottom

    def pointer_near_resize_handle(self, x: int, y: int) -> bool:
        if not self.resize_handle_visible or not self.resize_handle:
            return False
        left = self.resize_handle.winfo_x() - 8
        top = self.resize_handle.winfo_y() - 8
        right = left + RESIZE_HANDLE_SIZE + 16
        bottom = top + RESIZE_HANDLE_SIZE + 16
        return left <= x <= right and top <= y <= bottom

    def monitor_pointer(self) -> None:
        try:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            if self.resize_origin or self.pointer_near_pet(x, y) or self.pointer_near_resize_handle(x, y):
                self.show_resize_handle()
            else:
                self.hide_resize_handle()
        finally:
            self.pointer_job = self.root.after(RESIZE_POLL_MS, self.monitor_pointer)

    def position_resize_handle(self) -> None:
        if not self.resize_handle or not self.resize_handle_visible:
            return
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = self.root.winfo_x() + self.window_w - RESIZE_HANDLE_SIZE + 7
        y = self.root.winfo_y() + self.window_h - RESIZE_HANDLE_SIZE + 7
        x = min(max(0, x), max(0, screen_w - RESIZE_HANDLE_SIZE))
        y = min(max(0, y), max(0, screen_h - RESIZE_HANDLE_SIZE))
        self.resize_handle.geometry(f"{RESIZE_HANDLE_SIZE}x{RESIZE_HANDLE_SIZE}+{x}+{y}")

    def show_resize_handle(self) -> None:
        if not self.resize_handle:
            return
        if not self.resize_handle_visible:
            self.resize_handle_visible = True
            self.position_resize_handle()
            self.resize_handle.deiconify()
            self.resize_handle.lift()
        else:
            self.position_resize_handle()

    def hide_resize_handle(self) -> None:
        if self.resize_origin or not self.resize_handle or not self.resize_handle_visible:
            return
        self.resize_handle.withdraw()
        self.resize_handle_visible = False

    def save_position(self) -> None:
        self.settings["x"] = int(self.root.winfo_x())
        self.settings["y"] = int(self.root.winfo_y())
        self.settings["scale"] = self.scale
        save_settings(self.settings)

    def set_random_actions(self, enabled: bool) -> None:
        self.random_enabled = enabled
        self.settings["random_actions"] = self.random_enabled
        save_settings(self.settings)
        if self.random_enabled:
            self.schedule_random_action(reset=True)
        elif self.random_job is not None:
            self.root.after_cancel(self.random_job)
            self.random_job = None

    def toggle_random_actions(self) -> None:
        self.set_random_actions(not self.random_enabled)
        self.draw_menu()

    def schedule_random_action(self, reset: bool = False) -> None:
        if self.random_job is not None and reset:
            self.root.after_cancel(self.random_job)
            self.random_job = None
        if self.random_enabled and self.random_job is None:
            self.random_job = self.root.after(RANDOM_INTERVAL_MS, self.run_random_action)

    def run_random_action(self) -> None:
        self.random_job = None
        if self.random_enabled:
            choices = [state for state in RANDOM_STATES if self.frames.get(state) and state != self.state]
            if choices and not self.dragging and self.resize_origin is None:
                return_state = self.state if self.frames.get(self.state) else "idle"
                self.play_once(random.choice(choices), RANDOM_DURATION_MS, return_state=return_state)
            self.schedule_random_action()

    def menu_height(self) -> int:
        height = MENU_PADDING * 2
        for item in self.menu_items:
            height += MENU_SEPARATOR_HEIGHT if item["kind"] == "separator" else MENU_ITEM_HEIGHT
        return height

    def show_menu(self, event) -> None:
        self.hide_menu()
        height = self.menu_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = min(max(0, event.x_root), max(0, screen_w - MENU_WIDTH))
        y = min(max(0, event.y_root), max(0, screen_h - height))

        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=TRANSPARENT_COLOR)
        win.attributes("-topmost", True)
        try:
            win.wm_attributes("-toolwindow", True)
        except tk.TclError:
            pass
        try:
            win.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        except tk.TclError:
            pass

        canvas = tk.Canvas(win, width=MENU_WIDTH, height=height, bg=TRANSPARENT_COLOR, bd=0, highlightthickness=0)
        canvas.pack()
        canvas.bind("<Motion>", self.on_menu_motion)
        canvas.bind("<Leave>", self.on_menu_leave)
        canvas.bind("<ButtonRelease-1>", self.on_menu_click)
        win.bind("<Escape>", lambda _event: self.hide_menu())
        win.bind("<Button-3>", lambda _event: self.hide_menu())

        self.menu_window = win
        self.menu_canvas = canvas
        self.menu_hover_index = None
        self.draw_menu()

        win.geometry(f"{MENU_WIDTH}x{height}+{x}+{y}")
        win.update_idletasks()
        win.deiconify()
        win.update_idletasks()
        win.lift()
        try:
            win.focus_force()
        except tk.TclError:
            pass

    def hide_menu(self) -> None:
        if self.menu_window is not None:
            try:
                self.menu_window.destroy()
            except tk.TclError:
                pass
        self.menu_window = None
        self.menu_canvas = None
        self.menu_hover_index = None
        self.menu_layout = []

    def draw_menu(self) -> None:
        if not self.menu_canvas:
            return
        canvas = self.menu_canvas
        height = self.menu_height()
        canvas.delete("all")
        create_round_rect(
            canvas,
            1,
            1,
            MENU_WIDTH - 1,
            height - 1,
            MENU_RADIUS,
            fill=MENU_BG,
            outline=MENU_BORDER,
            width=1,
        )
        canvas.create_line(22, 2, MENU_WIDTH - 22, 2, fill="#ffffff")

        self.menu_layout = []
        y = MENU_PADDING
        for index, item in enumerate(self.menu_items):
            if item["kind"] == "separator":
                canvas.create_line(MENU_PADDING + 12, y + 5, MENU_WIDTH - MENU_PADDING - 12, y + 5, fill="#e7e9ef")
                y += MENU_SEPARATOR_HEIGHT
                continue

            y1 = y
            y2 = y + MENU_ITEM_HEIGHT
            self.menu_layout.append((index, y1, y2))
            if self.menu_hover_index == index:
                create_round_rect(
                    canvas,
                    MENU_PADDING,
                    y1 + 2,
                    MENU_WIDTH - MENU_PADDING,
                    y2 - 2,
                    12,
                    fill=MENU_HOVER,
                    outline="",
                )

            if item["kind"] == "check":
                box_x = MENU_PADDING + 12
                box_y = y1 + 10
                fill = "#161a22" if self.random_enabled else "#ffffff"
                outline = "#161a22" if self.random_enabled else "#a8afbb"
                create_round_rect(canvas, box_x, box_y, box_x + 16, box_y + 16, 5, fill=fill, outline=outline)
                if self.random_enabled:
                    canvas.create_line(box_x + 4, box_y + 8, box_x + 7, box_y + 11, box_x + 12, box_y + 5, fill="#ffffff", width=2)
                text_x = MENU_PADDING + 38
            else:
                text_x = MENU_PADDING + 14

            canvas.create_text(
                text_x,
                y1 + MENU_ITEM_HEIGHT // 2,
                text=item["label"],
                anchor="w",
                fill=MENU_TEXT,
                font=("Segoe UI", 10),
            )
            if item.get("action") == self.state:
                canvas.create_oval(MENU_WIDTH - 24, y1 + 15, MENU_WIDTH - 18, y1 + 21, fill=MENU_MUTED, outline="")
            y += MENU_ITEM_HEIGHT

    def menu_index_at(self, y: int):
        for index, y1, y2 in self.menu_layout:
            if y1 <= y <= y2:
                return index
        return None

    def on_menu_motion(self, event) -> None:
        index = self.menu_index_at(event.y)
        if index != self.menu_hover_index:
            self.menu_hover_index = index
            self.draw_menu()

    def on_menu_leave(self, _event) -> None:
        if self.menu_hover_index is not None:
            self.menu_hover_index = None
            self.draw_menu()

    def on_menu_click(self, event) -> None:
        index = self.menu_index_at(event.y)
        if index is None:
            return
        item = self.menu_items[index]
        action = item.get("action")
        if action == "random":
            self.toggle_random_actions()
            return

        self.hide_menu()
        if action == "idle":
            self.set_state("idle")
        elif action == "wave":
            self.play_once("waving", 2600)
        elif action == "work":
            self.set_state("running")
        elif action == "review":
            self.set_state("review")
        elif action == "waiting":
            self.set_state("waiting")
        elif action == "open":
            self.open_folder()
        elif action == "quit":
            self.quit()

    def open_folder(self) -> None:
        os.startfile(BASE_DIR)

    def quit(self) -> None:
        if self.random_job is not None:
            self.root.after_cancel(self.random_job)
            self.random_job = None
        if self.pointer_job is not None:
            self.root.after_cancel(self.pointer_job)
            self.pointer_job = None
        self.hide_menu()
        if self.resize_handle is not None:
            try:
                self.resize_handle.destroy()
            except tk.TclError:
                pass
        self.save_position()
        self.root.destroy()

    def run(self) -> None:
        self.schedule_random_action()
        self.animate()
        self.root.mainloop()


def run_check() -> int:
    print(json.dumps(scan_sheet(), indent=2))
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return run_check()

    global _INSTANCE_MUTEX
    set_dpi_aware()
    _INSTANCE_MUTEX = claim_single_instance()
    PetApp().run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        log_error()
