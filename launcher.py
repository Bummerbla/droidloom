#!/usr/bin/env python3
"""Native desktop app launcher for a phone running SCRCPY's virtual display."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
import shlex
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import math
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
NAMES_FILE = APP_DIR / "app_names.json"
SETTINGS_FILE = APP_DIR / "launcher_settings.json"
DEFAULT_DISPLAY_MODE = "1920x1080/240"
DISPLAY_PRESETS = ("1280x720/180", "1600x900/200", "1920x1080/240", "2560x1440/280")
APP_LAYOUT_TABLET = "Tablet (fill display)"
APP_LAYOUT_FREEFORM = "Freeform windows"
SCRCPY_WINDOW_TITLE = "DroidLoom SCRCPY"
BG = "#101311"
PANEL = "#191e1b"
CARD = "#1c221e"
EDGE = "#303a33"
FG = "#eff4ef"
MUTED = "#98a39b"
GREEN = "#b9ef6c"
ACCENTS = ("#b9ef6c", "#6fc5df", "#d99472", "#aa94ea", "#e9c264", "#e88192", "#70c99e")
UI_FONT = "Segoe UI" if os.name == "nt" else "DejaVu Sans"
MONO_FONT = "Consolas" if os.name == "nt" else "DejaVu Sans Mono"

LABELS = {
    "com.openai.chatgpt": "ChatGPT",
    "com.anthropic.claude": "Claude",
    "com.google.android.apps.bard": "Gemini",
    "org.telegram.messenger": "Telegram",
    "com.whatsapp": "WhatsApp",
    "com.google.android.apps.docs": "Google Drive",
    "com.google.android.apps.photos": "Google Photos",
    "com.google.android.apps.youtube.music": "YouTube Music",
    "com.google.android.youtube": "YouTube",
    "com.android.chrome": "Chrome",
    "com.android.vending": "Google Play Store",
    "com.google.android.gm": "Gmail",
    "com.google.android.apps.maps": "Google Maps",
    "com.google.android.calendar": "Google Calendar",
    "com.google.android.contacts": "Google Contacts",
    "com.google.android.apps.nbu.files": "Files by Google",
    "com.google.android.apps.messaging": "Google Messages",
    "com.google.android.dialer": "Phone",
    "com.android.settings": "Settings",
    "com.sec.android.app.clockpackage": "Clock",
    "com.sec.android.app.popupcalculator": "Calculator",
    "com.sec.android.app.launcher": "One UI Home",
    "com.sec.android.app.camera": "Camera",
    "com.sec.android.gallery3d": "Samsung Gallery",
    "com.sec.android.app.myfiles": "My Files",
    "com.samsung.android.app.notes": "Samsung Notes",
    "com.samsung.android.app.watchmanager": "Galaxy Wearable",
    "com.sec.android.app.voicenote": "Voice Recorder",
    "com.sec.android.app.sbrowser": "Samsung Internet",
    "com.instagram.android": "Instagram",
    "com.facebook.katana": "Facebook",
    "com.spotify.music": "Spotify",
    "com.netflix.mediaclient": "Netflix",
    "com.discord": "Discord",
    "org.mozilla.firefox": "Firefox",
    "com.microsoft.office.officehubrow": "Microsoft 365",
    "com.microsoft.teams": "Microsoft Teams",
    "com.amazon.mShop.android.shopping": "Amazon Shopping",
    "com.snapchat.android": "Snapchat",
    "com.reddit.frontpage": "Reddit",
}


def run(command, timeout=12):
    options = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, **options)


def find_tool(name, configured=None, search_dirs=(), env_var=None):
    """Find SCRCPY or ADB from a saved path, environment, adjacent folder, or PATH."""
    names = (f"{name}.exe", name) if os.name == "nt" else (name,)
    candidates = []
    for raw_path in (configured, os.environ.get(env_var) if env_var else None):
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if path.is_dir():
            candidates.extend(path / executable for executable in names)
        else:
            candidates.append(path)
    for directory in search_dirs:
        if directory:
            candidates.extend(Path(directory) / executable for executable in names)
    for executable in names:
        located = shutil.which(executable)
        if located:
            candidates.append(Path(located))
    for path in candidates:
        try:
            if path.is_file() and (os.name == "nt" or os.access(path, os.X_OK)):
                return path.resolve()
        except OSError:
            pass
    return None


def parse_display_mode(value):
    match = re.fullmatch(r"\s*(\d{3,5})\s*[xX]\s*(\d{3,5})(?:\s*/\s*(\d{2,4}))?\s*", value or "")
    if not match:
        raise ValueError("Enter a size like 1920x1080/155 (width × height / DPI).")
    width, height = int(match.group(1)), int(match.group(2))
    dpi = int(match.group(3) or 155)
    if not (320 <= width <= 8192 and 320 <= height <= 8192):
        raise ValueError("Width and height must each be between 320 and 8192 pixels.")
    if not (72 <= dpi <= 1000):
        raise ValueError("DPI must be between 72 and 1000.")
    return width, height, dpi, f"{width}x{height}/{dpi}"


def app_name(package, custom_names=None, system_name=None):
    if custom_names and custom_names.get(package):
        return custom_names[package]
    if package in LABELS:
        return LABELS[package]
    if system_name and system_name.strip():
        return system_name.strip()
    # Turn package IDs into a readable fallback while preserving the app's distinctive name.
    pieces = [part for part in package.split(".") if part.lower() not in {"com", "org", "net", "android", "app", "mobile", "client"}]
    tail = (pieces[-1] if pieces else package).replace("_", " ").replace("-", " ")
    tail = re.sub(r"([a-z])([A-Z])", r"\1 \2", tail)
    return " ".join(word.upper() if word.lower() in {"ai", "tv", "sms", "vpn", "pdf", "qr"} else word.title() for word in tail.split())


def app_category(name, package):
    value = f"{name} {package}".lower()
    sections = {
        "AI & Chat": ("chatgpt", "openai", "claude", "anthropic", "gemini", "bard", "copilot", "perplexity"),
        "Messaging": ("whatsapp", "telegram", "messenger", "signal", "discord", "wechat", "line", "viber", "messages"),
        "Work": ("docs", "drive", "sheets", "slides", "office", "word", "excel", "notion", "keep", "calendar", "zoom", "meet"),
        "Media": ("youtube", "netflix", "spotify", "music", "photos", "camera", "gallery", "video", "primevideo"),
        "Social": ("instagram", "facebook", "snapchat", "tiktok", "reddit", "pinterest", "twitter"),
        "Tools": ("settings", "clock", "calculator", "files", "browser", "chrome", "firefox", "phone", "contacts"),
    }
    for category, words in sections.items():
        if any(word in value for word in words):
            return category
    return "Other apps"


def read_scrcpy_app_labels(serial, packages, scrcpy_path):
    """Read Android's user-facing app labels from SCRCPY when its list format is available."""
    if not scrcpy_path or not scrcpy_path.is_file():
        return {}
    try:
        result = run([str(scrcpy_path), "--serial", serial, "--list-apps"], timeout=90)
    except (OSError, subprocess.SubprocessError):
        return {}
    text = result.stdout + "\n" + result.stderr
    labels = {}
    for package in packages:
        for raw_line in text.splitlines():
            if package not in raw_line:
                continue
            before, after = raw_line.split(package, 1)
            before = re.sub(r"^.*?\[server\]\s*INFO:\s*", "", before.strip())
            before = before.strip(" \t-:[]()")
            after = after.strip(" \t-:[]()")
            candidate = before if before and before.lower() not in {"info", "list of apps"} else after
            candidate = re.sub(r"^(?:INFO:\s*|\[server\]\s*)", "", candidate).strip()
            if candidate and candidate != package and not candidate.startswith("Processing Android apps"):
                labels[package] = candidate[:64]
                break
    return labels


