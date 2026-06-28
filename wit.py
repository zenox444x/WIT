#!/usr/bin/env python3
# ============================================================
#   WIT - Windows Is Trash
#   CachyOS utility - GTK4 + libadwaita - Python
#   v4.0 - Welcome dialog + Gaming section + Batch install
#          + App detection + sudo auto-refresh + WiFi/BT fixes
# ============================================================

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk
import subprocess, threading, shutil, os, pty, fcntl, select, termios, struct
import re as _re

# ─── App data ────────────────────────────────────────────────────────────────
APPS = [
    {"name": "Discord",   "pkg": "discord",                "icon": "🎮"},
    {"name": "Steam",     "pkg": "steam",                  "icon": "🕹️"},
    {"name": "Brave",     "pkg": "brave-bin",              "icon": "🦁"},
    {"name": "VLC",       "pkg": "vlc",                    "icon": "🎬"},
    {"name": "Spotify",   "pkg": "spotify",                "icon": "🎵"},
    {"name": "VS Code",   "pkg": "visual-studio-code-bin", "icon": "💻"},
    {"name": "Firefox",   "pkg": "firefox",                "icon": "🦊"},
    {"name": "Obsidian",  "pkg": "obsidian",               "icon": "📔"},
]

GAMING_APPS = [
    {"name": "Lutris",          "pkg": "lutris",                        "icon": "🏆"},
    {"name": "Heroic Launcher", "pkg": "heroic-games-launcher-bin",     "icon": "⚡"},
    {"name": "Wine",            "pkg": "wine",                          "icon": "🍷"},
    {"name": "ProtonUp-Qt",     "pkg": "protonup-qt",                   "icon": "🐧"},
    {"name": "MangoHud",        "pkg": "mangohud",                      "icon": "📊"},
    {"name": "Gamemode",        "pkg": "gamemode",                      "icon": "🚀"},
]

FIXES = [
    {
        "name": "Fix Bluetooth",
        "icon": "📶",
        "desc": "Enable service & unblock rfkill",
        "cmds": [
            "sudo systemctl enable --now bluetooth",
            "sudo rfkill unblock bluetooth",
            "sudo systemctl restart bluetooth",
        ],
    },
    {
        "name": "Fix Wi-Fi",
        "icon": "📡",
        "desc": "Restart NetworkManager & unblock rfkill",
        "cmds": [
            "sudo systemctl restart NetworkManager",
            "sudo rfkill unblock wifi",
            "sudo systemctl enable NetworkManager",
        ],
    },
    {
        "name": "Clean Cache",
        "icon": "🧹",
        "desc": "Remove old package cache",
        "cmds": ["yay -Sc --noconfirm --sudoflags '-A'"],
    },
    {
        "name": "Full System Update",
        "icon": "🔄",
        "desc": "Update all packages via yay",
        "cmds": ["yay -Syu --noconfirm --sudoflags '-A'"],
    },
]

# ─── WiFi fix steps (full diagnostic + fix chain) ────────────────────────────
WIFI_FIX_STEPS = [
    "echo '--- Checking WiFi hardware ---'",
    "ip a | grep -E 'wlan|wlp' || echo 'No WiFi interface found'",
    "lspci | grep -i network || true",
    "echo '--- Checking NetworkManager status ---'",
    "systemctl status NetworkManager --no-pager || true",
    "echo '--- Restarting WiFi ---'",
    "sudo systemctl restart NetworkManager",
    "sudo nmcli radio wifi off && sleep 1 && sudo nmcli radio wifi on",
    "sudo rfkill unblock wifi",
    "sudo systemctl enable NetworkManager",
    "echo '--- Scanning for networks ---'",
    "nmcli dev wifi list || true",
    "echo '--- Final status ---'",
    "systemctl is-active NetworkManager && echo 'NetworkManager: OK' || echo 'NetworkManager: FAILED'",
    "rfkill list wifi",
]

# ─── Bluetooth fix steps (full diagnostic + fix chain) ───────────────────────
BT_FIX_STEPS = [
    "echo '--- Checking Bluetooth hardware ---'",
    "lsusb | grep -i bluetooth || echo 'No USB Bluetooth found'",
    "lspci | grep -i bluetooth || true",
    "echo '--- Checking Bluetooth service ---'",
    "systemctl status bluetooth --no-pager || true",
    "echo '--- Restarting Bluetooth ---'",
    "sudo systemctl restart bluetooth",
    "sudo modprobe -r btusb 2>/dev/null; sudo modprobe btusb",
    "sudo rfkill unblock bluetooth",
    "sudo systemctl enable bluetooth",
    "echo '--- Final status ---'",
    "systemctl is-active bluetooth && echo 'Bluetooth: OK' || echo 'Bluetooth: FAILED'",
    "rfkill list bluetooth",
    "lsmod | grep bluetooth | head -5",
]

# ─── yay install chain ───────────────────────────────────────────────────────
YAY_INSTALL_STEPS = [
    "sudo pacman -S --needed --noconfirm git base-devel",
    "rm -rf /tmp/yay-build && git clone https://aur.archlinux.org/yay.git /tmp/yay-build",
    "cd /tmp/yay-build && makepkg -si --noconfirm --needed",
    "rm -rf /tmp/yay-build",
]

# ─── ANSI strip ──────────────────────────────────────────────────────────────
_ANSI_RE = _re.compile(r"\x1b\[[0-9;]*[mGKHFJ]|\x1b\][^\x07]*\x07|\r")
def _strip_ansi(t: str) -> str:
    return _ANSI_RE.sub("", t)

# ─── Error messages (user-friendly) ──────────────────────────────────────────
def _friendly(text: str) -> str:
    t = text.lower()
    if "permission denied" in t or "access denied" in t:
        return "⛔ Permission denied — make sure sudo is authenticated above."
    if "command not found" in t or "not found" in t:
        return "❓ Command not found — the package may not be installed."
    if "failed to connect" in t or "could not connect" in t:
        return "🌐 Network error — check your internet connection."
    if "no space left" in t:
        return "💾 Disk full — free up some space and try again."
    if "already installed" in t:
        return "✅ Already installed — nothing to do."
    if "error:" in t or "failed" in t:
        return f"❌ {text.strip()}"
    return text

