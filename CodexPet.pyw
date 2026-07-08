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
SPRITESHEET = ASSET_DIR / "spritesheet.png"
OUTFITS = [
    ("default", "\u539f\u7248", "spritesheet.png"),
    ("coat_on", "\u7a7f\u5916\u5957", "spritesheet_coat_on.png"),
    ("coat_off", "\u8131\u5916\u5957", "spritesheet_coat_off.png"),
]
OUTFIT_LOOKUP = {outfit_id: (label, filename) for outfit_id, label, filename in OUTFITS}
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
RANDOM_STATES = ["waving", "failed", "waiting", "running", "review"]
RANDOM_INTERVAL_MS = 60_000
RANDOM_LOOPS = 2
DRAG_ACTION_THRESHOLD = 3
RIGHT_DRAG_THRESHOLD = 18
MIN_SCALE = 0.5
MAX_SCALE = 2.0
ALPHA_THRESHOLD = 18
LIVE_SCALE_QUANTUM = 0.01
FRAME_CACHE_LIMIT = 16
DISPLAY_WATCHDOG_MS = 2_000

RESIZE_HANDLE_SIZE = 30
RESIZE_HANDLE_RADIUS = 11
RESIZE_NEAR_MARGIN = 54
RESIZE_POLL_MS = 90

MENU_LIFT_RETRY_MS = (1, 40, 120, 300, 800, 1600)
MENU_OUTSIDE_POLL_MS = 45
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
MENU_ACTIVE_BG = "#eaf0ff"
MENU_ACTIVE_BORDER = "#8da8f7"
MENU_ACTIVE_TEXT = "#203a72"
MENU_CHECK_MARK = "#315eea"

WARDROBE_SIZE = 228
WARDROBE_RADIUS = 108
WARDROBE_BUTTON_RADIUS = 39
WARDROBE_CENTER_RADIUS = 35
WARDROBE_ICON_SIZE = 56
WARDROBE_DISC_FILL = "#f7f8fb"
WARDROBE_BUTTON_FILL = "#f8fafc"
WARDROBE_BUTTON_HOVER = "#ffffff"
WARDROBE_CENTER_FILL = "#eef2f7"


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


def set_ellipse_window(window: tk.Toplevel, width: int, height: int) -> None:
    try:
        hwnd = wintypes.HWND(window.winfo_id())
        region = ctypes.windll.gdi32.CreateEllipticRgn(0, 0, width + 1, height + 1)
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
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD
        handle = kernel32.CreateMutexW(None, True, "CodexPetStandalone_eoe_un")
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


def outfit_spritesheet(outfit_id: str) -> Path:
    _label, filename = OUTFIT_LOOKUP.get(outfit_id, OUTFIT_LOOKUP["default"])
    return ASSET_DIR / filename


def normalize_outfit_id(value) -> str:
    outfit_id = value if isinstance(value, str) else "default"
    if outfit_id not in OUTFIT_LOOKUP or not outfit_spritesheet(outfit_id).exists():
        return "default"
    return outfit_id


def frame_has_pixels(frame: Image.Image) -> bool:
    return frame.getchannel("A").getbbox() is not None


def clean_frame_for_tk(frame: Image.Image) -> Image.Image:
    rgba = frame.convert("RGBA")
    r, g, b, a = rgba.split()
    mask = a.point(lambda value: 255 if value > ALPHA_THRESHOLD else 0)
    transparent_bg = Image.new("RGBA", rgba.size, (255, 0, 255, 0))
    opaque = Image.merge("RGBA", (r, g, b, mask))
    return Image.composite(opaque, transparent_bg, mask)


def scan_sheet(path: Path = SPRITESHEET) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing sprite sheet: {path}")

    sheet = Image.open(path).convert("RGBA")
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
        "spritesheet": str(path),
        "size": [sheet.width, sheet.height],
        "cell": [cell_w, cell_h],
        "states": counts,
    }


def scan_all_sheets() -> dict:
    return {
        outfit_id: scan_sheet(outfit_spritesheet(outfit_id))
        for outfit_id, _label, _filename in OUTFITS
        if outfit_spritesheet(outfit_id).exists()
    }


class PetApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.scale = float(self.settings.get("scale", 1.0))
        self.scale = min(MAX_SCALE, max(MIN_SCALE, self.scale))
        self.outfit_id = normalize_outfit_id(self.settings.get("outfit", "default"))
        self.sheet = Image.open(outfit_spritesheet(self.outfit_id)).convert("RGBA")
        self.source_frames: dict[str, list[Image.Image]] = {}
        self.frames: dict[str, list[ImageTk.PhotoImage]] = {}
        self.frame_cache: dict[tuple[str, int, str, str], list[ImageTk.PhotoImage]] = {}
        self.frame_cache_order: list[tuple[str, int, str, str]] = []
        self.frames_quality = "final"
        self.frames_scale_key = 0
        self.frames_outfit_id = self.outfit_id
        self.speeds = {state: speed for state, speed in STATES}
        self.state = "idle"
        self.frame_index = 0
        self.current_frame_image = None
        self.revert_job = None
        self.random_job = None
        self.watchdog_job = None
        self.random_enabled = bool(self.settings.get("random_actions", True))
        self.drag_origin = None
        self.root_origin = None
        self.dragging = False
        self.right_origin = None
        self.right_dragging = False
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
        self.menu_outside_job = None
        self.menu_wait_for_button_release = False
        self.wardrobe_hover_id = None
        self.wardrobe_icons: dict[str, ImageTk.PhotoImage] = {}

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("EOE-柚恩桌宠2.0")
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
        self.prepare_wardrobe_icons()
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

    def remember_frame_cache(self, cache_key: tuple[str, int, str, str], frames: list[ImageTk.PhotoImage]) -> None:
        self.frame_cache[cache_key] = frames
        self.frame_cache_order.append(cache_key)
        while len(self.frame_cache_order) > FRAME_CACHE_LIMIT:
            old_key = self.frame_cache_order.pop(0)
            if old_key != cache_key:
                self.frame_cache.pop(old_key, None)

    def scale_key_for_quality(self, live: bool) -> int:
        return int(round(self.scale * (100 if live else 1000)))

    def scaled_state_frames(self, state: str, quality: str, scale_key: int, live: bool) -> list[ImageTk.PhotoImage]:
        cache_key = (self.outfit_id, scale_key, quality, state)
        if cache_key in self.frame_cache:
            return self.frame_cache[cache_key]

        state_frames = []
        resample = Image.Resampling.BILINEAR if live else Image.Resampling.LANCZOS
        for source in self.source_frames.get(state, []):
            frame = source
            if self.scale != 1.0:
                frame = frame.resize((self.window_w, self.window_h), resample)
            frame = clean_frame_for_tk(frame)
            state_frames.append(ImageTk.PhotoImage(frame))
        self.remember_frame_cache(cache_key, state_frames)
        return state_frames

    def load_frames(self, live: bool = False, states: list[str] | None = None) -> None:
        quality = "live" if live else "final"
        scale_key = self.scale_key_for_quality(live)
        live_state = self.state if live and self.source_frames.get(self.state) else "idle"
        self.window_w = int(round(self.cell_w * self.scale))
        self.window_h = int(round(self.cell_h * self.scale))

        if (
            self.frames_quality != quality
            or self.frames_scale_key != scale_key
            or self.frames_outfit_id != self.outfit_id
        ):
            self.frames = {}
            self.frames_quality = quality
            self.frames_scale_key = scale_key
            self.frames_outfit_id = self.outfit_id

        if states is None:
            state_names = [live_state if live else self.state]
            if not live and "idle" not in state_names:
                state_names.append("idle")
        else:
            state_names = states
        state_names = list(dict.fromkeys(state for state in state_names if self.source_frames.get(state)))
        if not state_names and self.source_frames.get("idle"):
            state_names = ["idle"]

        for state in state_names:
            self.frames[state] = self.scaled_state_frames(state, quality, scale_key, live)

        if not self.frames.get("idle") and not live and self.source_frames.get("idle"):
            self.frames["idle"] = self.scaled_state_frames("idle", quality, scale_key, live)

        if not any(self.frames.values()):
            raise ValueError("Sprite sheet has no visible frames.")

    def prepare_wardrobe_icons(self) -> None:
        self.wardrobe_icons = {}
        for outfit_id, _label, _filename in OUTFITS:
            path = outfit_spritesheet(outfit_id)
            if not path.exists():
                continue
            try:
                sheet = Image.open(path).convert("RGBA")
            except Exception:
                continue
            cell_w = sheet.width // COLS
            cell_h = sheet.height // len(STATES)
            frame = sheet.crop((0, 0, cell_w, cell_h))
            bbox = frame.getchannel("A").getbbox()
            icon = Image.new("RGBA", (WARDROBE_ICON_SIZE, WARDROBE_ICON_SIZE), (0, 0, 0, 0))
            if bbox is not None:
                sprite = frame.crop(bbox)
                sprite.thumbnail((WARDROBE_ICON_SIZE - 10, WARDROBE_ICON_SIZE - 6), Image.Resampling.LANCZOS)
                x = (WARDROBE_ICON_SIZE - sprite.width) // 2
                y = (WARDROBE_ICON_SIZE - sprite.height) // 2 + 2
                icon.alpha_composite(sprite, (x, y))
            self.wardrobe_icons[outfit_id] = ImageTk.PhotoImage(clean_frame_for_tk(icon))

    def setup_menu(self) -> None:
        self.menu_items = [
            {"kind": "command", "label": "\u95f2\u7f6e", "action": "idle"},
            {"kind": "command", "label": "\u62db\u624b", "action": "wave"},
            {"kind": "command", "label": "\u5de5\u4f5c", "action": "work"},
            {"kind": "command", "label": "\u5ba1\u9605", "action": "review"},
            {"kind": "command", "label": "\u7b49\u5f85", "action": "waiting"},
            {"kind": "command", "label": "\u5931\u8d25", "action": "failed"},
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
            widget.bind("<ButtonPress-3>", self.on_right_down)
            widget.bind("<B3-Motion>", self.on_right_drag)
            widget.bind("<ButtonRelease-3>", self.on_right_up)

    def setup_resize_handle(self) -> None:
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=MENU_BG)
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
            widget.bind("<ButtonPress-3>", self.on_right_down)
            widget.bind("<B3-Motion>", self.on_right_drag)
            widget.bind("<ButtonRelease-3>", self.on_right_up)

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

    def apply_window_invariants(self) -> None:
        try:
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
            if not self.menu_is_open():
                self.root.lift()
        except tk.TclError:
            pass
        if not self.label.winfo_ismapped():
            self.label.pack()
        self.position_resize_handle()
        self.lift_floating_windows()

    def clear_menu_reference(self) -> None:
        if self.menu_outside_job is not None:
            try:
                self.root.after_cancel(self.menu_outside_job)
            except tk.TclError:
                pass
            self.menu_outside_job = None
        self.menu_wait_for_button_release = False
        self.menu_window = None
        self.menu_canvas = None
        self.menu_hover_index = None
        self.menu_layout = []
        self.wardrobe_hover_id = None

    def menu_is_open(self) -> bool:
        if self.menu_window is None:
            return False
        try:
            if self.menu_window.winfo_exists():
                return True
        except tk.TclError:
            pass
        self.clear_menu_reference()
        return False

    def lift_floating_windows(self) -> None:
        try:
            if self.resize_handle_visible and self.resize_handle is not None:
                self.resize_handle.attributes("-topmost", True)
                self.resize_handle.lift()
        except tk.TclError:
            pass
        self.lift_menu_window()

    def lift_menu_window(self, focus: bool = False) -> None:
        if self.menu_window is None:
            return
        try:
            if not self.menu_window.winfo_exists():
                self.clear_menu_reference()
                return
            self.menu_window.attributes("-topmost", True)
            self.menu_window.lift()
            if focus:
                self.menu_window.focus_force()
        except tk.TclError:
            self.clear_menu_reference()

    def schedule_menu_lift_retries(self) -> None:
        for delay_ms in MENU_LIFT_RETRY_MS:
            self.root.after(delay_ms, self.lift_menu_window)

    def mouse_buttons_down(self) -> bool:
        try:
            user32 = ctypes.windll.user32
            user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
            user32.GetAsyncKeyState.restype = ctypes.c_short
            return any(user32.GetAsyncKeyState(button) & 0x8001 for button in (1, 2, 4))
        except Exception:
            return False

    def pointer_in_menu(self, x: int, y: int) -> bool:
        if not self.menu_is_open():
            return False
        try:
            left = self.menu_window.winfo_rootx()
            top = self.menu_window.winfo_rooty()
            right = left + self.menu_window.winfo_width()
            bottom = top + self.menu_window.winfo_height()
            return left <= x <= right and top <= y <= bottom
        except tk.TclError:
            self.clear_menu_reference()
            return False

    def schedule_menu_outside_monitor(self) -> None:
        if self.menu_outside_job is None and self.menu_is_open():
            self.menu_outside_job = self.root.after(MENU_OUTSIDE_POLL_MS, self.monitor_menu_outside_click)

    def monitor_menu_outside_click(self) -> None:
        self.menu_outside_job = None
        if not self.menu_is_open():
            return
        buttons_down = self.mouse_buttons_down()
        if self.menu_wait_for_button_release:
            if not buttons_down:
                self.menu_wait_for_button_release = False
        elif buttons_down:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            if not self.pointer_in_menu(x, y):
                self.hide_menu()
                return
        self.schedule_menu_outside_monitor()

    def current_frames(self) -> list[ImageTk.PhotoImage]:
        frames = self.frames.get(self.state)
        if frames:
            return frames

        if self.source_frames.get(self.state):
            live = self.frames_quality == "live" and self.resize_origin is not None
            self.load_frames(live=live, states=[self.state])
            frames = self.frames.get(self.state)
            if frames:
                return frames

        frames = self.frames.get("idle")
        if frames:
            return frames

        self.state = "idle"
        self.load_frames(live=False, states=["idle"])
        return self.frames.get("idle", [])

    def show_current_frame(self, reset: bool = False) -> None:
        frames = self.current_frames()
        if not frames:
            return
        if reset:
            self.frame_index = 0
        image = frames[self.frame_index % len(frames)]
        self.current_frame_image = image
        self.label.configure(image=image)

    def recover_display(self) -> None:
        if self.resize_origin is None and self.frames_quality != "final":
            self.load_frames(live=False, states=[self.state])
        if not (self.frames.get(self.state) or self.frames.get("idle")):
            self.state = "idle"
            self.load_frames(live=False, states=["idle"])
        self.show_current_frame(reset=True)
        self.apply_window_invariants()

    def display_image_is_alive(self) -> bool:
        try:
            image_name = str(self.label.cget("image"))
            if not image_name:
                return False
            return image_name in self.root.tk.call("image", "names")
        except tk.TclError:
            return False

    def watchdog_display(self) -> None:
        try:
            needs_recovery = (
                not self.display_image_is_alive()
                or self.root.state() == "withdrawn"
                or (not self.source_frames.get(self.state) and not self.frames.get("idle"))
            )
            if self.resize_origin is None and self.frames_quality != "final":
                needs_recovery = True
            if needs_recovery:
                self.recover_display()
            else:
                self.apply_window_invariants()
        except Exception:
            log_error()
        finally:
            self.watchdog_job = self.root.after(DISPLAY_WATCHDOG_MS, self.watchdog_display)

    def animate(self) -> None:
        try:
            self.show_current_frame()
            self.frame_index += 1
        except Exception:
            log_error()
            self.recover_display()
        finally:
            self.root.after(self.speeds.get(self.state, 150), self.animate)

    def set_state(self, state: str) -> None:
        if not self.source_frames.get(state):
            state = "idle"
        if self.revert_job is not None:
            self.root.after_cancel(self.revert_job)
            self.revert_job = None
        self.state = state
        self.frame_index = 0
        live = self.resize_origin is not None
        self.load_frames(live=live, states=[state])

    def set_outfit(self, outfit_id: str) -> None:
        outfit_id = normalize_outfit_id(outfit_id)
        if outfit_id == self.outfit_id:
            return
        if self.revert_job is not None:
            self.root.after_cancel(self.revert_job)
            self.revert_job = None
        self.outfit_id = outfit_id
        self.settings["outfit"] = self.outfit_id
        self.sheet = Image.open(outfit_spritesheet(self.outfit_id)).convert("RGBA")
        self.frame_cache.clear()
        self.frame_cache_order.clear()
        self.frames = {}
        self.prepare_source_frames()
        if not self.source_frames.get(self.state):
            self.state = "idle"
        self.load_frames(live=False, states=[self.state])
        self.show_current_frame(reset=True)
        self.save_position()

    def play_once(self, state: str, duration_ms: int, return_state: str = "idle") -> None:
        self.set_state(state)
        self.revert_job = self.root.after(duration_ms, lambda: self.set_state(return_state))

    def apply_scale(self, scale: float, anchor: str = "center", save: bool = True, live: bool = False, force: bool = False) -> None:
        clamped = min(MAX_SCALE, max(MIN_SCALE, scale))
        if live:
            new_scale = round(round(clamped / LIVE_SCALE_QUANTUM) * LIVE_SCALE_QUANTUM, 2)
        else:
            new_scale = round(clamped, 3)
        target_quality = "live" if live else "final"
        if (
            not force
            and abs(new_scale - self.scale) < 0.001
            and self.frames_quality == target_quality
            and (self.frames.get(self.state) or self.frames.get("idle"))
        ):
            return

        old_w = self.window_w
        old_h = self.window_h
        old_x = self.root.winfo_x()
        old_y = self.root.winfo_y()

        self.scale = new_scale
        self.load_frames(live=live, states=[self.state])
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
        self.show_current_frame(reset=True)
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
        target_state = None
        if abs(dy) > DRAG_ACTION_THRESHOLD and abs(dy) >= abs(dx):
            target_state = "jumping"
        elif abs(dx) > DRAG_ACTION_THRESHOLD:
            target_state = "running-right" if dx > 0 else "running-left"
        if target_state and target_state != self.state:
            self.set_state(target_state)

    def on_left_up(self, _event) -> None:
        self.save_position()
        if self.dragging:
            self.set_state("idle")
        else:
            self.play_once("waving", 2200)
        self.drag_origin = None
        self.root_origin = None
        self.dragging = False

    def on_right_down(self, event) -> None:
        self.right_origin = (event.x_root, event.y_root)
        self.right_dragging = False

    def on_right_drag(self, event) -> None:
        if not self.right_origin:
            return
        dx = event.x_root - self.right_origin[0]
        dy = event.y_root - self.right_origin[1]
        if not self.right_dragging and (dx * dx + dy * dy) ** 0.5 >= RIGHT_DRAG_THRESHOLD:
            self.right_dragging = True
            self.show_wardrobe_wheel_at(self.right_origin[0], self.right_origin[1])
        elif self.right_dragging:
            self.lift_menu_window()

    def on_right_up(self, event) -> None:
        try:
            if self.right_dragging:
                self.select_wardrobe_at_root(event.x_root, event.y_root)
            else:
                self.show_action_menu_at(event.x_root, event.y_root)
        finally:
            self.right_origin = None
            self.right_dragging = False

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
        self.lift_menu_window()

    def hide_resize_handle(self) -> None:
        if self.resize_origin or not self.resize_handle or not self.resize_handle_visible:
            return
        self.resize_handle.withdraw()
        self.resize_handle_visible = False

    def save_position(self) -> None:
        self.settings["x"] = int(self.root.winfo_x())
        self.settings["y"] = int(self.root.winfo_y())
        self.settings["scale"] = self.scale
        self.settings["outfit"] = self.outfit_id
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
            if self.resize_origin is None and self.frames_quality != "final":
                self.load_frames(live=False)
            choices = [state for state in RANDOM_STATES if self.source_frames.get(state)]
            if choices and self.state == "idle" and not self.dragging and self.resize_origin is None:
                state = random.choice(choices)
                self.play_once(state, self.state_loop_duration_ms(state, RANDOM_LOOPS), return_state="idle")
            self.schedule_random_action()

    def state_loop_duration_ms(self, state: str, loops: int) -> int:
        frame_count = max(1, len(self.source_frames.get(state, [])))
        return frame_count * self.speeds.get(state, 150) * loops

    def menu_height(self) -> int:
        height = MENU_PADDING * 2
        for item in self.menu_items:
            height += MENU_SEPARATOR_HEIGHT if item["kind"] == "separator" else MENU_ITEM_HEIGHT
        return height

    def show_menu(self, event) -> None:
        self.show_action_menu_at(event.x_root, event.y_root)

    def show_action_menu_at(self, x_root: int, y_root: int) -> None:
        self.hide_menu()
        height = self.menu_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = min(max(0, x_root), max(0, screen_w - MENU_WIDTH))
        y = min(max(0, y_root), max(0, screen_h - height))

        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=TRANSPARENT_COLOR)
        win.attributes("-topmost", True)
        try:
            win.transient(self.root)
        except tk.TclError:
            pass
        try:
            win.wm_attributes("-toolwindow", True)
        except tk.TclError:
            pass

        canvas = tk.Canvas(win, width=MENU_WIDTH, height=height, bg=MENU_BG, bd=0, highlightthickness=0)
        canvas.pack()
        canvas.bind("<Motion>", self.on_menu_motion)
        canvas.bind("<Leave>", self.on_menu_leave)
        canvas.bind("<ButtonRelease-1>", self.on_menu_click)
        win.bind("<Escape>", lambda _event: self.hide_menu())
        win.bind("<Button-3>", lambda _event: self.hide_menu())

        self.menu_window = win
        self.menu_canvas = canvas
        self.menu_hover_index = None
        self.menu_wait_for_button_release = True
        self.draw_menu()

        win.geometry(f"{MENU_WIDTH}x{height}+{x}+{y}")
        win.update_idletasks()
        win.deiconify()
        win.update_idletasks()
        self.apply_popup_effects(win, MENU_WIDTH, height, MENU_RADIUS)
        self.lift_menu_window(focus=True)
        self.schedule_menu_lift_retries()
        self.schedule_menu_outside_monitor()

    def apply_popup_effects(self, win: tk.Toplevel, width: int, height: int, radius: int, ellipse: bool = False) -> None:
        try:
            win.attributes("-alpha", 0.96)
        except tk.TclError:
            pass
        enable_acrylic(win, 210)
        if ellipse:
            set_ellipse_window(win, width, height)
        else:
            set_rounded_window(win, width, height, radius * 2)

    def wardrobe_options(self) -> list[tuple[str, str, int, int]]:
        center = WARDROBE_SIZE // 2
        return [
            ("default", "\u539f\u7248", center, 42),
            ("coat_on", "\u5916\u5957", 62, 158),
            ("coat_off", "\u80cc\u5fc3", 166, 158),
        ]

    def show_wardrobe_wheel(self, event) -> None:
        self.show_wardrobe_wheel_at(event.x_root, event.y_root)

    def show_wardrobe_wheel_at(self, x_root: int, y_root: int) -> None:
        self.hide_menu()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = min(max(0, x_root - WARDROBE_SIZE // 2), max(0, screen_w - WARDROBE_SIZE))
        y = min(max(0, y_root - WARDROBE_SIZE // 2), max(0, screen_h - WARDROBE_SIZE))

        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=MENU_BG)
        win.attributes("-topmost", True)
        try:
            win.transient(self.root)
        except tk.TclError:
            pass
        try:
            win.wm_attributes("-toolwindow", True)
        except tk.TclError:
            pass

        canvas = tk.Canvas(win, width=WARDROBE_SIZE, height=WARDROBE_SIZE, bg=MENU_BG, bd=0, highlightthickness=0)
        canvas.pack()
        canvas.bind("<Motion>", self.on_wardrobe_motion)
        canvas.bind("<Leave>", self.on_wardrobe_leave)
        canvas.bind("<ButtonRelease-1>", self.on_wardrobe_click)
        canvas.bind("<ButtonRelease-3>", self.on_wardrobe_click)
        win.bind("<Escape>", lambda _event: self.hide_menu())
        win.bind("<Button-3>", lambda _event: self.hide_menu())

        self.menu_window = win
        self.menu_canvas = canvas
        self.menu_wait_for_button_release = True
        self.wardrobe_hover_id = None
        self.draw_wardrobe_wheel()

        win.geometry(f"{WARDROBE_SIZE}x{WARDROBE_SIZE}+{x}+{y}")
        win.update_idletasks()
        win.deiconify()
        win.update_idletasks()
        self.apply_popup_effects(win, WARDROBE_SIZE, WARDROBE_SIZE, WARDROBE_SIZE // 2, ellipse=True)
        self.lift_menu_window(focus=True)
        self.schedule_menu_lift_retries()
        self.schedule_menu_outside_monitor()

    def draw_wardrobe_wheel(self) -> None:
        if not self.menu_canvas:
            return
        canvas = self.menu_canvas
        canvas.delete("all")
        center = WARDROBE_SIZE // 2
        canvas.create_oval(
            center - WARDROBE_RADIUS,
            center - WARDROBE_RADIUS,
            center + WARDROBE_RADIUS,
            center + WARDROBE_RADIUS,
            fill=WARDROBE_DISC_FILL,
            outline="",
        )
        self.menu_layout = [("menu", "menu", center, center, WARDROBE_CENTER_RADIUS)]
        center_hover = self.wardrobe_hover_id == "menu"
        canvas.create_oval(
            center - WARDROBE_CENTER_RADIUS,
            center - WARDROBE_CENTER_RADIUS,
            center + WARDROBE_CENTER_RADIUS,
            center + WARDROBE_CENTER_RADIUS,
            fill=WARDROBE_BUTTON_HOVER if center_hover else WARDROBE_CENTER_FILL,
            outline="",
        )
        canvas.create_text(center, center, text="\u83dc\u5355", fill=MENU_TEXT, font=("Segoe UI", 10))

        for outfit_id, label, cx, cy in self.wardrobe_options():
            self.menu_layout.append(("outfit", outfit_id, cx, cy, WARDROBE_BUTTON_RADIUS))
            active = outfit_id == self.outfit_id
            hover = self.wardrobe_hover_id == outfit_id
            fill = MENU_ACTIVE_BG if active else (WARDROBE_BUTTON_HOVER if hover else WARDROBE_BUTTON_FILL)
            text_fill = MENU_ACTIVE_TEXT if active else MENU_TEXT
            canvas.create_oval(
                cx - WARDROBE_BUTTON_RADIUS,
                cy - WARDROBE_BUTTON_RADIUS,
                cx + WARDROBE_BUTTON_RADIUS,
                cy + WARDROBE_BUTTON_RADIUS,
                fill=fill,
                outline="",
            )
            icon = self.wardrobe_icons.get(outfit_id)
            if icon is not None:
                canvas.create_image(cx, cy - 5, image=icon)
            canvas.create_text(cx, cy + 25, text=label, fill=text_fill, font=("Segoe UI", 8))

    def wardrobe_item_at(self, x: int, y: int):
        for kind, value, cx, cy, radius in self.menu_layout:
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                return kind, value
        return None

    def on_wardrobe_motion(self, event) -> None:
        hit = self.wardrobe_item_at(event.x, event.y)
        hover_id = hit[1] if hit else None
        if hover_id != self.wardrobe_hover_id:
            self.wardrobe_hover_id = hover_id
            self.draw_wardrobe_wheel()

    def on_wardrobe_leave(self, _event) -> None:
        if self.wardrobe_hover_id is not None:
            self.wardrobe_hover_id = None
            self.draw_wardrobe_wheel()

    def on_wardrobe_click(self, event) -> None:
        hit = self.wardrobe_item_at(event.x, event.y)
        self.select_wardrobe_hit(hit, event.x_root, event.y_root)

    def select_wardrobe_at_root(self, x_root: int, y_root: int) -> None:
        if not self.menu_is_open() or self.menu_window is None:
            return
        try:
            x = x_root - self.menu_window.winfo_rootx()
            y = y_root - self.menu_window.winfo_rooty()
        except tk.TclError:
            return
        self.select_wardrobe_hit(self.wardrobe_item_at(x, y), x_root, y_root)

    def select_wardrobe_hit(self, hit, x_root: int, y_root: int) -> None:
        if not hit:
            return
        kind, value = hit
        if kind == "menu":
            self.hide_menu()
            self.show_action_menu_at(x_root, y_root)
        elif kind == "outfit":
            self.hide_menu()
            self.set_outfit(value)

    def hide_menu(self) -> None:
        if self.menu_window is not None:
            try:
                self.menu_window.destroy()
            except tk.TclError:
                pass
        self.clear_menu_reference()

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
                fill = MENU_ACTIVE_BG if self.random_enabled else "#ffffff"
                outline = MENU_ACTIVE_BORDER if self.random_enabled else "#a8afbb"
                create_round_rect(canvas, box_x, box_y, box_x + 16, box_y + 16, 5, fill=fill, outline=outline)
                if self.random_enabled:
                    canvas.create_line(box_x + 4, box_y + 8, box_x + 7, box_y + 11, box_x + 12, box_y + 5, fill=MENU_CHECK_MARK, width=2)
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
            action = item.get("action")
            active = action == self.state or action == f"outfit:{self.outfit_id}"
            if active:
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
            self.set_state("waving")
        elif action == "work":
            self.set_state("running")
        elif action == "review":
            self.set_state("review")
        elif action == "waiting":
            self.set_state("waiting")
        elif action == "failed":
            self.set_state("failed")
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
        if self.watchdog_job is not None:
            self.root.after_cancel(self.watchdog_job)
            self.watchdog_job = None
        if self.menu_outside_job is not None:
            self.root.after_cancel(self.menu_outside_job)
            self.menu_outside_job = None
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
        self.watchdog_display()
        self.animate()
        self.root.mainloop()


def run_check() -> int:
    print(json.dumps(scan_all_sheets(), indent=2))
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