def resolve_app(adb, serial, package, system_labels=None):
    result = run([
        str(adb), "-s", serial, "shell", "cmd", "package", "resolve-activity", "--brief",
        "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", package,
    ], timeout=15)
    if result.returncode:
        return None
    components = [line.strip() for line in result.stdout.splitlines() if "/" in line and not line.strip().startswith("priority=")]
    if not components:
        return None
    system_name = (system_labels or {}).get(package)
    name = app_name(package, system_name=system_name)
    return {"name": name, "system_name": system_name, "package": package, "component": components[-1], "category": app_category(name, package)}


def parse_display_tasks(activity_dump, window_dump, display_id, app_by_package):
    """Extract app tasks belonging to the SCRCPY display from Android's dumpsys output."""
    display_id = str(display_id)
    current_display = None
    current_stack = None
    current_task = None
    tasks = {}
    resumed_package = None

    for line in activity_dump.splitlines():
        display_header = re.search(r"Display\s+#(\d+)", line)
        if display_header:
            current_display = display_header.group(1)
            current_stack = None
            current_task = None

        explicit_display = re.search(r"(?:mDisplayId=|displayId=)(\d+)", line)
        if explicit_display:
            current_display = explicit_display.group(1)

        stack_match = re.search(r"(?:Stack|RootTask)\s+#(\d+)|StackId=(\d+)", line)
        if stack_match:
            current_stack = stack_match.group(1) or stack_match.group(2)

        task_match = re.search(r"Task(?:Record)?\{[^\n}]*?#(\d+)", line)
        if task_match:
            current_task = task_match.group(1)
            task_stack = re.search(r"StackId=(\d+)", line)
            if task_stack:
                current_stack = task_stack.group(1)

        component = re.search(r"\bu\d+\s+([A-Za-z0-9._]+)/([A-Za-z0-9_.$]+)", line)
        if not component:
            continue
        package, activity = component.group(1), component.group(2)
        activity_task = re.search(r"\bt=?([0-9]+)\b", line)
        task_id = activity_task.group(1) if activity_task else current_task
        if current_display != display_id or not task_id:
            continue
        task = tasks.setdefault(task_id, {
            "task_id": task_id,
            "stack_id": current_stack,
            "package": package,
            "activity": activity,
            "resumed": False,
        })
        if current_stack and not task["stack_id"]:
            task["stack_id"] = current_stack
        if any(word in line for word in ("mResumedActivity", "ResumedActivity:", "topResumedActivity")):
            task["package"] = package
            task["activity"] = activity
            task["resumed"] = True
            resumed_package = package

    focused = re.search(r"mCurrentFocus=.*?\s([A-Za-z0-9._]+)/([A-Za-z0-9_.$]+)", window_dump)
    focused_package = focused.group(1) if focused else resumed_package
    if focused_package not in {task["package"] for task in tasks.values()}:
        focused_package = resumed_package
    result = []
    for task in tasks.values():
        app = app_by_package.get(task["package"])
        if not app:
            continue
        result.append({
            **task,
            "name": app["name"],
            "system_name": app.get("system_name"),
            "component": f"{task['package']}/{task['activity']}",
            "focused": task["package"] == focused_package,
        })
    result.sort(key=lambda item: (not item["focused"], item["name"].casefold(), int(item["task_id"])))
    return result


class AndroidLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("DroidLoom")
        self.root.geometry("1260x800")
        self.root.minsize(960, 620)
        self.root.configure(bg=BG)
        self.devices = []
        self.apps = []
        self.custom_names = self._load_custom_names()
        self.settings = self._load_settings()
        bundled_dirs = (APP_DIR, APP_DIR / "tools" / "scrcpy")
        self.scrcpy = find_tool("scrcpy", self.settings.get("scrcpy_path"), bundled_dirs, "POCKET_DESKTOP_SCRCPY")
        adb_dirs = (*((self.scrcpy.parent,) if self.scrcpy else ()), *bundled_dirs)
        self.adb = find_tool("adb", self.settings.get("adb_path"), adb_dirs, "POCKET_DESKTOP_ADB")
        self.display_mode_var = tk.StringVar(value=self.settings.get("display_mode", DEFAULT_DISPLAY_MODE))
        self.app_layout_var = tk.StringVar(value=self.settings.get("app_layout", APP_LAYOUT_TABLET))
        self.audio_var = tk.BooleanVar(value=self.settings.get("audio_to_pc", True))
        self.screen_off_var = tk.BooleanVar(value=self.settings.get("screen_off", False))
        self.display_size = parse_display_mode(self.display_mode_var.get())[:2]
        self.display_id = None
        self.scrcpy_process = None
        self.scan_busy = False
        self.open_apps_busy = False
        self.open_tasks = {}
        self.open_refresh_after = None
        self.active_category = "All apps"
        self.query = tk.StringVar()
        self.device_var = tk.StringVar()
        self._configure_styles()
        self._build_ui()
        self.refresh_devices(silent=True)
        self.root.after(500, self.poll_process)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG, arrowcolor=GREEN, bordercolor=EDGE)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)])
        style.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED)

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=34, pady=24)
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x")
        logo = tk.Label(header, text="▣", bg=GREEN, fg="#182016", font=(UI_FONT, 17, "bold"), width=2, height=1)
        logo.pack(side="left", padx=(0, 11))
        tk.Label(header, text="droidloom", bg=BG, fg=FG, font=(UI_FONT, 16, "bold")).pack(side="left")
        self.status_dot = tk.Label(header, text="●", bg=BG, fg="#68736b", font=(UI_FONT, 10))
        self.status_dot.pack(side="right", padx=(9, 0))
        self.status_label = tk.Label(header, text="Checking phone…", bg=BG, fg=MUTED, font=(UI_FONT, 10))
        self.status_label.pack(side="right")
        tk.Frame(outer, bg=EDGE, height=1).pack(fill="x", pady=(17, 26))

        hero = tk.Frame(outer, bg=BG)
        hero.pack(fill="x", pady=(0, 25))
        tk.Label(hero, text="ANDROID WORKSPACE / 01", bg=BG, fg=GREEN, font=(MONO_FONT, 9)).pack(anchor="w")
        tk.Label(hero, text="Your phone, on desktop.", bg=BG, fg=FG, font=(UI_FONT, 29, "bold")).pack(anchor="w", pady=(7, 2))
        tk.Label(hero, text="Start a display, find an app, and open it on your PC.", bg=BG, fg=MUTED, font=(UI_FONT, 11)).pack(anchor="w")

        controls = tk.Frame(outer, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        controls.pack(fill="x", pady=(0, 19))
        control_row = tk.Frame(controls, bg=PANEL)
        control_row.pack(fill="x", padx=13, pady=12)
        self.start_button = self.make_button(control_row, "▶  Start desktop display", self.start_display, primary=True)
        self.start_button.pack(side="left", padx=(0, 8))
        self.stop_button = self.make_button(control_row, "■  Close display", self.stop_display)
        self.stop_button.pack(side="left", padx=(0, 8))
        self.scan_button = self.make_button(control_row, "↻  Scan phone apps", self.scan_apps)
        self.scan_button.pack(side="left", padx=(0, 15))
        tk.Label(control_row, text="Phone", bg=PANEL, fg=MUTED, font=(UI_FONT, 9)).pack(side="left", padx=(0, 7))
        self.device_menu = ttk.Combobox(control_row, textvariable=self.device_var, state="readonly", width=22)
        self.device_menu.pack(side="left")
        self.device_menu.bind("<<ComboboxSelected>>", self.device_selected)
        self.make_button(control_row, "↻", lambda: self.refresh_devices(silent=False)).pack(side="left", padx=(7, 0))
        self.make_button(control_row, "Tools…", self.locate_tools).pack(side="left", padx=(7, 0))
        settings_row = tk.Frame(controls, bg=PANEL)
        settings_row.pack(fill="x", padx=13, pady=(0, 9))
        tk.Label(settings_row, text="Resolution", bg=PANEL, fg=MUTED, font=(UI_FONT, 9)).pack(side="left", padx=(0, 8))
        self.resolution_menu = ttk.Combobox(settings_row, textvariable=self.display_mode_var, values=DISPLAY_PRESETS, width=19)
        self.resolution_menu.pack(side="left", padx=(0, 14))
        self.resolution_menu.bind("<<ComboboxSelected>>", self.update_display_summary)
        self.resolution_menu.bind("<FocusOut>", self.update_display_summary)
        tk.Label(settings_row, text="App view", bg=PANEL, fg=MUTED, font=(UI_FONT, 9)).pack(side="left", padx=(0, 8))
        self.app_layout_menu = ttk.Combobox(settings_row, textvariable=self.app_layout_var, values=(APP_LAYOUT_TABLET, APP_LAYOUT_FREEFORM), state="readonly", width=23)
        self.app_layout_menu.pack(side="left")
        options_row = tk.Frame(controls, bg=PANEL)
        options_row.pack(fill="x", padx=13, pady=(0, 9))
        self.audio_toggle = tk.Checkbutton(options_row, text="Play phone audio on this PC", variable=self.audio_var, bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=GREEN, selectcolor=CARD, font=(UI_FONT, 9), cursor="hand2")
        self.audio_toggle.pack(side="left")
        self.screen_off_toggle = tk.Checkbutton(options_row, text="Turn phone screen off on start", variable=self.screen_off_var, bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=GREEN, selectcolor=CARD, font=(UI_FONT, 9), cursor="hand2")
        self.screen_off_toggle.pack(side="left", padx=(15, 0))
        tk.Label(options_row, text="Custom size: 1920x1080/240", bg=PANEL, fg="#78827b", font=(UI_FONT, 8)).pack(side="left", padx=(12, 0))
        self.display_label = tk.Label(controls, text=self._display_settings_label(), bg=PANEL, fg=MUTED, font=(MONO_FONT, 9))
        self.display_label.pack(anchor="w", padx=15, pady=(0, 11))
        tk.Label(controls, text="While SCRCPY is focused: MOD+O turns the phone screen off · MOD+Shift+O turns it on", bg=PANEL, fg="#78827b", font=(UI_FONT, 8)).pack(anchor="w", padx=15, pady=(0, 10))

        tools = tk.Frame(outer, bg=BG)
        tools.pack(fill="x", pady=(0, 12))
        self.search_entry = tk.Entry(tools, textvariable=self.query, bg=PANEL, fg=FG, insertbackground=GREEN, relief="flat", font=(UI_FONT, 10), highlightthickness=1, highlightbackground=EDGE, highlightcolor=GREEN)
        self.search_entry.pack(side="right", ipadx=10, ipady=8)
        tk.Label(tools, text="SEARCH", bg=BG, fg=MUTED, font=(MONO_FONT, 8, "bold")).pack(side="right", padx=(0, 8))
        self.search_entry.insert(0, "")
        self.search_entry.bind("<KeyRelease>", lambda _event: self.render_apps())
        self.category_bar = tk.Frame(tools, bg=BG)
        self.category_bar.pack(side="left", fill="x")

        list_frame = tk.Frame(outer, bg=BG)
        list_frame.pack(fill="both", expand=True)
        app_area = tk.Frame(list_frame, bg=BG)
        app_area.pack(side="left", fill="both", expand=True, padx=(0, 16))
        self.canvas = tk.Canvas(app_area, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(app_area, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.app_frame = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.app_frame, anchor="nw")
        self.app_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        self._build_open_apps_panel(list_frame)
        self.show_empty("Connect and unlock your phone, then start a desktop display.\nYour apps will be found automatically.")

        footer = tk.Frame(outer, bg=BG)
        footer.pack(fill="x", pady=(16, 0))
        tk.Frame(footer, bg=EDGE, height=1).pack(fill="x", pady=(0, 12))
        tk.Label(footer, text="LOCAL ANDROID DESKTOP  /  ADB + SCRCPY", bg=BG, fg="#78827b", font=(MONO_FONT, 8)).pack(side="left")
        tk.Label(footer, text="The phone's display is not changed.", bg=BG, fg="#78827b", font=(UI_FONT, 8)).pack(side="right")

    def _build_open_apps_panel(self, parent):
        style = ttk.Style()
        style.configure("Open.Treeview", background=CARD, fieldbackground=CARD, foreground=FG, rowheight=31, borderwidth=0, font=(UI_FONT, 9))
        style.configure("Open.Treeview.Heading", background=PANEL, foreground=MUTED, relief="flat", font=(UI_FONT, 8, "bold"))
        style.map("Open.Treeview", background=[("selected", "#344333")], foreground=[("selected", FG)])
        panel = tk.Frame(parent, bg=PANEL, width=302, highlightbackground=EDGE, highlightthickness=1)
        panel.pack(side="right", fill="y")
        panel.pack_propagate(False)
        top = tk.Frame(panel, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(13, 5))
        tk.Label(top, text="OPEN ON DISPLAY", bg=PANEL, fg=GREEN, font=(MONO_FONT, 9, "bold")).pack(side="left")
        self.open_count = tk.Label(top, text="0", bg=PANEL, fg=MUTED, font=(MONO_FONT, 9))
        self.open_count.pack(side="left", padx=(7, 0))
        self.open_refresh_button = tk.Button(top, text="↻", command=self.refresh_open_apps, bg=PANEL, fg=FG, activebackground="#303a33", activeforeground=GREEN, relief="flat", bd=0, cursor="hand2", font=(UI_FONT, 12, "bold"))
        self.open_refresh_button.pack(side="right")
        tk.Label(panel, text="Select a window to manage it", bg=PANEL, fg=MUTED, font=(UI_FONT, 8)).pack(anchor="w", padx=14, pady=(0, 9))
        self.open_tree = ttk.Treeview(panel, columns=("app", "focus"), show="headings", style="Open.Treeview", selectmode="browse")
        self.open_tree.heading("app", text="APP", anchor="w")
        self.open_tree.heading("focus", text="STATE", anchor="center")
        self.open_tree.column("app", width=170, minwidth=100, stretch=True, anchor="w")
        self.open_tree.column("focus", width=78, minwidth=70, stretch=False, anchor="center")
        self.open_tree.tag_configure("focused", foreground=GREEN)
        self.open_tree.tag_configure("open", foreground=FG)
        self.open_tree.pack(fill="both", expand=True, padx=9, pady=(0, 10))
        self.open_tree.bind("<<TreeviewSelect>>", self.open_app_selected)
        self.open_buttons = []
        for label, action in (("Focus selected", self.focus_selected), ("Maximize", self.maximize_selected), ("Unfocus", self.unfocus_selected)):
            button = self.make_button(panel, label, action)
            button.configure(state="disabled")
            button.pack(fill="x", padx=12, pady=(0, 7))
            self.open_buttons.append(button)
        tk.Label(panel, text="Focus and window actions apply\nto this SCRCPY display.", bg=PANEL, fg="#78827b", justify="left", font=(UI_FONT, 8)).pack(anchor="w", padx=14, pady=(1, 13))

    def make_button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, bg=GREEN if primary else "#252d27", fg="#182016" if primary else FG, activebackground="#c9f78a" if primary else "#354038", activeforeground="#182016" if primary else FG, relief="flat", bd=0, padx=12, pady=9, cursor="hand2", font=(UI_FONT, 9, "bold"), disabledforeground="#718071")

    def _load_custom_names(self):
        try:
            value = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _load_settings(self):
        try:
            value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                return {}
            _, _, _, mode = parse_display_mode(value.get("display_mode", DEFAULT_DISPLAY_MODE))
            app_layout = value.get("app_layout", APP_LAYOUT_TABLET)
            if app_layout not in (APP_LAYOUT_TABLET, APP_LAYOUT_FREEFORM):
                app_layout = APP_LAYOUT_TABLET
            return {
                "display_mode": mode,
                "app_layout": app_layout,
                "audio_to_pc": bool(value.get("audio_to_pc", True)),
                "screen_off": bool(value.get("screen_off", False)),
                "scrcpy_path": value.get("scrcpy_path", ""),
                "adb_path": value.get("adb_path", ""),
            }
        except (OSError, json.JSONDecodeError, ValueError):
            return {"display_mode": DEFAULT_DISPLAY_MODE, "app_layout": APP_LAYOUT_TABLET, "audio_to_pc": True, "screen_off": False, "scrcpy_path": "", "adb_path": ""}

    def _save_settings(self, display_mode, app_layout, audio_to_pc, screen_off):
        self.settings.update({
            "display_mode": display_mode,
            "app_layout": app_layout,
            "audio_to_pc": audio_to_pc,
            "screen_off": screen_off,
            "scrcpy_path": str(self.scrcpy) if self.scrcpy else "",
            "adb_path": str(self.adb) if self.adb else "",
        })
        SETTINGS_FILE.write_text(json.dumps(self.settings, indent=2) + "\n", encoding="utf-8")

    def locate_tools(self):
        filetypes = [("SCRCPY executable", "*.exe"), ("All files", "*.*")] if os.name == "nt" else [("SCRCPY executable", "scrcpy*"), ("All files", "*")]
        selected = filedialog.askopenfilename(title="Choose the SCRCPY program", filetypes=filetypes, parent=self.root)
        if not selected:
            return
        self.scrcpy = Path(selected)
        sibling_dirs = (self.scrcpy.parent,)
        self.adb = find_tool("adb", search_dirs=sibling_dirs + (APP_DIR,), env_var="POCKET_DESKTOP_ADB")
        if not self.adb:
            adb_types = [("ADB executable", "adb.exe"), ("All files", "*.*")] if os.name == "nt" else [("ADB executable", "adb*"), ("All files", "*")]
            adb_selected = filedialog.askopenfilename(title="Choose the ADB program", filetypes=adb_types, parent=self.root)
            if not adb_selected:
                self.scrcpy = None
                return
            self.adb = Path(adb_selected)
        self.settings["scrcpy_path"] = str(self.scrcpy)
        self.settings["adb_path"] = str(self.adb)
        try:
            SETTINGS_FILE.write_text(json.dumps(self.settings, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Tool paths could not be saved", str(exc), parent=self.root)
            return
        self.refresh_devices(silent=False)

    def _display_settings_label(self):
        try:
            width, height, dpi, _mode = parse_display_mode(self.display_mode_var.get())
            return f"SCRCPY  ·  {width} × {height}  ·  {dpi} DPI"
        except ValueError:
            return "Enter resolution as WIDTHxHEIGHT/DPI"

    def _windowing_mode(self):
        return "1" if self.app_layout_var.get() == APP_LAYOUT_TABLET else "5"

    def update_display_summary(self, _event=None):
        if hasattr(self, "display_label"):
            self.display_label.configure(text=self._display_settings_label())

    def _save_custom_names(self):
        NAMES_FILE.write_text(json.dumps(self.custom_names, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def rename_app(self, app):
        package = app["package"]
        current = app["name"]
        new_name = simpledialog.askstring("Rename app", f"Choose a name for {current}:\n{package}", initialvalue=current, parent=self.root)
        if new_name is None:
            return
        new_name = new_name.strip()
        if new_name:
            self.custom_names[package] = new_name[:48]
        else:
            self.custom_names.pop(package, None)
        try:
            self._save_custom_names()
        except OSError as exc:
            messagebox.showerror("Name could not be saved", str(exc), parent=self.root)
            return
        for item in self.apps:
            item["name"] = app_name(item["package"], self.custom_names, item.get("system_name"))
            item["category"] = app_category(item["name"], item["package"])
        for item in self.open_tasks.values():
            item["name"] = app_name(item["package"], self.custom_names, item.get("system_name"))
        self.render_categories()
        self.render_apps()
        self._render_open_tasks(list(self.open_tasks.values()))

    def make_app_icon(self, parent, package, name=None):
        size = 42
        palette = {
            "com.openai.chatgpt": "#76d7b0",
            "com.anthropic.claude": "#d89b7b",
            "com.google.android.apps.bard": "#89a8ff",
            "org.telegram.messenger": "#65bce3",
            "com.whatsapp": "#45c981",
            "com.google.android.apps.docs": "#54a5ff",
            "com.google.android.apps.photos": "#73a7ff",
            "com.google.android.youtube": "#f35a62",
            "com.google.android.apps.youtube.music": "#f35a62",
            "com.android.chrome": "#f0c452",
            "com.instagram.android": "#d883cf",
            "com.spotify.music": "#54d47d",
        }
        color = palette.get(package, ACCENTS[sum(map(ord, package)) % len(ACCENTS)])
        icon = tk.Canvas(parent, width=size, height=size, bg=CARD, highlightthickness=0, cursor="hand2")
        # Use native canvas shapes so the launcher needs no icon packs or network access.
        icon.create_oval(3, 3, 39, 39, fill="#29352d", outline="")
        cx = cy = 21
        if package == "com.openai.chatgpt":
            points = []
            for n in range(12):
                radius = 14 if n % 2 == 0 else 6
                angle = n * math.pi / 6 - math.pi / 2
                points.extend((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
            icon.create_polygon(*points, fill=color, outline="")
            icon.create_oval(18, 18, 24, 24, fill="#29352d", outline="")
        elif package == "com.anthropic.claude":
            icon.create_text(cx, cy, text="✳", fill=color, font=(UI_FONT, 28, "bold"))
        elif package == "com.google.android.apps.bard":
            icon.create_polygon(cx, 5, cx+4, 17, 37, cy, cx+4, 25, cx, 37, cx-4, 25, 5, cy, cx-4, 17, fill=color, outline="")
        elif package == "org.telegram.messenger":
            icon.create_polygon(7, 20, 34, 9, 28, 34, 21, 26, 17, 31, 17, 23, fill=color, outline="")
            icon.create_line(17, 23, 29, 14, fill="#29352d", width=1)
        elif package == "com.whatsapp":
            icon.create_oval(7, 7, 35, 35, fill=color, outline="")
            icon.create_polygon(9, 31, 7, 38, 16, 34, fill=color, outline="")
            icon.create_text(21, 21, text="☎", fill="#ffffff", font=(UI_FONT, 14, "bold"))
        elif package == "com.google.android.apps.docs":
            icon.create_polygon(14, 7, 24, 7, 35, 26, 30, 34, fill="#fbbc04", outline="")
            icon.create_polygon(14, 7, 24, 7, 12, 29, 7, 21, fill="#4285f4", outline="")
            icon.create_polygon(7, 21, 12, 29, 30, 29, 35, 21, 30, 34, 12, 34, fill="#34a853", outline="")
        elif package == "com.google.android.apps.photos":
            icon.create_oval(17, 6, 25, 23, fill="#4d8df5", outline="")
            icon.create_oval(19, 19, 36, 27, fill="#34a853", outline="")
            icon.create_oval(17, 19, 25, 36, fill="#fbbc04", outline="")
            icon.create_oval(6, 19, 23, 27, fill="#ea4335", outline="")
        elif package in ("com.google.android.youtube", "com.google.android.apps.youtube.music"):
            icon.create_rectangle(6, 12, 36, 30, fill=color, outline="")
            icon.create_polygon(18, 16, 18, 26, 27, 21, fill="#ffffff", outline="")
        elif package == "com.android.chrome":
            icon.create_arc(5, 5, 37, 37, start=30, extent=115, fill="#ea4335", outline="")
            icon.create_arc(5, 5, 37, 37, start=145, extent=115, fill="#34a853", outline="")
            icon.create_arc(5, 5, 37, 37, start=260, extent=130, fill="#fbbc04", outline="")
            icon.create_oval(15, 15, 27, 27, fill="#4285f4", outline="#d8e4ff", width=1)
        elif package == "com.instagram.android":
            icon.create_rectangle(10, 10, 32, 32, outline=color, width=3)
            icon.create_oval(15, 15, 27, 27, outline=color, width=2)
            icon.create_oval(27, 12, 30, 15, fill=color, outline="")
        elif package == "com.spotify.music":
            icon.create_oval(5, 5, 37, 37, fill=color, outline="")
            icon.create_arc(11, 12, 32, 25, start=200, extent=140, style="arc", outline="#18351f", width=2)
            icon.create_arc(13, 18, 30, 29, start=200, extent=140, style="arc", outline="#18351f", width=2)
            icon.create_arc(15, 24, 28, 32, start=200, extent=140, style="arc", outline="#18351f", width=2)
        else:
            icon.create_text(cx, cy, text=(name or app_name(package, self.custom_names))[:1].upper(), fill=color, font=(UI_FONT, 18, "bold"))
        return icon

    def selected_serial(self):
        value = self.device_var.get()
        return value.split(" · ", 1)[0] if value else None

    def refresh_devices(self, silent=False):
        if not self.adb or not self.adb.is_file():
            self.set_status("ADB not found", False)
            if not silent:
                messagebox.showerror("ADB not found", "Install SCRCPY or Android Platform Tools, or use Tools… to select adb.", parent=self.root)
            return
        try:
            result = run([str(self.adb), "devices"], timeout=8)
            self.devices = [tuple(line.split()[:2]) for line in result.stdout.splitlines()[1:] if len(line.split()) >= 2]
        except (OSError, subprocess.SubprocessError) as exc:
            self.set_status("Could not check phone", False)
            if not silent:
                messagebox.showerror("Phone check failed", str(exc))
            return
        values = [f"{serial} · {state}" for serial, state in self.devices]
        self.device_menu["values"] = values
        active = next((value for value in values if value.startswith((self.selected_serial() or "") + " · device")), None)
        if not active:
            active = next((value for value in values if value.endswith("· device")), values[0] if values else "")
        self.device_var.set(active)
        ready = any(state == "device" for _, state in self.devices)
        unauthorized = any(state == "unauthorized" for _, state in self.devices)
        if ready:
            self.set_status("Phone connected", True)
        elif unauthorized:
            self.set_status("Approve USB debugging on phone", False)
        else:
            self.set_status("Phone not connected", False)

    def device_selected(self, _event=None):
        self.apps = []
        self.render_categories()
        self.show_empty("Phone changed. Scan again to load its apps.")

    def set_status(self, text, connected):
        self.status_label.configure(text=text)
        self.status_dot.configure(fg=GREEN if connected else "#68736b")

    def show_empty(self, text):
        for child in self.app_frame.winfo_children():
            child.destroy()
        tk.Label(self.app_frame, text=text, bg=PANEL, fg=MUTED, padx=20, pady=35, font=(UI_FONT, 10), justify="center").grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        self.app_frame.grid_columnconfigure(0, weight=1)

    def render_categories(self):
        for child in self.category_bar.winfo_children():
            child.destroy()
        categories = ["All apps", *sorted({app["category"] for app in self.apps})]
        if self.active_category not in categories:
            self.active_category = "All apps"
        for category in categories:
            button = tk.Button(self.category_bar, text=category, command=lambda c=category: self.select_category(c), bg="#252d27" if category == self.active_category else BG, fg=GREEN if category == self.active_category else MUTED, activebackground="#354038", activeforeground=GREEN, relief="flat", bd=0, padx=10, pady=7, cursor="hand2", font=(UI_FONT, 9, "bold"))
            button.pack(side="left", padx=(0, 5))

    def select_category(self, category):
        self.active_category = category
        self.render_categories()
        self.render_apps()

    def render_apps(self):
        for child in self.app_frame.winfo_children():
            child.destroy()
        query = self.query.get().strip().casefold()
        shown = [app for app in self.apps if (self.active_category == "All apps" or app["category"] == self.active_category) and query in (app["name"] + " " + app["package"]).casefold()]
        columns = max(2, min(5, self.canvas.winfo_width() // 185))
        for index, app in enumerate(shown):
            row, col = divmod(index, columns)
            accent = ACCENTS[index % len(ACCENTS)]
            card = tk.Frame(self.app_frame, bg=CARD, highlightbackground=EDGE, highlightthickness=1, padx=13, pady=12, cursor="hand2")
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            top = tk.Frame(card, bg=CARD)
            top.pack(fill="x")
            icon = self.make_app_icon(top, app["package"], app["name"])
            icon.pack(side="left", anchor="w")
            rename_button = tk.Button(top, text="✎", command=lambda item=app: self.rename_app(item), bg=CARD, fg=MUTED, activebackground="#29352d", activeforeground=GREEN, relief="flat", bd=0, cursor="hand2", font=(UI_FONT, 11))
            rename_button.pack(side="right", anchor="ne")
            name_label = tk.Label(card, text=app["name"], bg=CARD, fg=FG, font=(UI_FONT, 10, "bold"), anchor="w")
            name_label.pack(fill="x", pady=(11, 2))
            package_label = tk.Label(card, text=app["package"], bg=CARD, fg=MUTED, font=(UI_FONT, 7), anchor="w")
            package_label.pack(fill="x")
            for widget in (card, top, icon, name_label, package_label):
                widget.bind("<Button-1>", lambda _event, item=app: self.launch_app(item))
                widget.bind("<Enter>", lambda _event, box=card: box.configure(highlightbackground="#849a68"))
                widget.bind("<Leave>", lambda _event, box=card: box.configure(highlightbackground=EDGE))
        for col in range(columns):
            self.app_frame.grid_columnconfigure(col, weight=1, uniform="app")
        if not shown:
            self.show_empty("No apps match this filter." if self.apps else "Choose Scan phone apps to discover launchable apps.")

    def scan_apps(self):
        if self.scan_busy:
            return
        if not self.adb:
            messagebox.showinfo("Set up SCRCPY and ADB", "Install SCRCPY or Android Platform Tools, then use Tools… to locate them.", parent=self.root)
            return
        serial = self.selected_serial()
        if not serial or not any(s == serial and state == "device" for s, state in self.devices):
            messagebox.showinfo("Connect your phone", "Connect and unlock the phone, then allow USB debugging before scanning apps.")
            self.refresh_devices(silent=True)
            return
        self.scan_busy = True
        self.scan_button.configure(state="disabled", text="Scanning…")
        self.show_empty("Reading installed apps and finding launch activities…")
        threading.Thread(target=self._scan_worker, args=(serial,), daemon=True).start()

    def _scan_worker(self, serial):
        try:
            result = run([str(self.adb), "-s", serial, "shell", "pm", "list", "packages"], timeout=25)
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout).strip() or "Android did not return the installed apps.")
            packages = sorted({line.split(":", 1)[-1].strip() for line in result.stdout.splitlines() if line.strip().startswith("package:")})
            system_labels = read_scrcpy_app_labels(serial, packages, self.scrcpy)
            found = []
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [pool.submit(resolve_app, self.adb, serial, package, system_labels) for package in packages]
                for future in as_completed(futures):
                    app = future.result()
                    if app:
                        found.append(app)
            found.sort(key=lambda app: (app["category"], app["name"].casefold(), app["package"]))
            self.root.after(0, self._scan_done, found, None)
        except Exception as exc:
            self.root.after(0, self._scan_done, [], str(exc))

    def _scan_done(self, apps, error):
        self.scan_busy = False
        self.scan_button.configure(state="normal", text="↻  Scan phone apps")
        if error:
            self.show_empty("App scan failed. Check the phone connection and try again.")
            messagebox.showerror("App scan failed", error)
            return
        self.apps = apps
        for item in self.apps:
            item["name"] = app_name(item["package"], self.custom_names, item.get("system_name"))
            item["category"] = app_category(item["name"], item["package"])
        self.active_category = "All apps"
        self.render_categories()
        self.render_apps()
        self.set_status(f"Found {len(apps)} launchable apps", True)
        self.refresh_open_apps()

    def refresh_open_apps(self):
        process = self.scrcpy_process
        if self.open_apps_busy or not process or process.poll() is not None or not self.display_id:
            if not process or process.poll() is not None:
                self._render_open_tasks([])
            return
        serial = self.selected_serial()
        if not serial:
            return
        self.open_apps_busy = True
        threading.Thread(target=self._open_apps_worker, args=(serial, str(self.display_id), list(self.apps)), daemon=True).start()

    def _open_apps_worker(self, serial, display_id, apps):
        try:
            activity_dump = run([str(self.adb), "-s", serial, "shell", "dumpsys", "activity", "activities"], timeout=20).stdout
            window_dump = run([str(self.adb), "-s", serial, "shell", "dumpsys", "window", "windows"], timeout=15).stdout
            app_by_package = {app["package"]: app for app in apps}
            tasks = parse_display_tasks(activity_dump, window_dump, display_id, app_by_package)
            self.root.after(0, self._open_apps_done, tasks, None)
        except Exception as exc:
            self.root.after(0, self._open_apps_done, [], str(exc))

    def _open_apps_done(self, tasks, error):
        self.open_apps_busy = False
        if error:
            self.status_label.configure(text="Could not read open app windows")
        else:
            self.open_tasks = {task["task_id"]: task for task in tasks}
            self._render_open_tasks(tasks)
        if self.scrcpy_process and self.scrcpy_process.poll() is None:
            self.open_refresh_after = self.root.after(1800, self.refresh_open_apps)

    def _render_open_tasks(self, tasks):
        selected = self.open_tree.selection()
        selected_id = selected[0] if selected else None
        for item in self.open_tree.get_children():
            self.open_tree.delete(item)
        for task in tasks:
            state = "FOCUSED" if task["focused"] else "OPEN"
            tag = "focused" if task["focused"] else "open"
            self.open_tree.insert("", "end", iid=task["task_id"], values=(task["name"], state), tags=(tag,))
        self.open_count.configure(text=str(len(tasks)))
        if selected_id in self.open_tasks:
            self.open_tree.selection_set(selected_id)
        self._set_window_buttons(bool(self.open_tree.selection()))

    def open_app_selected(self, _event=None):
        self._set_window_buttons(bool(self.open_tree.selection()))

    def _set_window_buttons(self, enabled):
        for button in self.open_buttons:
            button.configure(state="normal" if enabled else "disabled")

    def selected_task(self):
        selection = self.open_tree.selection()
        return self.open_tasks.get(selection[0]) if selection else None

    @staticmethod
    def _command_failed(result):
        output = (result.stdout + "\n" + result.stderr).strip()
        return bool(result.returncode or re.search(r"(?:^|\n)(?:Error:|Exception|Unknown command|Permission Denial)", output, re.I)), output

    def _run_adb_shell(self, serial, *args):
        return run([str(self.adb), "-s", serial, "shell", *map(str, args)], timeout=15)

    @staticmethod
    def _raise_scrcpy_window():
        try:
            if os.name == "nt":
                import ctypes
                user32 = ctypes.windll.user32
                window = user32.FindWindowW(None, SCRCPY_WINDOW_TITLE)
                if window:
                    user32.ShowWindow(window, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(window)
                return
            wmctrl = shutil.which("wmctrl")
            if wmctrl:
                subprocess.run([wmctrl, "-a", SCRCPY_WINDOW_TITLE], capture_output=True, timeout=3)
        except (OSError, subprocess.SubprocessError):
            pass

    def focus_selected(self):
        task = self.selected_task()
        if task:
            self._start_window_action("focus", task)

    def maximize_selected(self):
        task = self.selected_task()
        if task:
            self._start_window_action("maximize", task)

    def unfocus_selected(self):
        task = self.selected_task()
        if task:
            self._start_window_action("unfocus", task)

    def _start_window_action(self, action, task):
        serial = self.selected_serial()
        if not serial or not self.display_id:
            return
        progress = {"focus": "Focusing", "maximize": "Maximizing", "unfocus": "Unfocusing"}[action]
        self.set_status(f"{progress} {task['name']}…", True)
        threading.Thread(target=self._window_action_worker, args=(serial, str(self.display_id), action, dict(task), list(self.open_tasks.values()), self._windowing_mode()), daemon=True).start()

    def _window_action_worker(self, serial, display_id, action, task, all_tasks, windowing_mode):
        try:
            task_id = task["task_id"]
            if action == "focus":
                result = self._run_adb_shell(serial, "am", "task", "focus", task_id)
                failed, detail = self._command_failed(result)
                if failed:
                    result = self._run_adb_shell(serial, "am", "start", "--display", display_id, "--windowingMode", windowing_mode, "--activity-reorder-to-front", "-n", shlex.quote(task["component"]))
                    failed, detail = self._command_failed(result)
            elif action == "maximize":
                width, height = self.display_size
                result = self._run_adb_shell(serial, "am", "task", "resize", task_id, "0", "0", str(width), str(height))
                failed, detail = self._command_failed(result)
            else:
                failed, detail = True, ""
                stack_id = task.get("stack_id")
                if stack_id:
                    result = self._run_adb_shell(serial, "am", "stack", "move-task", task_id, stack_id, "false")
                    failed, detail = self._command_failed(result)
                if failed:
                    other = next((item for item in all_tasks if item["task_id"] != task_id), None)
                    if other:
                        result = self._run_adb_shell(serial, "am", "task", "focus", other["task_id"])
                        failed, detail = self._command_failed(result)
                    else:
                        # Fallback: move this selected app to the back by showing Home on the virtual display.
                        focus = self._run_adb_shell(serial, "am", "task", "focus", task_id)
                        focus_failed, focus_detail = self._command_failed(focus)
                        if focus_failed:
                            focus = self._run_adb_shell(serial, "am", "start", "--display", display_id, "--windowingMode", windowing_mode, "--activity-reorder-to-front", "-n", shlex.quote(task["component"]))
                            focus_failed, focus_detail = self._command_failed(focus)
                        if focus_failed:
                            failed, detail = True, focus_detail
                        else:
                            result = self._run_adb_shell(serial, "input", "-d", display_id, "keyevent", "KEYCODE_HOME")
                            failed, detail = self._command_failed(result)
            if failed:
                self.root.after(0, self._window_action_done, action, task["name"], detail or "Android did not complete that window action.", True)
            else:
                self._raise_scrcpy_window()
                self.root.after(0, self._window_action_done, action, task["name"], "", False)
        except (OSError, subprocess.SubprocessError) as exc:
            self.root.after(0, self._window_action_done, action, task["name"], str(exc), True)

    def _window_action_done(self, action, name, detail, failed):
        if failed:
            self.set_status(f"Could not {action} {name}", False)
            messagebox.showerror(f"Could not {action} {name}", detail)
        else:
            labels = {"focus": "Focused", "maximize": "Maximized", "unfocus": "Moved to background"}
            self.set_status(f"{labels[action]} {name}", True)
        self.refresh_open_apps()

    def start_display(self):
        if self.scrcpy_process and self.scrcpy_process.poll() is None:
            self.set_status("SCRCPY display is already open", True)
            return
        serial = self.selected_serial()
        if not serial or not any(s == serial and state == "device" for s, state in self.devices):
            self.refresh_devices(silent=True)
            messagebox.showinfo("Connect your phone", "Connect and unlock the phone, then approve USB debugging.")
            return
        if not self.scrcpy or not self.scrcpy.is_file():
            messagebox.showerror("SCRCPY not found", "Install SCRCPY or use Tools… to locate scrcpy.", parent=self.root)
            return
        if not self.adb or not self.adb.is_file():
            messagebox.showerror("ADB not found", "Install SCRCPY or Android Platform Tools, or use Tools… to locate adb.", parent=self.root)
            return
        try:
            width, height, dpi, display_mode = parse_display_mode(self.display_mode_var.get())
        except ValueError as exc:
            messagebox.showerror("Check the resolution", str(exc), parent=self.root)
            self.resolution_menu.focus_set()
            return
        audio_to_pc = self.audio_var.get()
        screen_off = self.screen_off_var.get()
        try:
            self._save_settings(display_mode, self.app_layout_var.get(), audio_to_pc, screen_off)
        except OSError as exc:
            messagebox.showerror("Settings could not be saved", str(exc), parent=self.root)
            return
        self.display_mode_var.set(display_mode)
        self.display_size = (width, height)
        self.display_dpi = dpi
        self.start_button.configure(state="disabled")
        self.display_label.configure(text=f"Starting {width} × {height} virtual display…")
        self.set_status("Starting desktop display…", True)
        # Start discovery alongside SCRCPY startup so the app cards are ready
        # as soon as the new virtual display comes online.
        self.scan_apps()
        threading.Thread(target=self._start_worker, args=(serial, display_mode, audio_to_pc, screen_off), daemon=True).start()

    def _start_worker(self, serial, display_mode, audio_to_pc, screen_off):
        try:
            command = [
                str(self.scrcpy), "--serial", serial, f"--new-display={display_mode}",
                f"--window-title={SCRCPY_WINDOW_TITLE}", "--fullscreen", "--window-borderless",
            ]
            if not audio_to_pc:
                command.append("--no-audio")
            if screen_off:
                command.extend(("--turn-screen-off", "--stay-awake"))
            process_options = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if os.name == "nt" else {}
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, **process_options)
            self.scrcpy_process = process
            threading.Thread(target=self._read_scrcpy_output, args=(process,), daemon=True).start()
            self.root.after(0, self.set_status, "Starting SCRCPY display…", True)
        except OSError as exc:
            self.root.after(0, self._display_error, str(exc))

    def _read_scrcpy_output(self, process):
        for line in iter(process.stdout.readline, ""):
            match = re.search(r"New display:.*?\(id=(\d+)\)", line)
            if match:
                self.display_id = match.group(1)
                self.root.after(0, self._display_ready)
            elif "ERROR" in line:
                self.root.after(0, self.set_status, line.strip()[-120:], False)
        process.stdout.close()

    def _display_ready(self):
        self.start_button.configure(state="normal")
        width, height = self.display_size
        self.display_label.configure(text=f"SCRCPY desktop ready  ·  Display {self.display_id}  ·  {width} × {height} / {self.display_dpi} DPI")
        self.set_status("SCRCPY display ready", True)
        self.refresh_open_apps()

    def _display_error(self, error):
        self.start_button.configure(state="normal")
        self.display_label.configure(text="SCRCPY did not start")
        self.set_status("SCRCPY could not start", False)
        messagebox.showerror("SCRCPY failed", error)

    def poll_process(self):
        process = self.scrcpy_process
        if process and process.poll() is not None:
            self.scrcpy_process = None
            self.display_id = None
            self.open_tasks = {}
            self.start_button.configure(state="normal")
            self.display_label.configure(text=self._display_settings_label())
            self.set_status("SCRCPY display closed", False)
            self._render_open_tasks([])
        self.root.after(800, self.poll_process)

    def launch_app(self, app):
        serial = self.selected_serial()
        if not self.scrcpy_process or self.scrcpy_process.poll() is not None or not self.display_id:
            messagebox.showinfo("Start the desktop display", "Click Start desktop display and wait until its display number appears, then choose an app.")
            return
        self.set_status(f"Opening {app['name']}…", True)
        threading.Thread(target=self._launch_worker, args=(serial, app, self._windowing_mode()), daemon=True).start()

    def _launch_worker(self, serial, app, windowing_mode):
        try:
            result = run([str(self.adb), "-s", serial, "shell", "am", "start", "--display", str(self.display_id), "--windowingMode", windowing_mode, "-f", "0x18000000", "-n", shlex.quote(app["component"])], timeout=15)
            output = (result.stdout + "\n" + result.stderr).strip()
            failed = result.returncode or "Error:" in output or "Exception" in output
            if failed:
                self.root.after(0, self.launch_error, app["name"], output or "Android could not open this app on the virtual display.")
            else:
                self._raise_scrcpy_window()
                self.root.after(0, self.set_status, f"Opened {app['name']} on display {self.display_id}", True)
        except (OSError, subprocess.SubprocessError) as exc:
            self.root.after(0, self.launch_error, app["name"], str(exc))

    def launch_error(self, name, detail):
        self.set_status(f"Could not open {name}", False)
        messagebox.showerror(f"Could not open {name}", detail)

    def stop_display(self):
        process = self.scrcpy_process
        if process and process.poll() is None:
            process.terminate()
        self.display_id = None
        self.open_tasks = {}
        self.display_label.configure(text=self._display_settings_label())
        self.set_status("Closing SCRCPY display…", False)
        self._render_open_tasks([])

    def on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def close(self):
        process = self.scrcpy_process
        if process and process.poll() is None:
            process.terminate()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    AndroidLauncher(root)
    root.mainloop()