# ─── CSS ─────────────────────────────────────────────────────────────────────
CSS = """
/* Animations */
@keyframes pulse-glow {
  0%   { box-shadow: 0 0 0px  0px alpha(#e94560, 0.0); }
  50%  { box-shadow: 0 0 18px 6px alpha(#e94560, 0.35); }
  100% { box-shadow: 0 0 0px  0px alpha(#e94560, 0.0); }
}
@keyframes badge-pop {
  0%   { opacity: 0.6; }
  60%  { opacity: 1; }
  100% { opacity: 1; }
}
@keyframes slide-in-up {
  from { opacity: 0; margin-top: 16px; }
  to   { opacity: 1; margin-top: 0; }
}

/* Base */
window { background-color: #0b0b18; color: #dde3f0; }

/* Header */
.wit-header {
  background: linear-gradient(135deg, #10102a 0%, #181838 60%, #0e2050 100%);
  padding: 14px 24px 12px 24px;
  border-bottom: 1px solid alpha(#e94560, 0.22);
}
.wit-wordmark { font-size: 32px; font-weight: 900; color: #e94560; letter-spacing: 6px; animation: pulse-glow 3.5s ease-in-out infinite; }
.wit-tagline  { font-size: 9px;  font-weight: 700; color: #606888; letter-spacing: 3px; margin-top: 2px; }
.wit-version  { font-size: 9px;  color: #313660; letter-spacing: 1px; }

/* sudo bar */
.sudo-bar        { background: #0d0d1e; border-bottom: 1px solid #1c1c38; padding: 7px 22px; }
.sudo-bar-authed { background: #080f0a; border-bottom: 1px solid #163016; padding: 7px 22px; }
.sudo-label      { font-size: 11px; font-weight: 700; color: #606888; letter-spacing: 1px; }
.sudo-label-ok   { font-size: 11px; font-weight: 700; color: #30c984; letter-spacing: 1px; }
.sudo-label-err  { font-size: 11px; font-weight: 700; color: #f06a7a; letter-spacing: 1px; }
.sudo-entry {
  background: #13132a; color: #dde3f0;
  border-radius: 8px; border: 1px solid #28285a;
  font-family: monospace; font-size: 12px; min-width: 210px;
}
.sudo-entry:focus { border-color: #e94560; }
.sudo-btn {
  background: #e94560; color: white;
  border-radius: 8px; font-weight: 800; font-size: 11px;
  padding: 6px 16px; letter-spacing: 1px;
}
.sudo-btn:hover    { background: #c72e48; }
.sudo-btn:disabled { background: #1c1c40; color: #313660; }
.sudo-badge-ok   { background: #0a2818; color: #30c984; border-radius: 20px; padding: 4px 14px; font-size: 11px; font-weight: 700; border: 1px solid #054a30; }
.sudo-refresh-badge { background: #1a1a3a; color: #818cf8; border-radius: 20px; padding: 4px 14px; font-size: 10px; font-weight: 600; border: 1px solid #2a2a60; }

/* yay badge */
.badge-checking { background: #1c1c38; color: #606888; border-radius: 20px; padding: 5px 16px; font-size: 11px; font-weight: 700; letter-spacing: 1px; border: 1px solid #28285a; }
.badge-ok       { background: #0a2818; color: #30c984; border-radius: 20px; padding: 5px 16px; font-size: 11px; font-weight: 700; letter-spacing: 1px; border: 1px solid #054a30; animation: badge-pop 0.4s ease; }
.badge-fail     { background: #280d14; color: #f06a7a; border-radius: 20px; padding: 5px 16px; font-size: 11px; font-weight: 700; letter-spacing: 1px; border: 1px solid #7a1c28; animation: badge-pop 0.4s ease; }

/* yay missing banner */
.yay-missing-bar   { background: #170f04; border-bottom: 1px solid #352408; padding: 10px 22px; }
.yay-missing-label { font-size: 12px; font-weight: 700; color: #f0b040; }
.yay-install-btn {
  background: #7a380c; color: #f5d090;
  border-radius: 9px; font-weight: 800; font-size: 12px;
  padding: 7px 18px; letter-spacing: 1px; border: 1px solid #a04a10;
}
.yay-install-btn:hover    { background: #a04a10; }
.yay-install-btn:disabled { background: #201508; color: #604a28; }

/* Re-check button */
.check-btn {
  background: alpha(#e94560, 0.10); color: #e94560;
  border-radius: 10px; border: 1px solid alpha(#e94560, 0.28);
  font-size: 11px; font-weight: 700; padding: 5px 12px; letter-spacing: 1px;
}
.check-btn:hover { background: alpha(#e94560, 0.22); }

/* Batch install button */
.batch-btn {
  background: alpha(#818cf8, 0.12); color: #818cf8;
  border-radius: 10px; border: 1px solid alpha(#818cf8, 0.30);
  font-size: 11px; font-weight: 700; padding: 5px 14px; letter-spacing: 1px;
}
.batch-btn:hover    { background: alpha(#818cf8, 0.24); }
.batch-btn:disabled { background: alpha(#818cf8, 0.05); color: #3a4070; border-color: #2a2a50; }

/* Section headers */
.section-eyebrow { font-size: 9px; font-weight: 800; color: #313660; letter-spacing: 4px; margin-bottom: 2px; }
.section-title   { font-size: 15px; font-weight: 700; color: #b8c4e0; }

/* Tab bar */
.tab-row { background: #0d0d20; border-bottom: 1px solid #1c1c38; padding: 0 22px; }
.tab-btn {
  background: transparent; color: #606888;
  border-radius: 0; border: none; border-bottom: 2px solid transparent;
  font-size: 12px; font-weight: 700; padding: 10px 18px; letter-spacing: 1px;
}
.tab-btn:hover  { color: #aab4d0; }
.tab-btn-active { color: #e94560; border-bottom-color: #e94560; }

/* App cards */
.app-card {
  background: #121228; border-radius: 14px;
  border: 1px solid #1c1c3a; padding: 4px;
  animation: slide-in-up 320ms ease both;
}
.app-card:hover { border-color: alpha(#e94560, 0.45); }
.app-icon-label { font-size: 24px; min-width: 42px; min-height: 42px; }
.app-name       { font-size: 13px; font-weight: 700; color: #dde3f0; }
.app-pkg        { font-size: 10px; color: #313660; font-family: monospace; }

/* Install buttons */
.btn-install     { background: #e94560; color: white; border-radius: 9px; font-weight: 800; font-size: 11px; letter-spacing: 1px; padding: 6px 14px; min-width: 78px; }
.btn-install:hover    { background: #c72e48; }
.btn-install:disabled { background: #1c1c3a; color: #313660; }
.btn-installing  { background: #24244a; color: #606888; border-radius: 9px; font-weight: 700; font-size: 11px; padding: 6px 14px; min-width: 78px; }
.btn-done        { background: #0a2818; color: #30c984; border-radius: 9px; font-weight: 800; font-size: 11px; padding: 6px 14px; border: 1px solid #054a30; min-width: 78px; }
.btn-error       { background: #280d14; color: #f06a7a; border-radius: 9px; font-weight: 800; font-size: 11px; padding: 6px 14px; border: 1px solid #7a1c28; min-width: 78px; }

/* Fix cards */
.fix-card       { background: #121228; border-radius: 14px; border: 1px solid #1c1c3a; padding: 6px; animation: slide-in-up 320ms ease both; }
.fix-card:hover { border-color: alpha(#606888, 0.45); }
.fix-icon       { font-size: 22px; }
.fix-name       { font-size: 13px; font-weight: 700; color: #dde3f0; }
.fix-desc       { font-size: 10px; color: #313660; }
.btn-fix         { background: #181840; color: #818cf8; border-radius: 9px; font-weight: 700; font-size: 11px; padding: 6px 14px; border: 1px solid #28286a; letter-spacing: 1px; min-width: 70px; }
.btn-fix:hover   { background: #20205a; }
.btn-fix:disabled { background: #14142e; color: #313660; border-color: #1c1c3a; }
.btn-fix-running { background: #182818; color: #30c984; border-radius: 9px; font-weight: 700; font-size: 11px; padding: 6px 14px; min-width: 70px; }

/* Advanced fix buttons */
.btn-advanced { background: #1a1228; color: #c084fc; border-radius: 9px; font-weight: 700; font-size: 11px; padding: 6px 14px; border: 1px solid #3a2060; letter-spacing: 1px; min-width: 100px; }
.btn-advanced:hover { background: #221840; }
.btn-advanced:disabled { background: #120c20; color: #3a2060; border-color: #1c1030; }

/* Progress bar */
.install-progress { min-height: 4px; border-radius: 2px; }
.install-progress progress { background: #e94560; border-radius: 2px; }
.install-progress trough { background: #1c1c3a; border-radius: 2px; }

/* Terminal */
.terminal-panel     { background: #06060f; border-radius: 0 0 12px 12px; border: 1px solid #1c1c3a; border-top: none; }
.terminal-titlebar  { background: #0f0f24; border-radius: 12px 12px 0 0; border: 1px solid #1c1c3a; padding: 6px 12px; }
.terminal-title     { font-size: 10px; font-weight: 700; color: #313660; letter-spacing: 2px; }
.terminal-dot-red    { background: #e94560; border-radius: 50%; min-width: 10px; min-height: 10px; }
.terminal-dot-yellow { background: #f0b040; border-radius: 50%; min-width: 10px; min-height: 10px; }
.terminal-dot-green  { background: #30c984; border-radius: 50%; min-width: 10px; min-height: 10px; }
.terminal-view {
  background: transparent; color: #b8c4e0;
  font-family: "JetBrains Mono","Fira Code","Hack","Monospace",monospace;
  font-size: 11px; padding: 4px;
}
.terminal-input {
  background: transparent; color: #40d0a0;
  font-family: "JetBrains Mono","Fira Code","Hack","Monospace",monospace;
  font-size: 11px; border: none; box-shadow: none; caret-color: #e94560;
}
.terminal-prompt-label { color: #e94560; font-family: "JetBrains Mono","Fira Code","Hack","Monospace",monospace; font-size: 11px; font-weight: 700; padding: 0 4px; }
.terminal-input-row    { background: #0c0c1e; border-top: 1px solid #1c1c3a; padding: 4px 8px; border-radius: 0 0 12px 12px; }
.term-clear-btn { background: alpha(#313660, 0.3); color: #606888; border-radius: 6px; font-size: 10px; padding: 2px 8px; border: 1px solid #1c1c3a; }
.term-clear-btn:hover { background: alpha(#313660, 0.6); color: #b8c4e0; }

/* Misc */
.dim-sep { background: #1c1c3a; min-height: 1px; }
"""

# =============================================================================
class WITApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.wit.cachy")
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        self.win = WITWindow(application=app)
        self.win.present()
        GLib.timeout_add(200, self.win._maybe_show_welcome)

# =============================================================================
class WITWindow(Adw.ApplicationWindow):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.set_title("WIT")
        self.set_default_size(1160, 780)

        self.yay_ok       = False
        self.sudo_ok      = False
        self._running     = False
        self._sudo_pass   = ""          # held in memory only, never written to disk
        self._askpass_path = os.path.expanduser("~/.cache/wit-askpass.sh")
        self._app_btns: dict[str, Gtk.Button] = {}     # pkg -> button (all sections)
        self._sudo_refresh_id = None

        # CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Root
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        root.append(self._build_header())
        root.append(self._build_sudo_bar())
        self._yay_banner = self._build_yay_banner()
        root.append(self._yay_banner)

        # Tab row
        root.append(self._build_tab_row())

        # Stack (tab pages)
        self._stack = Gtk.Stack()
        self._stack.set_vexpand(True)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(160)
        root.append(self._stack)

        # Page 1: Apps + Fixes (split)
        self._stack.add_named(self._build_main_page(), "main")
        # Page 2: Gaming
        self._stack.add_named(self._build_gaming_page(), "gaming")
        # Page 3: Advanced fixes
        self._stack.add_named(self._build_advanced_page(), "advanced")

        # Boot
        GLib.timeout_add(500, self._auto_check)
        # sudo auto-refresh every 5 min (300s)
        self._sudo_refresh_id = GLib.timeout_add_seconds(300, self._auto_sudo_refresh)

    # ─── Welcome dialog ───────────────────────────────────────────────────────
    def _maybe_show_welcome(self):
        flag = os.path.expanduser("~/.config/wit/.welcomed")
        if not os.path.exists(flag):
            self._show_welcome_dialog()
            os.makedirs(os.path.dirname(flag), exist_ok=True)
            open(flag, "w").close()
        return False   # run once

    def _show_welcome_dialog(self):
        dlg = Adw.MessageDialog.new(
            self,
            "Welcome to WIT",
            "The CachyOS toolkit for apps, gaming, and system fixes.\n\n"
            "Get started:\n"
            "  1. Authenticate sudo in the bar at the top\n"
            "  2. Install yay if the banner appears\n"
            "  3. Pick apps or run a fix — the terminal shows everything live",
        )
        dlg.add_response("ok", "Let's go!")
        dlg.set_default_response("ok")
        dlg.set_close_response("ok")
        dlg.present()

    # ─── Header ───────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        hdr.add_css_class("wit-header")

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        left.set_hexpand(True)
        wm = Gtk.Label(label="WIT")
        wm.add_css_class("wit-wordmark"); wm.set_halign(Gtk.Align.START)
        tl = Gtk.Label(label="WINDOWS IS TRASH  ·  CACHY OS TOOLKIT")
        tl.add_css_class("wit-tagline"); tl.set_halign(Gtk.Align.START)
        ver = Gtk.Label(label="v4.0.0")
        ver.add_css_class("wit-version"); ver.set_halign(Gtk.Align.START)
        left.append(wm); left.append(tl); left.append(ver)
        hdr.append(left)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                        spacing=6, halign=Gtk.Align.END, valign=Gtk.Align.CENTER)
        self.yay_badge = Gtk.Label(label="Checking yay…")
        self.yay_badge.add_css_class("badge-checking")
        right.append(self.yay_badge)
        chk = Gtk.Button(label="Re-check")
        chk.add_css_class("check-btn")
        chk.connect("clicked", lambda _: self._check_yay())
        right.append(chk)
        hdr.append(right)
        return hdr

    # ─── sudo bar ─────────────────────────────────────────────────────────────
    def _build_sudo_bar(self):
        self._sudo_bar_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._sudo_bar_box.add_css_class("sudo-bar")

        Gtk.Label(label="🔑")   # just for spacing — appended below
        lock = Gtk.Label(label="🔑")
        lock.set_margin_end(2)
        lbl = Gtk.Label(label="Root access required:")
        lbl.add_css_class("sudo-label")

        self._sudo_entry = Gtk.Entry()
        self._sudo_entry.add_css_class("sudo-entry")
        self._sudo_entry.set_placeholder_text("sudo password…")
        self._sudo_entry.set_visibility(False)
        self._sudo_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self._sudo_entry.connect("activate", self._on_sudo_submit)

        auth_btn = Gtk.Button(label="Authenticate")
        auth_btn.add_css_class("sudo-btn")
        auth_btn.connect("clicked", self._on_sudo_submit)

        self._sudo_status = Gtk.Label(label="")
        self._sudo_status.add_css_class("sudo-label")
        self._sudo_status.set_hexpand(True)
        self._sudo_status.set_halign(Gtk.Align.END)

        self._sudo_refresh_lbl = Gtk.Label(label="")
        self._sudo_refresh_lbl.add_css_class("sudo-refresh-badge")
        self._sudo_refresh_lbl.set_visible(False)

        self._sudo_bar_box.append(lock)
        self._sudo_bar_box.append(lbl)
        self._sudo_bar_box.append(self._sudo_entry)
        self._sudo_bar_box.append(auth_btn)
        self._sudo_bar_box.append(self._sudo_status)
        self._sudo_bar_box.append(self._sudo_refresh_lbl)
        return self._sudo_bar_box

    # ─── yay banner ───────────────────────────────────────────────────────────
    def _build_yay_banner(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        bar.add_css_class("yay-missing-bar")
        bar.set_visible(False)

        warn = Gtk.Label(
            label="⚠  yay is not installed — install it automatically to unlock the app installer.")
        warn.add_css_class("yay-missing-label")
        warn.set_hexpand(True); warn.set_halign(Gtk.Align.START)

        self._yay_install_btn = Gtk.Button(label="Install yay")
        self._yay_install_btn.add_css_class("yay-install-btn")
        self._yay_install_btn.connect("clicked", self._on_install_yay)

        bar.append(warn); bar.append(self._yay_install_btn)
        return bar

    # ─── Tab row ──────────────────────────────────────────────────────────────
    def _build_tab_row(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        row.add_css_class("tab-row")
        self._tab_btns = {}
        tabs = [
            ("main",     "📦  Apps & Fixes"),
            ("gaming",   "🎮  Gaming"),
            ("advanced", "🔧  Advanced Fixes"),
        ]
        for page_id, label in tabs:
            btn = Gtk.Button(label=label)
            btn.add_css_class("tab-btn")
            btn.connect("clicked", lambda b, pid=page_id: self._switch_tab(pid))
            row.append(btn)
            self._tab_btns[page_id] = btn
        self._switch_tab("main")
        return row

    def _switch_tab(self, page_id):
        for pid, btn in self._tab_btns.items():
            btn.remove_css_class("tab-btn-active")
        self._tab_btns[page_id].add_css_class("tab-btn-active")
        if hasattr(self, "_stack"):
            self._stack.set_visible_child_name(page_id)

    # ─── Main page (Apps + Quick Fixes, split) ────────────────────────────────
    def _build_main_page(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(600)
        paned.set_wide_handle(True)

        # Left side
        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_hexpand(True)
        left_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        left_body.set_margin_top(20); left_body.set_margin_bottom(24)
        left_body.set_margin_start(22); left_body.set_margin_end(16)
        left_scroll.set_child(left_body)
        left_body.append(self._build_apps_section())
        left_body.append(self._make_sep())
        left_body.append(self._build_fixes_section())
        paned.set_start_child(left_scroll)

        # Right side: terminal
        term_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        term_box.set_margin_top(20); term_box.set_margin_bottom(24)
        term_box.set_margin_start(8); term_box.set_margin_end(22)
        term_box.append(self._build_terminal())
        paned.set_end_child(term_box)
        return paned

    # ─── Gaming page ──────────────────────────────────────────────────────────
    def _build_gaming_page(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(600)
        paned.set_wide_handle(True)

        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_hexpand(True)
        left_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        left_body.set_margin_top(20); left_body.set_margin_bottom(24)
        left_body.set_margin_start(22); left_body.set_margin_end(16)
        left_scroll.set_child(left_body)
        left_body.append(self._build_gaming_section())
        paned.set_start_child(left_scroll)

        # Gaming tab reuses the same terminal widget reference
        right_note = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right_note.set_margin_top(20); right_note.set_margin_bottom(24)
        right_note.set_margin_start(8); right_note.set_margin_end(22)
        hint = Gtk.Label(label="Terminal output appears in the Apps & Fixes tab →")
        hint.add_css_class("sudo-label"); hint.set_valign(Gtk.Align.CENTER)
        hint.set_vexpand(True); hint.set_halign(Gtk.Align.CENTER)
        right_note.append(hint)
        paned.set_end_child(right_note)
        return paned

    # ─── Advanced fixes page ──────────────────────────────────────────────────
    def _build_advanced_page(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(600)
        paned.set_wide_handle(True)

        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_hexpand(True)
        left_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        left_body.set_margin_top(20); left_body.set_margin_bottom(24)
        left_body.set_margin_start(22); left_body.set_margin_end(16)
        left_scroll.set_child(left_body)
        left_body.append(self._build_advanced_fixes_section())
        paned.set_start_child(left_scroll)

        right_note = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right_note.set_margin_top(20); right_note.set_margin_bottom(24)
        right_note.set_margin_start(8); right_note.set_margin_end(22)
        hint = Gtk.Label(label="Terminal output appears in the Apps & Fixes tab →")
        hint.add_css_class("sudo-label"); hint.set_valign(Gtk.Align.CENTER)
        hint.set_vexpand(True); hint.set_halign(Gtk.Align.CENTER)
        right_note.append(hint)
        paned.set_end_child(right_note)
        return paned

    # ─── Section helpers ──────────────────────────────────────────────────────
    def _section_header(self, eyebrow, title, action=None):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        labels.set_hexpand(True)
        ey = Gtk.Label(label=eyebrow); ey.add_css_class("section-eyebrow"); ey.set_halign(Gtk.Align.START)
        ti = Gtk.Label(label=title);   ti.add_css_class("section-title");   ti.set_halign(Gtk.Align.START)
        labels.append(ey); labels.append(ti)
        row.append(labels)
        if action:
            row.append(action)
        return row

    def _make_sep(self):
        s = Gtk.Separator(); s.add_css_class("dim-sep"); return s

    # ─── Apps section ─────────────────────────────────────────────────────────
    def _build_apps_section(self):
        batch_btn = Gtk.Button(label="Install All")
        batch_btn.add_css_class("batch-btn")
        batch_btn.set_sensitive(False)
        batch_btn.connect("clicked", lambda _: self._batch_install(APPS))
        self._apps_batch_btn = batch_btn

        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("PACKAGES", "Install Apps", batch_btn))

        # Progress bar
        self._install_progress = Gtk.ProgressBar()
        self._install_progress.add_css_class("install-progress")
        self._install_progress.set_show_text(True)
        self._install_progress.set_visible(False)
        sec.append(self._install_progress)

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(2); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        for app in APPS:
            grid.append(self._make_app_card(app))
        sec.append(grid)
        return sec

    def _make_app_card(self, app):
        outer = Gtk.Box()
        outer.set_hexpand(True)
        outer.set_margin_top(1); outer.set_margin_bottom(1)
        outer.set_margin_start(1); outer.set_margin_end(1)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("app-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label=app["icon"])
        icon_lbl.add_css_class("app-icon-label")
        icon_lbl.set_margin_start(10); icon_lbl.set_margin_top(8); icon_lbl.set_margin_bottom(8)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info.set_hexpand(True)
        name_lbl = Gtk.Label(label=app["name"])
        name_lbl.add_css_class("app-name"); name_lbl.set_halign(Gtk.Align.START)
        pkg_lbl = Gtk.Label(label=app["pkg"])
        pkg_lbl.add_css_class("app-pkg"); pkg_lbl.set_halign(Gtk.Align.START)
        info.append(name_lbl); info.append(pkg_lbl)

        btn = Gtk.Button(label="Install")
        btn.add_css_class("btn-install"); btn.set_sensitive(False)
        btn.set_valign(Gtk.Align.CENTER); btn.set_margin_end(10)
        btn.connect("clicked", lambda _, a=app, b=btn: self._on_install(a, b))
        self._app_btns[app["pkg"]] = btn

        card.append(icon_lbl); card.append(info); card.append(btn)
        outer.append(card)
        return outer

    # ─── Gaming section ───────────────────────────────────────────────────────
    def _build_gaming_section(self):
        batch_btn = Gtk.Button(label="Install All")
        batch_btn.add_css_class("batch-btn")
        batch_btn.set_sensitive(False)
        batch_btn.connect("clicked", lambda _: self._batch_install(GAMING_APPS))
        self._gaming_batch_btn = batch_btn

        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("GAMING", "Game Launchers & Tools", batch_btn))

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(2); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        for app in GAMING_APPS:
            grid.append(self._make_app_card(app))
        sec.append(grid)
        return sec

    # ─── Quick fixes section ──────────────────────────────────────────────────
    def _build_fixes_section(self):
        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("QUICK FIXES", "Common System Fixes"))
        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(2); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        for fix in FIXES:
            grid.append(self._make_fix_card(fix))
        sec.append(grid)
        return sec

    def _make_fix_card(self, fix):
        outer = Gtk.Box(); outer.set_hexpand(True)
        outer.set_margin_top(1); outer.set_margin_bottom(1)
        outer.set_margin_start(1); outer.set_margin_end(1)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("fix-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label=fix["icon"])
        icon_lbl.add_css_class("fix-icon")
        icon_lbl.set_margin_start(12); icon_lbl.set_margin_top(12); icon_lbl.set_margin_bottom(12)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        name_lbl = Gtk.Label(label=fix["name"])
        name_lbl.add_css_class("fix-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label=fix["desc"])
        desc_lbl.add_css_class("fix-desc"); desc_lbl.set_halign(Gtk.Align.START)
        text.append(name_lbl); text.append(desc_lbl)

        btn = Gtk.Button(label="Run")
        btn.add_css_class("btn-fix"); btn.set_valign(Gtk.Align.CENTER)
        btn.set_margin_end(12)
        btn.connect("clicked", lambda _, f=fix, b=btn: self._on_fix(f, b))
        card.append(icon_lbl); card.append(text); card.append(btn)
        outer.append(card)
        return outer

    # ─── Advanced fixes section (WiFi / BT full diagnostic) ──────────────────
    def _build_advanced_fixes_section(self):
        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        sec.append(self._section_header("DIAGNOSTICS", "Advanced System Repair"))

        # WiFi card
        wifi_card = self._make_advanced_fix_card(
            icon="📡",
            title="Full Wi-Fi Diagnostic & Fix",
            desc="Checks hardware, restarts NetworkManager, unblocks rfkill,\nscans networks, and reports final status.",
            btn_label="Run Wi-Fi Fix",
            steps=WIFI_FIX_STEPS,
        )
        sec.append(wifi_card)

        # Bluetooth card
        bt_card = self._make_advanced_fix_card(
            icon="🔵",
            title="Full Bluetooth Diagnostic & Fix",
            desc="Checks hardware, reloads kernel modules, unblocks rfkill,\nrestarts service, and reports final status.",
            btn_label="Run BT Fix",
            steps=BT_FIX_STEPS,
        )
        sec.append(bt_card)

        return sec

    def _make_advanced_fix_card(self, icon, title, desc, btn_label, steps):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("fix-card")
        card.set_margin_top(2); card.set_margin_bottom(2)
        card.set_margin_start(2); card.set_margin_end(2)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top_row.set_margin_start(12); top_row.set_margin_top(12); top_row.set_margin_end(12)

        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.add_css_class("fix-icon")

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text_box.set_hexpand(True)
        name_lbl = Gtk.Label(label=title)
        name_lbl.add_css_class("fix-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label=desc)
        desc_lbl.add_css_class("fix-desc"); desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_wrap(True)
        text_box.append(name_lbl); text_box.append(desc_lbl)

        btn = Gtk.Button(label=btn_label)
        btn.add_css_class("btn-advanced")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _, s=steps, b=btn: self._on_advanced_fix(s, b))

        top_row.append(icon_lbl); top_row.append(text_box); top_row.append(btn)
        card.append(top_row)

        sep = Gtk.Separator(); sep.add_css_class("dim-sep")
        sep.set_margin_start(12); sep.set_margin_end(12)
        card.append(sep)

        # Step list preview
        step_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        step_box.set_margin_start(16); step_box.set_margin_bottom(12)
        step_box.set_margin_end(12)
        for i, step in enumerate(steps[:5]):
            lbl = Gtk.Label(label=f"  {step}")
            lbl.add_css_class("app-pkg"); lbl.set_halign(Gtk.Align.START)
            step_box.append(lbl)
        if len(steps) > 5:
            more = Gtk.Label(label=f"  … and {len(steps)-5} more steps")
            more.add_css_class("app-pkg"); more.set_halign(Gtk.Align.START)
            step_box.append(more)
        card.append(step_box)
        return card

    # ─── Terminal panel ───────────────────────────────────────────────────────
    def _build_terminal(self):
        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        wrapper.set_vexpand(True)

        # Title bar
        titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        titlebar.add_css_class("terminal-titlebar")
        for cls in ("terminal-dot-red", "terminal-dot-yellow", "terminal-dot-green"):
            d = Gtk.Box(); d.add_css_class(cls); d.set_valign(Gtk.Align.CENTER)
            if cls == "terminal-dot-red": d.set_margin_start(4)
            titlebar.append(d)
        title_lbl = Gtk.Label(label="TERMINAL")
        title_lbl.add_css_class("terminal-title"); title_lbl.set_hexpand(True)
        title_lbl.set_halign(Gtk.Align.CENTER)
        clear_btn = Gtk.Button(label="clear")
        clear_btn.add_css_class("term-clear-btn"); clear_btn.set_valign(Gtk.Align.CENTER)
        clear_btn.connect("clicked", self._clear_terminal)
        titlebar.append(title_lbl); titlebar.append(clear_btn)
        wrapper.append(titlebar)

        # Output panel
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.add_css_class("terminal-panel"); panel.set_vexpand(True)
        out_scroll = Gtk.ScrolledWindow()
        out_scroll.set_vexpand(True)
        out_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.term_view = Gtk.TextView()
        self.term_view.set_editable(False); self.term_view.set_cursor_visible(False)
        self.term_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.term_view.add_css_class("terminal-view")
        self.term_view.set_left_margin(8); self.term_view.set_right_margin(8)
        self.term_view.set_top_margin(8); self.term_view.set_bottom_margin(4)
        self.term_buf = self.term_view.get_buffer()
        out_scroll.set_child(self.term_view)
        panel.append(out_scroll)

        # Color tags
        for name, color, weight in [
            ("stdout",   "#b8c4e0", 400),
            ("stderr",   "#f06a7a", 400),
            ("ok",       "#30c984", 700),
            ("err",      "#f06a7a", 700),
            ("info",     "#818cf8", 700),
            ("prompt",   "#e94560", 700),
            ("cmd_echo", "#f0b040", 400),
            ("dim",      "#313660", 400),
        ]:
            self.term_buf.create_tag(name, foreground=color, weight=weight)

        # Input row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        input_row.add_css_class("terminal-input-row")
        prompt_lbl = Gtk.Label(label="$"); prompt_lbl.add_css_class("terminal-prompt-label")
        self.term_input = Gtk.Entry()
        self.term_input.add_css_class("terminal-input"); self.term_input.set_hexpand(True)
        self.term_input.set_placeholder_text("Enter command…")
        self.term_input.connect("activate", self._on_term_enter)
        input_row.append(prompt_lbl); input_row.append(self.term_input)
        panel.append(input_row)
        wrapper.append(panel)

        self._term_scroll = out_scroll
        self._term_write("WIT v4.0 — authenticate sudo, then use the cards.\n", "info")
        self._term_write("$ ", "prompt")
        return wrapper

    # ─── Terminal helpers ─────────────────────────────────────────────────────
    def _term_write(self, text, tag="stdout"):
        end = self.term_buf.get_end_iter()
        self.term_buf.insert_with_tags_by_name(end, text, tag)
        GLib.idle_add(self._scroll_term)

    def _scroll_term(self):
        adj = self._term_scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def _clear_terminal(self, _=None):
        self.term_buf.set_text("")
        self._term_write("Terminal cleared.\n", "dim")
        self._term_write("$ ", "prompt")

    def _on_term_enter(self, entry):
        cmd = entry.get_text().strip(); entry.set_text("")
        if not cmd: return
        if self._running:
            self._term_write("[busy — wait for current task]\n", "err"); return
        self._term_write(f"{cmd}\n", "cmd_echo")
        self._run_in_terminal(cmd)

    # ─── Core: run command via pty ────────────────────────────────────────────
    def _run_in_terminal(self, cmd, on_done=None):
        self._running = True
        self.term_input.set_sensitive(False)

        def worker():
            success = False
            try:
                master_fd, slave_fd = pty.openpty()
                ws = struct.pack("HHHH", 40, 120, 0, 0)
                fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, ws)
                env = os.environ.copy()
                env.update({"TERM": "xterm-256color", "COLUMNS": "120", "LINES": "40"})
                # Inject askpass so sudo/yay never need an interactive terminal
                if self.sudo_ok and os.path.exists(self._askpass_path):
                    env["SUDO_ASKPASS"] = self._askpass_path
                proc = subprocess.Popen(
                    cmd, shell=True,
                    stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                    close_fds=True, env=env,
                )
                os.close(slave_fd)
                buf = b""
                while True:
                    r, _, _ = select.select([master_fd], [], [], 0.04)
                    if r:
                        try:
                            chunk = os.read(master_fd, 4096)
                        except OSError:
                            break
                        if not chunk: break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            raw = _strip_ansi(line.decode("utf-8", errors="replace"))
                            txt = _friendly(raw) if raw else raw
                            if txt:
                                GLib.idle_add(self._term_write, txt + "\n", "stdout")
                    elif proc.poll() is not None:
                        try:
                            rest = os.read(master_fd, 4096)
                            if rest: buf += rest
                        except OSError: pass
                        break
                if buf:
                    raw = _strip_ansi(buf.decode("utf-8", errors="replace"))
                    txt = _friendly(raw) if raw.strip() else raw
                    if txt.strip():
                        GLib.idle_add(self._term_write, txt + "\n", "stdout")
                try: os.close(master_fd)
                except OSError: pass
                proc.wait()
                success = proc.returncode == 0
            except Exception as exc:
                GLib.idle_add(self._term_write, f"[error: {exc}]\n", "err")
            GLib.idle_add(self._cmd_finished, success, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _cmd_finished(self, success, on_done):
        self._running = False
        self._term_write("[done]\n" if success else "[failed]\n",
                         "ok" if success else "err")
        self._term_write("$ ", "prompt")
        self.term_input.set_sensitive(True)
        self.term_input.grab_focus()
        if on_done: on_done(success)

    # ─── sudo auth ────────────────────────────────────────────────────────────
    def _on_sudo_submit(self, _):
        password = self._sudo_entry.get_text()
        if not password:
            self._sudo_status.set_label("Enter your password first.")
            self._sudo_status.remove_css_class("sudo-label-ok")
            self._sudo_status.add_css_class("sudo-label-err")
            return
        self._sudo_status.set_label("Authenticating…")
        self._sudo_status.remove_css_class("sudo-label-ok")
        self._sudo_status.remove_css_class("sudo-label-err")
        self._sudo_status.add_css_class("sudo-label")
        self._sudo_entry.set_sensitive(False)
        threading.Thread(target=self._sudo_auth_thread, args=(password,), daemon=True).start()

    def _sudo_auth_thread(self, password):
        try:
            proc = subprocess.run(
                ["sudo", "-v", "-S"],
                input=password + "\n",
                capture_output=True, text=True, timeout=15,
            )
            ok = proc.returncode == 0
        except subprocess.TimeoutExpired:
            ok = False
        GLib.idle_add(self._apply_sudo_result, ok)

    def _apply_sudo_result(self, ok):
        raw_pass = self._sudo_entry.get_text()
        self._sudo_entry.set_text("")
        self._sudo_entry.set_sensitive(not ok)

        if ok:
            self.sudo_ok    = True
            self._sudo_pass = raw_pass   # keep in memory for SUDO_ASKPASS

            # Write a tiny askpass helper script (chmod 700, deleted on exit)
            os.makedirs(os.path.dirname(self._askpass_path), exist_ok=True)
            with open(self._askpass_path, "w") as f:
                f.write(f"#!/bin/sh\necho '{raw_pass.replace(chr(39), '')}'\n")
            os.chmod(self._askpass_path, 0o700)

            self._sudo_bar_box.remove_css_class("sudo-bar")
            self._sudo_bar_box.add_css_class("sudo-bar-authed")
            self._sudo_status.remove_css_class("sudo-label-err")
            self._sudo_status.remove_css_class("sudo-label")
            self._sudo_status.add_css_class("sudo-label-ok")
            self._sudo_status.set_label("✔  Authenticated")
            self._sudo_refresh_lbl.set_label("⟳ auto-refresh: 5 min")
            self._sudo_refresh_lbl.set_visible(True)
            self._term_write("Root access granted.\n", "ok")
            self._term_write("$ ", "prompt")
        else:
            self.sudo_ok = False
            self._sudo_status.remove_css_class("sudo-label-ok")
            self._sudo_status.remove_css_class("sudo-label")
            self._sudo_status.add_css_class("sudo-label-err")
            self._sudo_status.set_label("✖  Wrong password — try again")
            self._sudo_entry.set_sensitive(True)
            self._sudo_entry.grab_focus()
            self._term_write("Authentication failed.\n", "err")
            self._term_write("$ ", "prompt")

    # ─── sudo auto-refresh every 5 min ───────────────────────────────────────
    def _auto_sudo_refresh(self):
        if self.sudo_ok:
            threading.Thread(target=self._silent_sudo_refresh, daemon=True).start()
        return True  # keep repeating

    def _silent_sudo_refresh(self):
        try:
            subprocess.run(["sudo", "-v"], capture_output=True, timeout=10)
        except Exception:
            pass

    # ─── yay check ────────────────────────────────────────────────────────────
    def _auto_check(self):
        self._check_yay()
        return False

    def _check_yay(self):
        self.yay_badge.set_label("Checking yay…")
        self.yay_badge.remove_css_class("badge-ok")
        self.yay_badge.remove_css_class("badge-fail")
        self.yay_badge.add_css_class("badge-checking")
        threading.Thread(target=self._check_yay_thread, daemon=True).start()

    def _check_yay_thread(self):
        found = shutil.which("yay") is not None
        GLib.idle_add(self._apply_yay_result, found)

    def _apply_yay_result(self, found):
        self.yay_ok = found
        self.yay_badge.remove_css_class("badge-checking")
        if found:
            self.yay_badge.set_label("  yay: ready")
            self.yay_badge.add_css_class("badge-ok")
            self._yay_banner.set_visible(False)
            self._term_write("yay found — checking installed packages…\n", "ok")
            self._check_installed_apps()
            # unlock install buttons
            for pkg, btn in self._app_btns.items():
                if btn.get_label() not in ("Installed", "Retry"):
                    btn.set_sensitive(True)
            if hasattr(self, "_apps_batch_btn"):
                self._apps_batch_btn.set_sensitive(True)
            if hasattr(self, "_gaming_batch_btn"):
                self._gaming_batch_btn.set_sensitive(True)
        else:
            self.yay_badge.set_label("  yay: missing")
            self.yay_badge.add_css_class("badge-fail")
            self._yay_banner.set_visible(True)
            self._term_write("yay not found — use the banner above to install it.\n", "err")
            for btn in self._app_btns.values():
                btn.set_sensitive(False)
        self._term_write("$ ", "prompt")

    # ─── Check which apps are already installed ───────────────────────────────
    def _check_installed_apps(self):
        threading.Thread(target=self._check_installed_thread, daemon=True).start()

    def _check_installed_thread(self):
        results = {}
        all_pkgs = [a["pkg"] for a in APPS + GAMING_APPS]
        for pkg in all_pkgs:
            r = subprocess.run(["pacman", "-Q", pkg], capture_output=True, text=True)
            results[pkg] = r.returncode == 0
        GLib.idle_add(self._apply_installed_results, results)

    def _apply_installed_results(self, results):
        for pkg, installed in results.items():
            btn = self._app_btns.get(pkg)
            if not btn: continue
            if installed:
                btn.set_label("Installed")
                for cls in ("btn-install", "btn-error", "btn-installing"):
                    btn.remove_css_class(cls)
                btn.add_css_class("btn-done")
                btn.set_sensitive(False)
        self._term_write("Package status check complete.\n", "dim")

    # ─── Install yay ──────────────────────────────────────────────────────────
    def _on_install_yay(self, btn):
        if self._running:
            self._term_write("[busy] wait for current task.\n", "err"); return
        btn.set_label("Installing…"); btn.set_sensitive(False)
        self._term_write("\n--- Installing yay ---\n", "info")
        for step in YAY_INSTALL_STEPS:
            self._term_write(f"  {step}\n", "dim")
        self._term_write("\n", "dim")
        self._run_yay_steps(list(YAY_INSTALL_STEPS), btn)

    def _run_yay_steps(self, steps, btn):
        if not steps:
            self._term_write("yay installation complete!\n", "ok")
            self._check_yay()
            return
        step = steps.pop(0)
        self._term_write(f"$ {step}\n", "cmd_echo")

        def done(ok):
            if ok:
                self._run_yay_steps(steps, btn)
            else:
                self._term_write("A step failed — check the output above.\n", "err")
                btn.set_label("Install yay"); btn.set_sensitive(True)

        self._run_in_terminal(step, on_done=done)

    # ─── Install single app ───────────────────────────────────────────────────
    def _on_install(self, app, btn):
        if not self.yay_ok:
            self._term_write("Install yay first!\n", "err"); return
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return

        btn.set_label("…")
        for cls in ("btn-install", "btn-error"):
            btn.remove_css_class(cls)
        btn.add_css_class("btn-installing"); btn.set_sensitive(False)

        cmd = f"yay -S {app['pkg']} --noconfirm --sudoflags '-A'"
        self._term_write(f"\n--- Installing {app['name']} ---\n", "info")
        self._term_write(f"$ yay -S {app['pkg']} --noconfirm\n", "cmd_echo")

        def done(ok):
            if ok:
                btn.set_label("Installed")
                btn.remove_css_class("btn-installing")
                btn.add_css_class("btn-done"); btn.set_sensitive(False)
            else:
                btn.set_label("Retry")
                btn.remove_css_class("btn-installing")
                btn.add_css_class("btn-error"); btn.set_sensitive(True)

        self._run_in_terminal(cmd, on_done=done)

    # ─── Batch install ────────────────────────────────────────────────────────
    def _batch_install(self, app_list):
        if not self.yay_ok:
            self._term_write("Install yay first!\n", "err"); return
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return

        # Only install apps that aren't already done
        pending = [
            a for a in app_list
            if self._app_btns.get(a["pkg"]) and
               self._app_btns[a["pkg"]].get_label() not in ("Installed",)
        ]
        if not pending:
            self._term_write("All apps already installed!\n", "ok"); return

        self._term_write(f"\n--- Batch install: {len(pending)} apps ---\n", "info")
        total = len(pending)

        # Show progress bar
        self._install_progress.set_visible(True)
        self._install_progress.set_fraction(0.0)
        self._install_progress.set_text(f"0 / {total}")

        def install_next(index):
            if index >= len(pending):
                self._term_write("✅ Batch install complete!\n", "ok")
                self._install_progress.set_fraction(1.0)
                self._install_progress.set_text("Done!")
                GLib.timeout_add_seconds(3, lambda: self._install_progress.set_visible(False))
                return

            app = pending[index]
            btn = self._app_btns.get(app["pkg"])
            if btn:
                btn.set_label("…")
                for cls in ("btn-install", "btn-error"):
                    btn.remove_css_class(cls)
                btn.add_css_class("btn-installing")
                btn.set_sensitive(False)

            cmd = f"yay -S {app['pkg']} --noconfirm --sudoflags '-A'"
            self._term_write(f"\n[{index+1}/{total}] Installing {app['name']}…\n", "info")
            self._term_write(f"$ yay -S {app['pkg']} --noconfirm\n", "cmd_echo")

            def done(ok):
                frac = (index + 1) / total
                self._install_progress.set_fraction(frac)
                self._install_progress.set_text(f"{index+1} / {total}")
                if btn:
                    if ok:
                        btn.set_label("Installed")
                        btn.remove_css_class("btn-installing")
                        btn.add_css_class("btn-done"); btn.set_sensitive(False)
                    else:
                        btn.set_label("Retry")
                        btn.remove_css_class("btn-installing")
                        btn.add_css_class("btn-error"); btn.set_sensitive(True)
                install_next(index + 1)

            self._run_in_terminal(cmd, on_done=done)

        install_next(0)

    # ─── Quick fix ────────────────────────────────────────────────────────────
    def _on_fix(self, fix, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        btn.set_label("…")
        btn.remove_css_class("btn-fix"); btn.add_css_class("btn-fix-running")
        btn.set_sensitive(False)
        cmd = " && ".join(fix["cmds"])
        self._term_write(f"\n--- {fix['name']} ---\n", "info")
        self._term_write(f"$ {cmd}\n", "cmd_echo")

        def done(ok):
            btn.set_label("Run")
            btn.remove_css_class("btn-fix-running")
            btn.add_css_class("btn-fix"); btn.set_sensitive(True)

        self._run_in_terminal(cmd, on_done=done)

    # ─── Advanced fix (step chain) ────────────────────────────────────────────
    def _on_advanced_fix(self, steps, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        btn.set_label("Running…"); btn.set_sensitive(False)
        self._switch_tab("main")   # switch to terminal view
        self._run_step_chain(list(steps), btn)

    def _run_step_chain(self, steps, btn):
        if not steps:
            self._term_write("--- Diagnostic complete ---\n", "ok")
            btn.set_label(btn.get_label().replace("Running…", "Run Again"))
            btn.set_sensitive(True)
            return
        step = steps.pop(0)
        self._term_write(f"$ {step}\n", "cmd_echo")

        def done(ok):
            self._run_step_chain(steps, btn)

        self._run_in_terminal(step, on_done=done)


# ─── Entry ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import atexit
    _askpass = os.path.expanduser("~/.cache/wit-askpass.sh")
    def _cleanup():
        try:
            if os.path.exists(_askpass):
                # Overwrite with zeros before deleting
                with open(_askpass, "w") as f:
                    f.write("#!/bin/sh\necho ''\n")
                os.remove(_askpass)
        except Exception:
            pass
    atexit.register(_cleanup)

    app = WITApp()
    app.run()
