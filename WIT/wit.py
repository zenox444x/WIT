#!/usr/bin/env python3
# ============================================================
#   WIT - CachyOS Toolkit
#   GTK4 + libadwaita - Python
#   v8.1.0 - Undo/Restore + Diagnostics + Task Manager + yay Gate
#           + Package History + Timeshift Backup
#   DEV: zenox / yolan
#   IG:  @z7.nv
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

# ─── GPU drivers ─────────────────────────────────────────────────────────────
DRIVERS = [
    {
        "name": "NVIDIA (proprietary)",
        "icon": "🟢",
        "vendor": "nvidia",
        "desc": "nvidia-dkms + nvidia-utils — best performance, needs reboot",
        "pkgs": ["nvidia-dkms", "nvidia-utils", "nvidia-settings"],
    },
    {
        "name": "AMD (open-source)",
        "icon": "🔴",
        "vendor": "amd",
        "desc": "mesa + vulkan-radeon — open-source AMD GPU stack",
        "pkgs": ["mesa", "vulkan-radeon", "lib32-vulkan-radeon"],
    },
    {
        "name": "Intel (open-source)",
        "icon": "🔵",
        "vendor": "intel",
        "desc": "mesa + vulkan-intel — open-source Intel GPU stack",
        "pkgs": ["mesa", "vulkan-intel", "lib32-vulkan-intel"],
    },
]

# ─── Useful tools for beginners ──────────────────────────────────────────────
TOOLS = [
    {"name": "Timeshift", "pkg": "timeshift", "icon": "🕒"},
    {"name": "GParted",   "pkg": "gparted",   "icon": "💿"},
    {"name": "HardInfo",  "pkg": "hardinfo2", "icon": "📊"},
    {"name": "Neofetch",  "pkg": "neofetch",  "icon": "🐧"},
    {"name": "Stacer",    "pkg": "stacer",    "icon": "🧹"},
    {"name": "Flatpak",   "pkg": "flatpak",   "icon": "📦"},
]

# ─── System services ──────────────────────────────────────────────────────────
SERVICES = [
    {"name": "NetworkManager", "unit": "NetworkManager",  "icon": "🌐", "desc": "Internet connectivity"},
    {"name": "Bluetooth",      "unit": "bluetooth",       "icon": "📶", "desc": "Bluetooth devices"},
    {"name": "CUPS",           "unit": "cups",            "icon": "🖨️", "desc": "Printer support"},
    {"name": "SSH Daemon",     "unit": "sshd",             "icon": "🔐", "desc": "Remote SSH access"},
    {"name": "Reflector",      "unit": "reflector",        "icon": "🪞", "desc": "Mirror list updater"},
]

# ─── Performance tools ───────────────────────────────────────────────────────
GAMEMODE_STEPS = [
    "sudo pacman -S --needed --noconfirm gamemode lib32-gamemode",
    "sudo usermod -aG gamemode $USER",
    "sudo systemctl --user enable --now gamemoded 2>/dev/null || true",
    "echo 'Gamemode installed. Log out/in for group changes to take effect.'",
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
    {
        "name": "Advanced Cleanup",
        "icon": "🧽",
        "desc": "Cache, orphans, journal logs & thumbnails",
        "cmds": [
            "sudo pacman -Sc --noconfirm",
            "sudo pacman -Rns --noconfirm $(pacman -Qdtq) 2>/dev/null || echo 'No orphan packages to remove'",
            "yay -Sc --noconfirm",
            "sudo journalctl --vacuum-size=100M",
            "rm -rf ~/.cache/thumbnails/* 2>/dev/null || true",
            "echo 'Advanced cleanup complete.'",
        ],
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

# ─── Windows Apps (Wine / Proton) ────────────────────────────────────────────
WINDOWS_APPS = [
    {
        "name": "Wine + Winetricks",
        "pkg":  "wine",
        "icon": "🍷",
        "extra_pkgs": ["wine-ge-custom", "winetricks"],
        "desc": "Run Windows apps & games",
    },
    {
        "name": "ProtonGE",
        "pkg":  "proton-ge-custom-bin",
        "icon": "⚗️",
        "extra_pkgs": [],
        "desc": "Enhanced Proton for Steam games",
    },
    {
        "name": "Bottles",
        "pkg":  "bottles",
        "icon": "🫙",
        "extra_pkgs": [],
        "desc": "GUI manager for Windows software",
    },
    {
        "name": "PlayOnLinux",
        "pkg":  "playonlinux",
        "icon": "🎰",
        "extra_pkgs": [],
        "desc": "Easy Wine front-end for games",
    },
]

# ─── Screen / NVIDIA fixes ────────────────────────────────────────────────────
SCREEN_FIXES = [
    {
        "name": "Enable NVIDIA DRM Modeset",
        "icon": "🟢",
        "desc": "Adds nvidia_drm.modeset=1 to GRUB — fixes black screen & Wayland",
        "cmds": [
            "sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT=\"/GRUB_CMDLINE_LINUX_DEFAULT=\"nvidia_drm.modeset=1 /' /etc/default/grub",
            "sudo grub-mkconfig -o /boot/grub/grub.cfg",
            "echo 'Done — reboot to apply.'",
        ],
    },
    {
        "name": "Fix Screen Tearing (picom)",
        "icon": "🖥️",
        "desc": "Install picom & apply vsync config for X11 tearing",
        "cmds": [
            "yay -S --needed --noconfirm picom --sudoflags '-A'",
            "mkdir -p ~/.config/picom",
            "echo 'backend = \"glx\"; vsync = true; glx-no-stencil = true;' > ~/.config/picom/picom.conf",
            "pkill picom 2>/dev/null; picom --daemon",
            "echo 'picom running with vsync — add to autostart for persistence.'",
        ],
    },
    {
        "name": "Set Max Refresh Rate",
        "icon": "⚡",
        "desc": "Detect connected displays and apply highest supported refresh rate",
        "cmds": [
            "xrandr --listmonitors",
            "for M in $(xrandr | grep ' connected' | awk '{print $1}'); do R=$(xrandr | grep -A1 \"^$M\" | tail -1 | awk '{print $1}'); xrandr --output \"$M\" --mode \"$R\" --rate $(xrandr | grep -A20 \"^$M\" | grep '*' | awk '{print $1}' | head -1 | grep -oP '[0-9]+\\.[0-9]+' | sort -n | tail -1) 2>/dev/null || true; done",
            "echo 'Refresh rate applied.'",
        ],
    },
    {
        "name": "NVIDIA Secure Boot Warning",
        "icon": "⚠️",
        "desc": "Check Secure Boot status — NVIDIA dkms needs it disabled",
        "cmds": [
            "mokutil --sb-state 2>/dev/null || echo 'mokutil not found'",
            "echo 'If Secure Boot is ENABLED, NVIDIA dkms modules will NOT load.'",
            "echo 'Disable Secure Boot in UEFI/BIOS settings before installing NVIDIA drivers.'",
        ],
    },
]

# ─── Common Issues (one-click fixes) ─────────────────────────────────────────
COMMON_FIXES = [
    {
        "name": "Fix: No Sound",
        "icon": "🔊",
        "desc": "Restart PipeWire/PulseAudio & install missing audio packages",
        "cmds": [
            "sudo pacman -S --needed --noconfirm pipewire pipewire-pulse pipewire-alsa wireplumber --sudoflags '-A' 2>/dev/null || true",
            "systemctl --user restart pipewire pipewire-pulse wireplumber 2>/dev/null || pulseaudio --kill && pulseaudio --start",
            "echo 'Audio restarted.'",
        ],
    },
    {
        "name": "Fix: Boot Issues",
        "icon": "🔁",
        "desc": "Rebuild initramfs with mkinitcpio -P",
        "cmds": [
            "sudo mkinitcpio -P",
            "echo 'initramfs rebuilt — reboot to apply.'",
        ],
    },
    {
        "name": "Fix: Wrong Clock/Time",
        "icon": "🕒",
        "desc": "Enable NTP time sync via systemd-timesyncd",
        "cmds": [
            "sudo timedatectl set-ntp true",
            "sudo systemctl enable --now systemd-timesyncd",
            "timedatectl status",
        ],
    },
    {
        "name": "Fix: Printer Not Working",
        "icon": "🖨️",
        "desc": "Install CUPS & enable printer service",
        "cmds": [
            "sudo pacman -S --needed --noconfirm cups cups-filters --sudoflags '-A' 2>/dev/null || true",
            "sudo systemctl enable --now cups",
            "echo 'CUPS running — visit http://localhost:631 to add your printer.'",
        ],
    },
]

# ─── Power management ─────────────────────────────────────────────────────────
POWER_FIXES = [
    {
        "name": "Install TLP (Battery)",
        "icon": "🔋",
        "desc": "Laptop battery optimizer — auto-tunes power settings",
        "cmds": [
            "sudo pacman -S --needed --noconfirm tlp tlp-rdw --sudoflags '-A' 2>/dev/null || true",
            "sudo systemctl enable --now tlp",
            "sudo systemctl enable --now NetworkManager-dispatcher",
            "echo 'TLP running.'",
        ],
    },
    {
        "name": "Install auto-cpufreq",
        "icon": "⚡",
        "desc": "Automatic CPU frequency & power optimizer",
        "cmds": [
            "yay -S --needed --noconfirm auto-cpufreq --sudoflags '-A'",
            "sudo auto-cpufreq --install",
            "echo 'auto-cpufreq installed and active.'",
        ],
    },
]

# ─── Package backup/restore ───────────────────────────────────────────────────
PKG_BACKUP_DEST  = os.path.expanduser("~/Desktop/packages.txt")
AUR_BACKUP_DEST  = os.path.expanduser("~/Desktop/aur-packages.txt")

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
.btn-reinstall   { background: #1c1c3a; color: #818cf8; border-radius: 9px; font-weight: 800; font-size: 13px; padding: 6px 10px; min-width: 30px; border: 1px solid #2a2a60; }
.btn-reinstall:hover    { background: #2a2a55; color: #a5b4fc; }
.btn-reinstall:disabled { background: #16162c; color: #313660; }
.btn-uninstall   { background: #1c0a10; color: #f06a7a; border-radius: 9px; font-weight: 800; font-size: 13px; padding: 6px 10px; min-width: 30px; border: 1px solid #4a1018; }
.btn-uninstall:hover    { background: #3a1018; color: #ff8a96; }
.btn-uninstall:disabled { background: #16162c; color: #313660; }
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

/* ── About button ── */
.about-btn {
  background: alpha(#606888, 0.15); color: #606888;
  border-radius: 50%; border: 1px solid alpha(#606888, 0.3);
  font-size: 13px; font-weight: 700;
  min-width: 28px; min-height: 28px;
  padding: 0;
  transition: background 150ms, color 150ms;
}
.about-btn:hover { background: alpha(#818cf8, 0.25); color: #818cf8; border-color: alpha(#818cf8,0.5); }

/* ── Uninstall dialog button ── */
.uninstall-red-btn {
  background: #3a0d12; color: #f06a7a;
  border-radius: 10px; font-weight: 800; font-size: 12px;
  padding: 8px 22px; border: 1px solid #7a1c28;
  letter-spacing: 1px;
  transition: background 150ms;
}
.uninstall-red-btn:hover { background: #5a1018; }

/* Misc */
.dim-sep { background: #1c1c3a; min-height: 1px; }

/* ── Undo bar ── */
.undo-bar {
  background: #0f1a10; border-bottom: 1px solid #1a3a1a;
  padding: 6px 22px;
}
.undo-label { font-size: 11px; font-weight: 700; color: #a3e6b0; letter-spacing: 1px; }
.undo-btn {
  background: #1a3a1a; color: #30c984;
  border-radius: 8px; font-weight: 800; font-size: 11px;
  padding: 5px 14px; border: 1px solid #2a5a2a;
  transition: background 150ms;
}
.undo-btn:hover { background: #1e4e1e; }

/* ── Task manager bar ── */
.task-bar {
  background: #0f0f20; border-top: 1px solid #1c1c3a;
  padding: 5px 22px;
}
.task-label { font-size: 11px; font-weight: 700; color: #818cf8; letter-spacing: 1px; }
.task-cancel-btn {
  background: #280d14; color: #f06a7a;
  border-radius: 8px; font-weight: 700; font-size: 11px;
  padding: 4px 12px; border: 1px solid #7a1c28;
}
.task-cancel-btn:hover { background: #3a1018; }

/* ── History page ── */
.history-card {
  background: #121228; border-radius: 12px;
  border: 1px solid #1c1c3a; padding: 4px;
  animation: slide-in-up 280ms ease both;
}
.history-action-install  { color: #30c984; font-size: 11px; font-weight: 700; }
.history-action-remove   { color: #f06a7a; font-size: 11px; font-weight: 700; }
.history-action-fix      { color: #818cf8; font-size: 11px; font-weight: 700; }
.history-action-system   { color: #f0b040; font-size: 11px; font-weight: 700; }
.history-pkg  { font-size: 12px; font-weight: 700; color: #dde3f0; }
.history-time { font-size: 10px; color: #313660; font-family: monospace; }
.history-clear-btn {
  background: alpha(#f06a7a, 0.10); color: #f06a7a;
  border-radius: 8px; font-weight: 700; font-size: 11px;
  padding: 5px 12px; border: 1px solid alpha(#f06a7a, 0.3);
}
.history-clear-btn:hover { background: alpha(#f06a7a, 0.22); }

/* ── Diagnostics page ── */
.diag-card {
  background: #121228; border-radius: 12px;
  border: 1px solid #1c1c3a; padding: 10px 16px;
  animation: slide-in-up 280ms ease both;
}
.diag-section-title { font-size: 13px; font-weight: 700; color: #818cf8; }
.diag-key   { font-size: 11px; color: #606888; font-family: monospace; }
.diag-value { font-size: 11px; color: #dde3f0; font-family: monospace; font-weight: 600; }
.diag-export-btn {
  background: #1a1840; color: #818cf8;
  border-radius: 9px; font-weight: 800; font-size: 12px;
  padding: 7px 18px; border: 1px solid #2a2a6a; letter-spacing: 1px;
}
.diag-export-btn:hover { background: #22205a; }
.diag-run-btn {
  background: #e94560; color: white;
  border-radius: 9px; font-weight: 800; font-size: 12px;
  padding: 7px 18px; letter-spacing: 1px; transition: background 150ms;
}
.diag-run-btn:hover { background: #c72e48; }

/* ── Backup badge ── */
.backup-badge {
  background: #12100a; color: #f0b040;
  border-radius: 20px; padding: 4px 14px;
  font-size: 10px; font-weight: 700;
  border: 1px solid #3a2a08;
}
.svc-status-active   { background: #0a2818; color: #30c984; border-radius: 20px; padding: 4px 12px; font-size: 10px; font-weight: 700; border: 1px solid #054a30; }
.svc-status-inactive { background: #1c1c38; color: #606888; border-radius: 20px; padding: 4px 12px; font-size: 10px; font-weight: 700; border: 1px solid #28285a; }
.svc-status-unknown  { background: #280d14; color: #f06a7a; border-radius: 20px; padding: 4px 12px; font-size: 10px; font-weight: 700; border: 1px solid #7a1c28; }
.btn-svc-start { background: #0a2818; color: #30c984; border-radius: 9px; font-weight: 700; font-size: 11px; padding: 6px 12px; border: 1px solid #054a30; min-width: 56px; }
.btn-svc-start:hover { background: #0e3a22; }
.btn-svc-stop  { background: #280d14; color: #f06a7a; border-radius: 9px; font-weight: 700; font-size: 11px; padding: 6px 12px; border: 1px solid #7a1c28; min-width: 56px; }
.btn-svc-stop:hover { background: #3a1018; }
.btn-svc:disabled { background: #14142e; color: #313660; border-color: #1c1c3a; }

/* ── New sections (v8) ── */
.win-app-card { background: #121228; border-radius: 14px; border: 1px solid #2a1c3a; padding: 4px; animation: slide-in-up 320ms ease both; }
.win-app-card:hover { border-color: alpha(#c084fc, 0.45); }
.btn-win     { background: #1a0e28; color: #c084fc; border-radius: 9px; font-weight: 800; font-size: 11px; letter-spacing: 1px; padding: 6px 14px; min-width: 78px; border: 1px solid #3a1c60; }
.btn-win:hover    { background: #26124a; }
.btn-win:disabled { background: #1c1c3a; color: #313660; border-color: #1c1c3a; }
.screen-fix-card { background: #121228; border-radius: 14px; border: 1px solid #1c2a3a; padding: 6px; animation: slide-in-up 320ms ease both; }
.screen-fix-card:hover { border-color: alpha(#38bdf8, 0.45); }
.btn-screen  { background: #0a1e28; color: #38bdf8; border-radius: 9px; font-weight: 700; font-size: 11px; padding: 6px 14px; border: 1px solid #1c4060; letter-spacing: 1px; min-width: 70px; }
.btn-screen:hover   { background: #0e2a38; }
.btn-screen:disabled { background: #14142e; color: #313660; border-color: #1c1c3a; }
.pkg-backup-card { background: #121228; border-radius: 14px; border: 1px solid #1a2818; padding: 12px 16px; }
.notify-bar { background: #0a1e10; border-bottom: 1px solid #1a4020; padding: 7px 22px; }
.notify-label { font-size: 11px; font-weight: 700; color: #60d090; letter-spacing: 1px; }

/* ── sudo warning bar ── */
.sudo-warning-bar {
  background: #1a0e28;
  border-bottom: 1px solid alpha(#c084fc, 0.3);
  padding: 7px 22px;
}
.sudo-warning-label { font-size: 11px; font-weight: 700; color: #c084fc; letter-spacing: 0.5px; }

/* ── yay-required overlay ── */
.yay-overlay {
  background: alpha(#0b0b18, 0.96);
}
.yay-overlay-box {
  background: #121228;
  border-radius: 20px;
  border: 2px solid alpha(#f0b040, 0.5);
  padding: 40px 48px;
}
.yay-overlay-icon  { font-size: 64px; }
.yay-overlay-title {
  font-size: 22px; font-weight: 900; color: #f0b040;
  letter-spacing: 2px; margin-top: 12px;
}
.yay-overlay-body  { font-size: 13px; color: #808898; margin-top: 8px; }
.yay-overlay-arrow { font-size: 13px; font-weight: 700; color: #e94560; margin-top: 16px; letter-spacing: 1px; }
.yay-overlay-btn {
  background: #f0b040; color: #0b0b18;
  border-radius: 12px; font-weight: 900; font-size: 13px;
  padding: 10px 28px; letter-spacing: 1px; margin-top: 20px;
  border: none;
}
.yay-overlay-btn:hover { background: #d49030; }
"""
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
        self._sudo_pass   = ""
        self._askpass_path = os.path.expanduser("~/.cache/wit-askpass.sh")
        self._app_btns: dict[str, Gtk.Button] = {}
        self._app_reinstall_btns: dict[str, Gtk.Button] = {}
        self._app_uninstall_btns: dict[str, Gtk.Button] = {}
        self._driver_btns: dict[str, Gtk.Button] = {}
        self._win_btns: dict[str, Gtk.Button] = {}
        self._service_widgets: dict[str, dict] = {}
        self._sudo_refresh_id = None
        # ── New v8.1 state ──────────────────────────────────────────────────
        self._history: list[dict] = []        # package history log
        self._undo_stack: list[dict] = []     # undo/restore operations
        self._active_proc = None              # current running subprocess
        self._task_cancelled = False          # cancel flag for background tasks

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
        # sudo warning — shown when yay is missing AND sudo not authenticated
        self._sudo_warning_bar = self._build_sudo_warning()
        root.append(self._sudo_warning_bar)
        self._yay_banner = self._build_yay_banner()
        root.append(self._yay_banner)

        # Undo bar (hidden until an undoable action runs)
        self._undo_bar = self._build_undo_bar()
        root.append(self._undo_bar)

        # Tab row
        self._tab_row_widget = self._build_tab_row()
        root.append(self._tab_row_widget)

        # Stack wrapped in Gtk.Overlay so the blocker only covers content,
        # leaving the header + sudo bar always accessible above.
        self._stack = Gtk.Stack()
        self._stack.set_vexpand(True)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(160)

        self._stack_overlay = Gtk.Overlay()
        self._stack_overlay.set_vexpand(True)
        self._stack_overlay.set_child(self._stack)

        # yay overlay — floats over stack only; sudo bar stays accessible above
        self._yay_overlay_widget = self._build_yay_overlay()
        self._yay_overlay_widget.set_visible(False)   # hidden until check
        self._stack_overlay.add_overlay(self._yay_overlay_widget)

        root.append(self._stack_overlay)

        # Page 1: Apps + Fixes (split)
        self._stack.add_named(self._build_main_page(), "main")
        # Page 2: Gaming
        self._stack.add_named(self._build_gaming_page(), "gaming")
        # Page 3: Windows Apps
        self._stack.add_named(self._build_windows_page(), "windows")
        # Page 4: Screen / NVIDIA
        self._stack.add_named(self._build_screen_page(), "screen")
        # Page 5: Common Issues
        self._stack.add_named(self._build_issues_page(), "issues")
        # Page 6: System (Drivers + Performance)
        self._stack.add_named(self._build_system_page(), "system")
        # Page 7: Advanced fixes
        self._stack.add_named(self._build_advanced_page(), "advanced")
        # Page 8: Power management
        self._stack.add_named(self._build_power_page(), "power")
        # Page 9: Package backup/restore
        self._stack.add_named(self._build_packages_page(), "packages")
        # Page 10: History
        self._stack.add_named(self._build_history_page(), "history")
        # Page 11: Diagnostics
        self._stack.add_named(self._build_diagnostics_page(), "diagnostics")

        # Task manager bar (bottom, always visible when task runs)
        self._task_bar = self._build_task_bar()
        root.append(self._task_bar)

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
            "Welcome to WIT v8.1.0",
            "The CachyOS toolkit for apps, gaming, and system fixes.\n\n"
            "Get started:\n"
            "  1. Authenticate sudo in the bar at the top\n"
            "  2. Install yay if the banner appears\n"
            "  3. Pick apps or run a fix — the terminal shows everything live\n"
            "  4. Check History tab to review past operations\n"
            "  5. Use Diagnostics to generate a full system report",
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
        tl = Gtk.Label(label="CACHY OS TOOLKIT")
        tl.add_css_class("wit-tagline"); tl.set_halign(Gtk.Align.START)
        ver = Gtk.Label(label="v8.1.0")
        ver.add_css_class("wit-version"); ver.set_halign(Gtk.Align.START)
        dev = Gtk.Label(label="DEV: zenox / yolan")
        dev.add_css_class("wit-version"); dev.set_halign(Gtk.Align.START)
        ig = Gtk.Label(label="IG: @z7.nv")
        ig.add_css_class("wit-version"); ig.set_halign(Gtk.Align.START)
        left.append(wm); left.append(tl); left.append(ver); left.append(dev); left.append(ig)
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

        # ── About button (bottom-right of header) ──
        about_btn = Gtk.Button(label="ℹ")
        about_btn.add_css_class("about-btn")
        about_btn.set_tooltip_text("About & Uninstall")
        about_btn.connect("clicked", self._show_about_dialog)
        about_btn.set_valign(Gtk.Align.END)
        about_btn.set_halign(Gtk.Align.END)
        right.append(about_btn)

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


    # ─── sudo warning bar (shown when yay missing + not authenticated) ────────
    def _build_sudo_warning(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.add_css_class("sudo-warning-bar")
        bar.set_visible(False)

        icon = Gtk.Label(label="🔐")
        lbl = Gtk.Label(
            label="Sudo authentication required to install yay — "
                  "enter your password in the bar above first.")
        lbl.add_css_class("sudo-warning-label")
        lbl.set_hexpand(True)
        lbl.set_halign(Gtk.Align.START)

        bar.append(icon)
        bar.append(lbl)
        return bar

    def _show_sudo_warning(self, visible: bool):
        if hasattr(self, "_sudo_warning_bar"):
            self._sudo_warning_bar.set_visible(visible and not self.sudo_ok)

    # ─── yay-required overlay (blocks all UI until yay installed) ────────────
    def _build_yay_overlay(self):
        """Full-screen overlay that blocks all interaction until yay is ready."""
        overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.add_css_class("yay-overlay")
        overlay.set_hexpand(True)
        overlay.set_vexpand(True)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)
        center.set_hexpand(True)
        center.set_vexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.add_css_class("yay-overlay-box")
        box.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Label(label="⚠️")
        icon.add_css_class("yay-overlay-icon")
        icon.set_halign(Gtk.Align.CENTER)

        title = Gtk.Label(label="yay is required")
        title.add_css_class("yay-overlay-title")
        title.set_halign(Gtk.Align.CENTER)

        body = Gtk.Label(
            label="yay (AUR helper) must be installed\n"
                  "before you can use any feature in WIT.\n\n"
                  "1. Enter your sudo password above\n"
                  "2. Click \"Install yay\" in the top-right corner"
        )
        body.add_css_class("yay-overlay-body")
        body.set_halign(Gtk.Align.CENTER)
        body.set_justify(Gtk.Justification.CENTER)

        arrow = Gtk.Label(label="↑  Click  \"Install yay\"  in the top-right corner  ↑")
        arrow.add_css_class("yay-overlay-arrow")
        arrow.set_halign(Gtk.Align.CENTER)

        install_btn = Gtk.Button(label="Install yay now")
        install_btn.add_css_class("yay-overlay-btn")
        install_btn.set_halign(Gtk.Align.CENTER)
        install_btn.connect("clicked", self._on_install_yay)

        box.append(icon)
        box.append(title)
        box.append(body)
        box.append(arrow)
        box.append(install_btn)
        center.append(box)
        overlay.append(center)
        return overlay

    def _lock_ui(self):
        """Block all content — overlay covers only the stack, sudo bar stays usable."""
        self._ui_locked = True
        self._tab_row_widget.set_sensitive(False)
        self._yay_overlay_widget.set_visible(True)
        # Also show sudo warning if not yet authenticated
        if not self.sudo_ok:
            self._show_sudo_warning(True)

    def _unlock_ui(self):
        """Hide overlay and reveal the full UI."""
        self._ui_locked = False
        self._yay_overlay_widget.set_visible(False)
        self._tab_row_widget.set_sensitive(True)
        self._show_sudo_warning(False)


    # ─── Tab row ──────────────────────────────────────────────────────────────
    def _build_tab_row(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        row.add_css_class("tab-row")
        self._tab_btns = {}
        tabs = [
            ("main",        "📦  Apps & Fixes"),
            ("gaming",      "🎮  Gaming"),
            ("windows",     "🪟  Windows Apps"),
            ("screen",      "🖥️  Screen"),
            ("issues",      "🔧  Common Issues"),
            ("system",      "⚙️  System"),
            ("advanced",    "🩹  Advanced Fixes"),
            ("power",       "🔋  Power"),
            ("packages",    "💾  Packages"),
            ("history",     "📋  History"),
            ("diagnostics", "🩺  Diagnostics"),
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

    # ─── Windows Apps page ────────────────────────────────────────────────────
    def _build_windows_page(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(620); paned.set_wide_handle(True)
        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_hexpand(True)
        left_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        left_body.set_margin_top(20); left_body.set_margin_bottom(24)
        left_body.set_margin_start(22); left_body.set_margin_end(16)
        left_scroll.set_child(left_body)
        left_body.append(self._build_windows_section())
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

    def _build_windows_section(self):
        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("COMPATIBILITY", "Windows Apps (Wine / Proton)"))
        notice = Gtk.Label(label="⚠  Wine/Proton run Windows software — performance may vary. AUR required.")
        notice.add_css_class("fix-desc"); notice.set_halign(Gtk.Align.START)
        notice.set_margin_bottom(4)
        sec.append(notice)
        self._win_btns: dict[str, Gtk.Button] = {}
        for app in WINDOWS_APPS:
            sec.append(self._make_windows_card(app))
        return sec

    def _make_windows_card(self, app):
        outer = Gtk.Box(); outer.set_hexpand(True)
        outer.set_margin_top(1); outer.set_margin_bottom(1)
        outer.set_margin_start(1); outer.set_margin_end(1)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("win-app-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label=app["icon"])
        icon_lbl.add_css_class("app-icon-label")
        icon_lbl.set_margin_start(10); icon_lbl.set_margin_top(8); icon_lbl.set_margin_bottom(8)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)
        name_lbl = Gtk.Label(label=app["name"])
        name_lbl.add_css_class("app-name"); name_lbl.set_halign(Gtk.Align.START)
        pkgs = " + ".join([app["pkg"]] + app.get("extra_pkgs", []))
        desc_lbl = Gtk.Label(label=f"{app['desc']}  [{pkgs}]")
        desc_lbl.add_css_class("app-pkg"); desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_wrap(True)
        info.append(name_lbl); info.append(desc_lbl)

        btn = Gtk.Button(label="Install")
        btn.add_css_class("btn-win"); btn.set_sensitive(False)
        btn.set_valign(Gtk.Align.CENTER); btn.set_margin_end(10)
        btn.connect("clicked", lambda _, a=app, b=btn: self._on_install_win(a, b))
        self._win_btns[app["pkg"]] = btn

        card.append(icon_lbl); card.append(info); card.append(btn)
        outer.append(card)
        # Unlock if yay is ready
        GLib.idle_add(lambda b=btn: b.set_sensitive(self.yay_ok) or False)
        return outer

    def _on_install_win(self, app, btn):
        if not self.yay_ok:
            self._term_write("Install yay first!\n", "err"); return
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        all_pkgs = [app["pkg"]] + app.get("extra_pkgs", [])
        pkgs_str = " ".join(all_pkgs)
        btn.set_label("…"); btn.add_css_class("btn-installing"); btn.set_sensitive(False)
        cmd = f"yay -S --needed --noconfirm {pkgs_str} --sudoflags '-A'"
        self._term_write(f"\n--- Installing {app['name']} ---\n", "info")
        self._term_write(f"$ {cmd}\n", "cmd_echo")
        self._show_task(f"Installing {app['name']}")

        def done(ok):
            btn.remove_css_class("btn-installing")
            if ok:
                btn.set_label("Installed"); btn.add_css_class("btn-done"); btn.set_sensitive(False)
                self._log_history("install", app["name"], pkgs_str)
            else:
                btn.set_label("Retry"); btn.add_css_class("btn-win"); btn.set_sensitive(True)
        self._run_in_terminal(cmd, on_done=done)

    # ─── Screen / NVIDIA page ─────────────────────────────────────────────────
    def _build_screen_page(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(620); paned.set_wide_handle(True)
        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_hexpand(True)
        left_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        left_body.set_margin_top(20); left_body.set_margin_bottom(24)
        left_body.set_margin_start(22); left_body.set_margin_end(16)
        left_scroll.set_child(left_body)
        left_body.append(self._build_screen_section())
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

    def _build_screen_section(self):
        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("DISPLAY", "Screen & NVIDIA Issues"))
        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(1); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        for fix in SCREEN_FIXES:
            grid.append(self._make_screen_fix_card(fix))
        sec.append(grid)
        return sec

    def _make_screen_fix_card(self, fix):
        outer = Gtk.Box(); outer.set_hexpand(True)
        outer.set_margin_top(1); outer.set_margin_bottom(1)
        outer.set_margin_start(1); outer.set_margin_end(1)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("screen-fix-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label=fix["icon"])
        icon_lbl.add_css_class("fix-icon")
        icon_lbl.set_margin_start(12); icon_lbl.set_margin_top(12); icon_lbl.set_margin_bottom(12)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        name_lbl = Gtk.Label(label=fix["name"])
        name_lbl.add_css_class("fix-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label=fix["desc"])
        desc_lbl.add_css_class("fix-desc"); desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_wrap(True)
        text.append(name_lbl); text.append(desc_lbl)

        btn = Gtk.Button(label="Run")
        btn.add_css_class("btn-screen"); btn.set_valign(Gtk.Align.CENTER)
        btn.set_margin_end(12)
        btn.connect("clicked", lambda _, f=fix, b=btn: self._on_screen_fix(f, b))
        card.append(icon_lbl); card.append(text); card.append(btn)
        outer.append(card)
        return outer

    def _on_screen_fix(self, fix, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        btn.set_label("…"); btn.set_sensitive(False)
        cmd = " && ".join(fix["cmds"])
        self._term_write(f"\n--- {fix['name']} ---\n", "info")
        self._term_write(f"$ {cmd}\n", "cmd_echo")
        self._show_task(fix["name"])
        self._switch_tab("main")

        def done(ok):
            btn.set_label("Run"); btn.set_sensitive(True)
            if ok:
                self._log_history("fix", fix["name"])
        self._run_in_terminal(cmd, on_done=done)

    # ─── Common Issues page ───────────────────────────────────────────────────
    def _build_issues_page(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(620); paned.set_wide_handle(True)
        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_hexpand(True)
        left_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        left_body.set_margin_top(20); left_body.set_margin_bottom(24)
        left_body.set_margin_start(22); left_body.set_margin_end(16)
        left_scroll.set_child(left_body)
        left_body.append(self._build_issues_section())
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

    def _build_issues_section(self):
        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("ONE-CLICK", "Common Issues"))
        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(2); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        for fix in COMMON_FIXES:
            grid.append(self._make_fix_card(fix))
        sec.append(grid)
        return sec

    # ─── Power Management page ────────────────────────────────────────────────
    def _build_power_page(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(620); paned.set_wide_handle(True)
        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_hexpand(True)
        left_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        left_body.set_margin_top(20); left_body.set_margin_bottom(24)
        left_body.set_margin_start(22); left_body.set_margin_end(16)
        left_scroll.set_child(left_body)
        left_body.append(self._build_power_section())
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

    def _build_power_section(self):
        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("LAPTOP", "Power Management"))
        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(2); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        for fix in POWER_FIXES:
            grid.append(self._make_fix_card(fix))
        sec.append(grid)

        sec.append(self._make_sep())
        sec.append(self._build_sleep_section())
        return sec

    def _build_sleep_section(self):
        sub = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sub.append(self._section_header("IDLE", "Sleep / Screen Timeout"))

        # Sleep timeout row
        sleep_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sleep_row.add_css_class("fix-card"); sleep_row.set_hexpand(True)
        sleep_row.set_margin_top(2); sleep_row.set_margin_bottom(2)

        icon = Gtk.Label(label="😴"); icon.add_css_class("fix-icon")
        icon.set_margin_start(12); icon.set_margin_top(12); icon.set_margin_bottom(12)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); info.set_hexpand(True)
        Gtk.Label(label="Sleep Timeout")  # placeholder
        name_lbl = Gtk.Label(label="Sleep Timeout")
        name_lbl.add_css_class("fix-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label="Minutes until system sleeps (0 = never)")
        desc_lbl.add_css_class("fix-desc"); desc_lbl.set_halign(Gtk.Align.START)
        info.append(name_lbl); info.append(desc_lbl)

        self._sleep_spin = Gtk.SpinButton.new_with_range(0, 120, 5)
        self._sleep_spin.set_value(20); self._sleep_spin.set_valign(Gtk.Align.CENTER)
        self._sleep_spin.set_margin_end(8)

        sleep_btn = Gtk.Button(label="Apply")
        sleep_btn.add_css_class("btn-fix"); sleep_btn.set_valign(Gtk.Align.CENTER)
        sleep_btn.set_margin_end(12)
        sleep_btn.connect("clicked", self._on_apply_sleep)

        sleep_row.append(icon); sleep_row.append(info)
        sleep_row.append(self._sleep_spin); sleep_row.append(sleep_btn)
        sub.append(sleep_row)
        return sub

    def _on_apply_sleep(self, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        val = int(self._sleep_spin.get_value())
        secs = val * 60 if val > 0 else 0
        btn.set_label("…"); btn.set_sensitive(False)
        cmd = f"gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout {secs} 2>/dev/null || xset s {secs} 2>/dev/null || echo 'Applied: sleep timeout {val} min'"
        self._term_write(f"\n--- Setting sleep timeout to {val} min ---\n", "info")
        self._term_write(f"$ {cmd}\n", "cmd_echo")

        def done(ok):
            btn.set_label("Apply"); btn.set_sensitive(True)
        self._run_in_terminal(cmd, on_done=done)

    # ─── Package Backup / Restore page ───────────────────────────────────────
    def _build_packages_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_vexpand(True)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar.set_margin_top(18); toolbar.set_margin_bottom(10)
        toolbar.set_margin_start(22); toolbar.set_margin_end(22)
        title = Gtk.Label(label="Package Backup & Restore")
        title.add_css_class("section-title"); title.set_hexpand(True)
        title.set_halign(Gtk.Align.START)
        toolbar.append(title)
        outer.append(toolbar)

        sep = Gtk.Separator(); sep.add_css_class("dim-sep"); outer.append(sep)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        body.set_margin_top(20); body.set_margin_bottom(24)
        body.set_margin_start(22); body.set_margin_end(22)
        scroll.set_child(body)

        # ── Pacman backup ──
        body.append(self._section_header("OFFICIAL", "Pacman Package List"))
        body.append(self._make_pkg_card(
            icon="💾", title="Save Pacman List",
            desc=f"Saves explicitly installed packages → {PKG_BACKUP_DEST}",
            btn_label="Save",
            cmd=f"pacman -Qqe > {PKG_BACKUP_DEST} && echo 'Saved to {PKG_BACKUP_DEST}'",
            copy_path=PKG_BACKUP_DEST,
        ))
        body.append(self._make_pkg_card(
            icon="📥", title="Restore Pacman List",
            desc=f"Installs packages from {PKG_BACKUP_DEST}",
            btn_label="Restore",
            cmd=f"sudo pacman -S --needed --noconfirm $(cat {PKG_BACKUP_DEST}) 2>/dev/null || echo 'File not found or no packages to install'",
        ))

        body.append(self._make_sep())

        # ── AUR backup ──
        body.append(self._section_header("AUR", "AUR Package List"))
        body.append(self._make_pkg_card(
            icon="💾", title="Save AUR List",
            desc=f"Saves AUR-installed packages → {AUR_BACKUP_DEST}",
            btn_label="Save",
            cmd=f"yay -Qqe > {AUR_BACKUP_DEST} && echo 'Saved to {AUR_BACKUP_DEST}'",
            copy_path=AUR_BACKUP_DEST,
        ))
        body.append(self._make_pkg_card(
            icon="📥", title="Restore AUR List",
            desc=f"Re-installs AUR packages from {AUR_BACKUP_DEST}",
            btn_label="Restore",
            cmd=f"yay -S --needed --noconfirm $(cat {AUR_BACKUP_DEST}) --sudoflags '-A' 2>/dev/null || echo 'File not found'",
        ))

        outer.append(scroll)
        return outer

    def _make_pkg_card(self, icon, title, desc, btn_label, cmd, copy_path=None):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.add_css_class("pkg-backup-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label=icon); icon_lbl.add_css_class("fix-icon")
        icon_lbl.set_margin_start(4); icon_lbl.set_margin_top(4); icon_lbl.set_margin_bottom(4)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); info.set_hexpand(True)
        name_lbl = Gtk.Label(label=title); name_lbl.add_css_class("fix-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label=desc); desc_lbl.add_css_class("fix-desc"); desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_wrap(True)
        info.append(name_lbl); info.append(desc_lbl)

        btn = Gtk.Button(label=btn_label); btn.add_css_class("btn-fix")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _, c=cmd, b=btn: self._on_pkg_action(c, b))

        card.append(icon_lbl); card.append(info); card.append(btn)

        if copy_path:
            copy_btn = Gtk.Button(label="📋 Copy")
            copy_btn.add_css_class("batch-btn"); copy_btn.set_valign(Gtk.Align.CENTER)
            copy_btn.set_margin_end(4)
            copy_btn.connect("clicked", lambda _, p=copy_path: self._copy_file_to_clipboard(p))
            card.append(copy_btn)

        return card

    def _on_pkg_action(self, cmd, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        btn.set_label("…"); btn.set_sensitive(False)
        self._term_write(f"\n$ {cmd}\n", "cmd_echo")
        self._switch_tab("main")
        def done(ok):
            btn.set_label(btn.get_label() if btn.get_label() != "…" else "Run")
            btn.set_label("Done ✓" if ok else "Retry")
            btn.set_sensitive(True)
        self._run_in_terminal(cmd, on_done=done)

    def _copy_file_to_clipboard(self, path):
        try:
            with open(path) as f:
                content = f.read()
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(content)
            self._term_write(f"Copied {path} to clipboard.\n", "ok")
        except Exception as exc:
            self._term_write(f"Could not copy: {exc}\n", "err")

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

    # ─── System page (Drivers + Performance) ─────────────────────────────────
    def _build_system_page(self):
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
        left_body.append(self._build_drivers_section())
        left_body.append(self._make_sep())
        left_body.append(self._build_performance_section())
        left_body.append(self._make_sep())
        left_body.append(self._build_tools_section())
        left_body.append(self._make_sep())
        left_body.append(self._build_services_section())
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
        btn.set_valign(Gtk.Align.CENTER); btn.set_margin_end(4)
        btn.connect("clicked", lambda _, a=app, b=btn: self._on_install_with_history(a, b))
        self._app_btns[app["pkg"]] = btn

        reinstall_btn = Gtk.Button(label="↻")
        reinstall_btn.add_css_class("btn-reinstall")
        reinstall_btn.set_valign(Gtk.Align.CENTER); reinstall_btn.set_margin_end(4)
        reinstall_btn.set_tooltip_text("Reinstall")
        reinstall_btn.set_visible(False)
        reinstall_btn.connect("clicked", lambda _, a=app, b=btn: self._on_install_with_history(a, b, reinstall=True))
        self._app_reinstall_btns[app["pkg"]] = reinstall_btn

        uninstall_btn = Gtk.Button(label="🗑")
        uninstall_btn.add_css_class("btn-uninstall")
        uninstall_btn.set_valign(Gtk.Align.CENTER); uninstall_btn.set_margin_end(10)
        uninstall_btn.set_tooltip_text("Uninstall")
        uninstall_btn.set_visible(False)
        uninstall_btn.connect("clicked", lambda _, a=app, b=btn: self._on_uninstall_clicked(a, b))
        self._app_uninstall_btns[app["pkg"]] = uninstall_btn

        card.append(icon_lbl); card.append(info); card.append(btn); card.append(reinstall_btn); card.append(uninstall_btn)
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

    # ─── Useful tools section ─────────────────────────────────────────────────
    def _build_tools_section(self):
        batch_btn = Gtk.Button(label="Install All")
        batch_btn.add_css_class("batch-btn")
        batch_btn.set_sensitive(False)
        batch_btn.connect("clicked", lambda _: self._batch_install(TOOLS))
        self._tools_batch_btn = batch_btn

        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("BEGINNER", "Useful Tools", batch_btn))

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(2); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        for tool in TOOLS:
            grid.append(self._make_app_card(tool))
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
        critical_names = {"Full System Update", "Fix: Boot Issues"}
        handler = self._on_fix_critical if fix.get("name") in critical_names else self._on_fix
        btn.connect("clicked", lambda _, f=fix, b=btn, h=handler: h(f, b))
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

    # ─── Drivers section ──────────────────────────────────────────────────────
    def _build_drivers_section(self):
        detect_btn = Gtk.Button(label="Auto-detect GPU")
        detect_btn.add_css_class("batch-btn")
        detect_btn.connect("clicked", lambda _: self._detect_gpu())
        self._gpu_detect_btn = detect_btn

        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("HARDWARE", "GPU Drivers", detect_btn))

        self._gpu_detect_label = Gtk.Label(label="")
        self._gpu_detect_label.add_css_class("app-pkg")
        self._gpu_detect_label.set_halign(Gtk.Align.START)
        self._gpu_detect_label.set_visible(False)
        sec.append(self._gpu_detect_label)

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(1); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        for drv in DRIVERS:
            grid.append(self._make_driver_card(drv))
        sec.append(grid)

        # Auto-detect on first build of this section
        GLib.idle_add(self._detect_gpu)
        return sec

    def _make_driver_card(self, drv):
        outer = Gtk.Box(); outer.set_hexpand(True)
        outer.set_margin_top(1); outer.set_margin_bottom(1)
        outer.set_margin_start(1); outer.set_margin_end(1)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("app-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label=drv["icon"])
        icon_lbl.add_css_class("app-icon-label")
        icon_lbl.set_margin_start(10); icon_lbl.set_margin_top(8); icon_lbl.set_margin_bottom(8)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info.set_hexpand(True)
        name_lbl = Gtk.Label(label=drv["name"])
        name_lbl.add_css_class("app-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label=drv["desc"])
        desc_lbl.add_css_class("app-pkg"); desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_wrap(True)
        info.append(name_lbl); info.append(desc_lbl)

        btn = Gtk.Button(label="Install")
        btn.add_css_class("btn-install")
        btn.set_valign(Gtk.Align.CENTER); btn.set_margin_end(10)
        btn.connect("clicked", lambda _, d=drv, b=btn: self._on_install_driver(d, b))
        self._driver_btns[drv["vendor"]] = btn

        card.append(icon_lbl); card.append(info); card.append(btn)
        outer.append(card)
        return outer

    def _detect_gpu(self):
        threading.Thread(target=self._detect_gpu_thread, daemon=True).start()
        return False  # for GLib.idle_add one-shot

    def _detect_gpu_thread(self):
        vendor = None
        try:
            out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5).stdout.lower()
            if "nvidia" in out:
                vendor = "nvidia"
            elif "amd" in out or "radeon" in out or "advanced micro devices" in out:
                vendor = "amd"
            elif "intel" in out:
                vendor = "intel"
        except Exception:
            pass
        GLib.idle_add(self._apply_gpu_detection, vendor)

    def _apply_gpu_detection(self, vendor):
        names = {"nvidia": "NVIDIA", "amd": "AMD", "intel": "Intel"}
        if vendor:
            self._gpu_detect_label.set_label(f"🔍 Detected: {names[vendor]} GPU — recommended card highlighted below")
        else:
            self._gpu_detect_label.set_label("🔍 Could not auto-detect GPU vendor — pick manually below")
        self._gpu_detect_label.set_visible(True)
        for v, btn in self._driver_btns.items():
            if v == vendor:
                btn.set_label("Install (recommended)")
            elif btn.get_label() == "Install (recommended)":
                btn.set_label("Install")

    def _on_install_driver(self, drv, btn):
        if not self.yay_ok:
            self._term_write("Install yay first!\n", "err"); return
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return

        btn.set_label("…")
        for cls in ("btn-install", "btn-error", "btn-done"):
            btn.remove_css_class(cls)
        btn.add_css_class("btn-installing"); btn.set_sensitive(False)

        pkgs = " ".join(drv["pkgs"])
        cmd = f"yay -S {pkgs} --noconfirm --sudoflags '-A'"
        self._term_write(f"\n--- Installing {drv['name']} driver ---\n", "info")
        self._term_write(f"$ yay -S {pkgs} --noconfirm\n", "cmd_echo")

        def done(ok):
            btn.remove_css_class("btn-installing")
            if ok:
                btn.set_label("Installed")
                btn.add_css_class("btn-done"); btn.set_sensitive(False)
                self._term_write(
                    "⚠  Reboot required for the new driver to take effect.\n", "info")
            else:
                btn.set_label("Retry")
                btn.add_css_class("btn-error"); btn.set_sensitive(True)

        self._run_in_terminal(cmd, on_done=done)

    # ─── Performance tools section ────────────────────────────────────────────
    def _build_performance_section(self):
        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("TUNING", "Performance Tools"))

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(2); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        grid.append(self._make_gamemode_card())
        grid.append(self._make_swappiness_card())
        sec.append(grid)
        return sec

    def _make_gamemode_card(self):
        outer = Gtk.Box(); outer.set_hexpand(True)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("fix-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label="🚀")
        icon_lbl.add_css_class("fix-icon")
        icon_lbl.set_margin_start(12); icon_lbl.set_margin_top(12); icon_lbl.set_margin_bottom(12)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        name_lbl = Gtk.Label(label="Enable Gamemode")
        name_lbl.add_css_class("fix-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label="Install + add user to gamemode group")
        desc_lbl.add_css_class("fix-desc"); desc_lbl.set_halign(Gtk.Align.START)
        text.append(name_lbl); text.append(desc_lbl)

        btn = Gtk.Button(label="Run")
        btn.add_css_class("btn-fix"); btn.set_valign(Gtk.Align.CENTER)
        btn.set_margin_end(12)
        btn.connect("clicked", self._on_enable_gamemode)
        self._gamemode_btn = btn

        card.append(icon_lbl); card.append(text); card.append(btn)
        outer.append(card)
        return outer

    def _on_enable_gamemode(self, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        btn.set_label("…")
        btn.remove_css_class("btn-fix"); btn.add_css_class("btn-fix-running")
        btn.set_sensitive(False)
        self._term_write("\n--- Enabling Gamemode ---\n", "info")
        self._run_gamemode_steps(list(GAMEMODE_STEPS), btn)

    def _run_gamemode_steps(self, steps, btn):
        if not steps:
            btn.set_label("Done"); btn.remove_css_class("btn-fix-running")
            btn.add_css_class("btn-done")
            return
        step = steps.pop(0)
        self._term_write(f"$ {step}\n", "cmd_echo")

        def done(ok):
            if ok:
                self._run_gamemode_steps(steps, btn)
            else:
                self._term_write("A step failed — check the output above.\n", "err")
                btn.set_label("Run"); btn.remove_css_class("btn-fix-running")
                btn.add_css_class("btn-fix"); btn.set_sensitive(True)

        self._run_in_terminal(step, on_done=done)

    def _make_swappiness_card(self):
        outer = Gtk.Box(); outer.set_hexpand(True)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("fix-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label="🧠")
        icon_lbl.add_css_class("fix-icon")
        icon_lbl.set_margin_start(12); icon_lbl.set_margin_top(12); icon_lbl.set_margin_bottom(12)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        name_lbl = Gtk.Label(label="Swappiness")
        name_lbl.add_css_class("fix-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label="Lower = less swap usage (10 recommended for 16GB+ RAM)")
        desc_lbl.add_css_class("fix-desc"); desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_wrap(True)
        text.append(name_lbl); text.append(desc_lbl)

        spin = Gtk.SpinButton.new_with_range(0, 100, 5)
        spin.set_value(60)
        spin.set_valign(Gtk.Align.CENTER)
        spin.set_margin_end(8)
        self._swappiness_spin = spin

        btn = Gtk.Button(label="Apply")
        btn.add_css_class("btn-fix"); btn.set_valign(Gtk.Align.CENTER)
        btn.set_margin_end(12)
        btn.connect("clicked", self._on_apply_swappiness)

        card.append(icon_lbl); card.append(text); card.append(spin); card.append(btn)
        outer.append(card)
        return outer

    def _on_apply_swappiness(self, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        value = int(self._swappiness_spin.get_value())
        btn.set_label("…")
        btn.remove_css_class("btn-fix"); btn.add_css_class("btn-fix-running")
        btn.set_sensitive(False)
        self._term_write(f"\n--- Setting swappiness to {value} ---\n", "info")
        cmd = (
            f"sudo sysctl vm.swappiness={value} && "
            f"echo 'vm.swappiness={value}' | sudo tee /etc/sysctl.d/99-swappiness.conf"
        )
        self._term_write(f"$ {cmd}\n", "cmd_echo")

        def done(ok):
            btn.remove_css_class("btn-fix-running")
            if ok:
                btn.set_label("Applied"); btn.add_css_class("btn-done")
            else:
                btn.set_label("Apply"); btn.add_css_class("btn-fix")
            btn.set_sensitive(True)

        self._run_in_terminal(cmd, on_done=done)

    # ─── Services manager section ────────────────────────────────────────────
    def _build_services_section(self):
        refresh_btn = Gtk.Button(label="Refresh status")
        refresh_btn.add_css_class("check-btn")
        refresh_btn.connect("clicked", lambda _: self._refresh_services())

        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec.append(self._section_header("DAEMONS", "Services Manager", refresh_btn))

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(1); grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_row_spacing(8); grid.set_column_spacing(8)
        grid.set_homogeneous(True)
        for svc in SERVICES:
            grid.append(self._make_service_card(svc))
        sec.append(grid)

        GLib.idle_add(self._refresh_services)
        return sec

    def _make_service_card(self, svc):
        outer = Gtk.Box(); outer.set_hexpand(True)
        outer.set_margin_top(1); outer.set_margin_bottom(1)
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("app-card"); card.set_hexpand(True)

        icon_lbl = Gtk.Label(label=svc["icon"])
        icon_lbl.add_css_class("app-icon-label")
        icon_lbl.set_margin_start(10); icon_lbl.set_margin_top(8); icon_lbl.set_margin_bottom(8)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info.set_hexpand(True)
        name_lbl = Gtk.Label(label=svc["name"])
        name_lbl.add_css_class("app-name"); name_lbl.set_halign(Gtk.Align.START)
        desc_lbl = Gtk.Label(label=svc["desc"])
        desc_lbl.add_css_class("app-pkg"); desc_lbl.set_halign(Gtk.Align.START)
        info.append(name_lbl); info.append(desc_lbl)

        status_lbl = Gtk.Label(label="…")
        status_lbl.add_css_class("svc-status-unknown")
        status_lbl.set_valign(Gtk.Align.CENTER); status_lbl.set_margin_end(8)

        btn = Gtk.Button(label="…")
        btn.add_css_class("btn-svc-start")
        btn.set_valign(Gtk.Align.CENTER); btn.set_margin_end(10)
        btn.set_sensitive(False)
        btn.connect("clicked", lambda _, u=svc["unit"], b=btn, s=status_lbl:
                    self._on_toggle_service_v7(u, b, s))

        self._service_widgets[svc["unit"]] = {"status": status_lbl, "btn": btn}

        card.append(icon_lbl); card.append(info); card.append(status_lbl); card.append(btn)
        outer.append(card)
        return outer

    def _refresh_services(self):
        threading.Thread(target=self._refresh_services_thread, daemon=True).start()
        return False  # one-shot when used with GLib.idle_add

    def _refresh_services_thread(self):
        results = {}
        for svc in SERVICES:
            unit = svc["unit"]
            try:
                r = subprocess.run(["systemctl", "is-active", unit],
                                    capture_output=True, text=True, timeout=5)
                state = r.stdout.strip()
                results[unit] = "active" if state == "active" else "inactive"
            except Exception:
                results[unit] = "unknown"
        GLib.idle_add(self._apply_service_status, results)

    def _apply_service_status(self, results):
        for unit, state in results.items():
            widgets = self._service_widgets.get(unit)
            if not widgets: continue
            status_lbl, btn = widgets["status"], widgets["btn"]
            for cls in ("svc-status-active", "svc-status-inactive", "svc-status-unknown"):
                status_lbl.remove_css_class(cls)
            if state == "active":
                status_lbl.set_label("● Active")
                status_lbl.add_css_class("svc-status-active")
                btn.set_label("Stop")
                for cls in ("btn-svc-start",): btn.remove_css_class(cls)
                btn.add_css_class("btn-svc-stop")
            elif state == "inactive":
                status_lbl.set_label("○ Inactive")
                status_lbl.add_css_class("svc-status-inactive")
                btn.set_label("Start")
                for cls in ("btn-svc-stop",): btn.remove_css_class(cls)
                btn.add_css_class("btn-svc-start")
            else:
                status_lbl.set_label("? Unknown")
                status_lbl.add_css_class("svc-status-unknown")
                btn.set_label("Start")
                btn.add_css_class("btn-svc-start")
            btn.set_sensitive(True)

    def _on_toggle_service(self, unit, btn, status_lbl):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        starting = btn.get_label() == "Start"
        action = "start" if starting else "stop"
        btn.set_label("…"); btn.set_sensitive(False)
        cmd = f"sudo systemctl {action} {unit}"
        self._term_write(f"\n--- {action.capitalize()}ing {unit} ---\n", "info")
        self._term_write(f"$ {cmd}\n", "cmd_echo")

        def done(ok):
            self._refresh_services_single(unit)

        self._run_in_terminal(cmd, on_done=done)

    def _refresh_services_single(self, unit):
        def worker():
            try:
                r = subprocess.run(["systemctl", "is-active", unit],
                                    capture_output=True, text=True, timeout=5)
                state = "active" if r.stdout.strip() == "active" else "inactive"
            except Exception:
                state = "unknown"
            GLib.idle_add(self._apply_service_status, {unit: state})
        threading.Thread(target=worker, daemon=True).start()

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
        self._term_write("WIT v8.1.0 — authenticate sudo, then use the cards.\n", "info")
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
                # Inject askpass so sudo/yay/makepkg never need an interactive terminal.
                # NOTE: yay (a Go binary) calls exec.Command("sudo", ...) directly and
                # ignores SUDO_ASKPASS on its own (see Jguer/yay#913); --sudoflags '-A'
                # also doesn't reach the final `pacman -U` step yay shells out to after
                # building. A bash function override for sudo() would NOT help here,
                # since yay is a separate binary, not a bash subprocess that inherits
                # exported shell functions. The only override that works for *any*
                # process (binary or script) is a real executable shadowing sudo
                # earlier in PATH.
                if self.sudo_ok and os.path.exists(self._askpass_path):
                    env["SUDO_ASKPASS"] = self._askpass_path
                    shim_dir = os.path.expanduser("~/.cache/wit-sudo-shim")
                    shim_path = os.path.join(shim_dir, "sudo")
                    os.makedirs(shim_dir, exist_ok=True)
                    with open(shim_path, "w") as f:
                        f.write('#!/bin/sh\nexec /usr/bin/sudo -A "$@"\n')
                    os.chmod(shim_path, 0o700)
                    env["PATH"] = shim_dir + os.pathsep + env.get("PATH", "")
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
        # ── system notification ──
        try:
            icon = "dialog-information" if success else "dialog-error"
            msg  = "Task completed successfully." if success else "Task finished with errors."
            subprocess.Popen(
                ["notify-send", "-i", icon, "WIT", msg],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
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
        # Pass the password directly — don't re-read the entry later (it may be cleared)
        GLib.idle_add(self._apply_sudo_result, ok, password)

    def _apply_sudo_result(self, ok, raw_pass=""):
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
            # Hide sudo warning if it was showing
            self._show_sudo_warning(False)
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
            # ── yay found: unlock entire UI ──────────────────────────────────
            self._unlock_ui()
            self.yay_badge.set_label("  yay: ready")
            self.yay_badge.add_css_class("badge-ok")
            self._yay_banner.set_visible(False)
            self._term_write("yay found — checking installed packages…\n", "ok")
            self._check_installed_apps()
            # unlock install buttons
            for pkg, btn in self._app_btns.items():
                if btn.get_label() not in ("Installed", "Retry"):
                    btn.set_sensitive(True)
            if hasattr(self, "_win_btns"):
                for pkg, btn in self._win_btns.items():
                    if btn.get_label() not in ("Installed", "Retry"):
                        btn.set_sensitive(True)
            if hasattr(self, "_apps_batch_btn"):
                self._apps_batch_btn.set_sensitive(True)
            if hasattr(self, "_gaming_batch_btn"):
                self._gaming_batch_btn.set_sensitive(True)
            if hasattr(self, "_tools_batch_btn"):
                self._tools_batch_btn.set_sensitive(True)
        else:
            # ── yay missing: lock entire UI and show overlay ──────────────────
            self._lock_ui()
            self.yay_badge.set_label("  yay: missing")
            self.yay_badge.add_css_class("badge-fail")
            self._yay_banner.set_visible(True)
            self._term_write("yay not found — install it from the top-right banner.\n", "err")
            for btn in self._app_btns.values():
                btn.set_sensitive(False)
        self._term_write("$ ", "prompt")

    # ─── Check which apps are already installed ───────────────────────────────
    def _check_installed_apps(self):
        threading.Thread(target=self._check_installed_thread, daemon=True).start()

    def _check_installed_thread(self):
        results = {}
        all_pkgs = [a["pkg"] for a in APPS + GAMING_APPS + TOOLS + WINDOWS_APPS]
        for pkg in all_pkgs:
            r = subprocess.run(["pacman", "-Q", pkg], capture_output=True, text=True)
            results[pkg] = r.returncode == 0
        GLib.idle_add(self._apply_installed_results, results)

    def _apply_installed_results(self, results):
        for pkg, installed in results.items():
            btn = self._app_btns.get(pkg) or self._win_btns.get(pkg)
            if not btn: continue
            if installed:
                btn.set_label("Installed")
                for cls in ("btn-install", "btn-error", "btn-installing"):
                    btn.remove_css_class(cls)
                btn.add_css_class("btn-done")
                btn.set_sensitive(False)
                rbtn = self._app_reinstall_btns.get(pkg)
                if rbtn: rbtn.set_visible(True)
                ubtn = self._app_uninstall_btns.get(pkg)
                if ubtn: ubtn.set_visible(True)
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
    def _on_install(self, app, btn, reinstall=False):
        if not self.yay_ok:
            self._term_write("Install yay first!\n", "err"); return
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return

        rbtn = self._app_reinstall_btns.get(app["pkg"])
        ubtn = self._app_uninstall_btns.get(app["pkg"])

        btn.set_label("…")
        for cls in ("btn-install", "btn-error", "btn-done"):
            btn.remove_css_class(cls)
        btn.add_css_class("btn-installing"); btn.set_sensitive(False)
        if rbtn:
            rbtn.set_sensitive(False)
        if ubtn:
            ubtn.set_sensitive(False)

        cmd = f"yay -S {app['pkg']} --noconfirm --sudoflags '-A'"
        label = f"Reinstalling {app['name']}" if reinstall else f"Installing {app['name']}"
        self._term_write(f"\n--- {label} ---\n", "info")
        self._term_write(f"$ yay -S {app['pkg']} --noconfirm\n", "cmd_echo")

        def done(ok):
            if ok:
                btn.set_label("Installed")
                btn.remove_css_class("btn-installing")
                btn.add_css_class("btn-done"); btn.set_sensitive(False)
                if rbtn:
                    rbtn.set_visible(True); rbtn.set_sensitive(True)
                if ubtn:
                    ubtn.set_visible(True); ubtn.set_sensitive(True)
            else:
                btn.set_label("Retry")
                btn.remove_css_class("btn-installing")
                btn.add_css_class("btn-error"); btn.set_sensitive(True)
                if rbtn:
                    rbtn.set_sensitive(True)
                if ubtn:
                    ubtn.set_sensitive(True)

        self._run_in_terminal(cmd, on_done=done)

    # ─── Uninstall single app ─────────────────────────────────────────────────
    def _on_uninstall_clicked(self, app, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        threading.Thread(target=self._scan_user_dirs_thread, args=(app, btn), daemon=True).start()

    def _scan_user_dirs_thread(self, app, btn):
        pkg = app["pkg"]
        candidates = [
            os.path.expanduser(f"~/.config/{pkg}"),
            os.path.expanduser(f"~/.cache/{pkg}"),
            os.path.expanduser(f"~/.local/share/{pkg}"),
        ]
        found = [p for p in candidates if os.path.exists(p)]
        GLib.idle_add(self._show_uninstall_dialog, app, btn, found)

    def _show_uninstall_dialog(self, app, btn, user_dirs):
        body = f"This will remove the “{app['name']}” package"
        if user_dirs:
            body += " and delete these personal data folders:\n\n"
            body += "\n".join(f"  • {p}" for p in user_dirs)
        else:
            body += " (no personal config/cache folders were found)."
        body += "\n\nThis cannot be undone."

        dlg = Adw.MessageDialog.new(self, f"Uninstall {app['name']}?", body)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("uninstall", "Uninstall")
        dlg.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")
        dlg.connect("response", self._on_uninstall_dialog_response, app, btn, user_dirs)
        dlg.present()

    def _on_uninstall_dialog_response(self, dlg, response, app, btn, user_dirs):
        if response != "uninstall":
            return
        self._do_uninstall(app, btn, user_dirs)

    def _do_uninstall(self, app, btn, user_dirs):
        rbtn = self._app_reinstall_btns.get(app["pkg"])
        ubtn = self._app_uninstall_btns.get(app["pkg"])

        btn.set_label("…")
        for cls in ("btn-install", "btn-error", "btn-done"):
            btn.remove_css_class(cls)
        btn.add_css_class("btn-installing"); btn.set_sensitive(False)
        if rbtn:
            rbtn.set_visible(False); rbtn.set_sensitive(False)
        if ubtn:
            ubtn.set_sensitive(False)

        cmd = f"sudo pacman -Rns --noconfirm {app['pkg']}"
        self._term_write(f"\n--- Uninstalling {app['name']} ---\n", "info")
        self._term_write(f"$ {cmd}\n", "cmd_echo")

        def done(ok):
            if ok:
                for p in user_dirs:
                    try:
                        if os.path.isdir(p):
                            shutil.rmtree(p)
                        else:
                            os.remove(p)
                        self._term_write(f"Removed {p}\n", "dim")
                    except Exception as exc:
                        self._term_write(f"Could not remove {p}: {exc}\n", "err")
                btn.set_label("Install")
                btn.remove_css_class("btn-installing")
                btn.add_css_class("btn-install"); btn.set_sensitive(True)
                if ubtn:
                    ubtn.set_visible(False)
                self._term_write(f"{app['name']} uninstalled.\n", "ok")
            else:
                btn.set_label("Installed")
                btn.remove_css_class("btn-installing")
                btn.add_css_class("btn-done"); btn.set_sensitive(False)
                if rbtn:
                    rbtn.set_visible(True); rbtn.set_sensitive(True)
                if ubtn:
                    ubtn.set_sensitive(True)

        self._run_in_terminal(cmd, on_done=done)
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

    # =========================================================================
    # v8.1 — Undo / Restore bar
    # =========================================================================
    def _build_undo_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.add_css_class("undo-bar")
        bar.set_visible(False)

        self._undo_label = Gtk.Label(label="")
        self._undo_label.add_css_class("undo-label")
        self._undo_label.set_hexpand(True)
        self._undo_label.set_halign(Gtk.Align.START)

        undo_btn = Gtk.Button(label="↩  Undo")
        undo_btn.add_css_class("undo-btn")
        undo_btn.connect("clicked", self._on_undo)

        dismiss_btn = Gtk.Button(label="✕")
        dismiss_btn.add_css_class("term-clear-btn")
        dismiss_btn.connect("clicked", lambda _: self._undo_bar.set_visible(False))

        bar.append(self._undo_label)
        bar.append(undo_btn)
        bar.append(dismiss_btn)
        return bar

    def _push_undo(self, description: str, undo_cmd: str):
        """Register an undoable operation and show the undo bar."""
        self._undo_stack.append({"desc": description, "cmd": undo_cmd})
        self._undo_label.set_label(f"Last action: {description}")
        self._undo_bar.set_visible(True)

    def _on_undo(self, _):
        if not self._undo_stack:
            self._undo_bar.set_visible(False)
            return
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err")
            return
        op = self._undo_stack.pop()
        self._undo_bar.set_visible(bool(self._undo_stack))
        if self._undo_stack:
            self._undo_label.set_label(f"Last action: {self._undo_stack[-1]['desc']}")
        self._term_write(f"\n--- Undoing: {op['desc']} ---\n", "info")
        self._term_write(f"$ {op['cmd']}\n", "cmd_echo")
        self._run_in_terminal(op["cmd"])

    # =========================================================================
    # v8.1 — Task manager bar (bottom)
    # =========================================================================
    def _build_task_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.add_css_class("task-bar")
        bar.set_visible(False)

        self._task_label = Gtk.Label(label="")
        self._task_label.add_css_class("task-label")
        self._task_label.set_hexpand(True)
        self._task_label.set_halign(Gtk.Align.START)

        self._task_progress = Gtk.ProgressBar()
        self._task_progress.set_pulse_step(0.06)
        self._task_progress.set_show_text(False)

        cancel_btn = Gtk.Button(label="✕  Cancel")
        cancel_btn.add_css_class("task-cancel-btn")
        cancel_btn.connect("clicked", self._on_cancel_task)

        bar.append(self._task_label)
        bar.append(self._task_progress)
        bar.append(cancel_btn)
        return bar

    def _show_task(self, label: str):
        self._task_label.set_label(label)
        self._task_bar.set_visible(True)
        self._task_cancelled = False
        # Pulse animation
        def _pulse():
            if self._running:
                self._task_progress.pulse()
                return True
            self._task_bar.set_visible(False)
            return False
        GLib.timeout_add(120, _pulse)

    def _on_cancel_task(self, _):
        self._task_cancelled = True
        if self._active_proc:
            try:
                self._active_proc.kill()
            except Exception:
                pass
        self._term_write("\n[task cancelled by user]\n", "err")
        self._task_bar.set_visible(False)

    # =========================================================================
    # v8.1 — Package History page
    # =========================================================================
    def _build_history_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_vexpand(True)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar.set_margin_top(18); toolbar.set_margin_bottom(10)
        toolbar.set_margin_start(22); toolbar.set_margin_end(22)

        title = Gtk.Label(label="Operation History")
        title.add_css_class("section-title"); title.set_hexpand(True)
        title.set_halign(Gtk.Align.START)

        clear_btn = Gtk.Button(label="🗑  Clear History")
        clear_btn.add_css_class("history-clear-btn")
        clear_btn.connect("clicked", self._clear_history)

        toolbar.append(title); toolbar.append(clear_btn)
        outer.append(toolbar)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._history_box.set_margin_start(22); self._history_box.set_margin_end(22)
        self._history_box.set_margin_bottom(22)

        self._history_empty_lbl = Gtk.Label(label="No operations recorded yet.")
        self._history_empty_lbl.add_css_class("sudo-label")
        self._history_empty_lbl.set_valign(Gtk.Align.CENTER)
        self._history_empty_lbl.set_halign(Gtk.Align.CENTER)
        self._history_empty_lbl.set_vexpand(True)
        self._history_box.append(self._history_empty_lbl)

        scroll.set_child(self._history_box)
        outer.append(scroll)
        return outer

    def _log_history(self, action: str, name: str, detail: str = ""):
        import datetime
        entry = {
            "action": action,
            "name":   name,
            "detail": detail,
            "time":   datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S"),
        }
        self._history.append(entry)
        GLib.idle_add(self._add_history_card, entry)

    def _add_history_card(self, entry: dict):
        # Hide empty label
        self._history_empty_lbl.set_visible(False)

        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.add_css_class("history-card")

        # Action icon + colour
        icons = {"install": "📦", "remove": "🗑", "fix": "🔧",
                 "system": "🔄", "driver": "🎛", "backup": "💾"}
        css_map = {"install": "history-action-install", "remove": "history-action-remove",
                   "fix": "history-action-fix", "system": "history-action-system",
                   "driver": "history-action-install", "backup": "history-action-system"}
        icon = Gtk.Label(label=icons.get(entry["action"], "•"))
        icon.set_margin_start(12); icon.set_margin_top(10); icon.set_margin_bottom(10)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)
        name_lbl = Gtk.Label(label=entry["name"])
        name_lbl.add_css_class("history-pkg"); name_lbl.set_halign(Gtk.Align.START)
        act_lbl = Gtk.Label(label=entry["action"].upper())
        act_lbl.add_css_class(css_map.get(entry["action"], "history-action-fix"))
        act_lbl.set_halign(Gtk.Align.START)
        info.append(name_lbl); info.append(act_lbl)

        time_lbl = Gtk.Label(label=entry["time"])
        time_lbl.add_css_class("history-time")
        time_lbl.set_valign(Gtk.Align.CENTER)
        time_lbl.set_margin_end(14)

        card.append(icon); card.append(info); card.append(time_lbl)
        # Insert newest on top (after empty label)
        self._history_box.prepend(card)

    def _clear_history(self, _):
        self._history.clear()
        # Remove all cards except the empty label
        child = self._history_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            if child is not self._history_empty_lbl:
                self._history_box.remove(child)
            child = nxt
        self._history_empty_lbl.set_visible(True)

    # =========================================================================
    # v8.1 — Diagnostics Report page
    # =========================================================================
    def _build_diagnostics_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_vexpand(True)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        toolbar.set_margin_top(18); toolbar.set_margin_bottom(10)
        toolbar.set_margin_start(22); toolbar.set_margin_end(22)

        title = Gtk.Label(label="System Diagnostics")
        title.add_css_class("section-title"); title.set_hexpand(True)
        title.set_halign(Gtk.Align.START)

        run_btn = Gtk.Button(label="▶  Run Scan")
        run_btn.add_css_class("diag-run-btn")
        run_btn.connect("clicked", lambda _: self._run_diagnostics())

        # Export format chooser
        fmt_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fmt_lbl = Gtk.Label(label="Export as:"); fmt_lbl.add_css_class("sudo-label")
        self._diag_fmt = Gtk.DropDown.new_from_strings(["Markdown (.md)", "Plain Text (.txt)", "HTML (.html)"])
        self._diag_fmt.set_selected(0)

        export_btn = Gtk.Button(label="💾  Save Report")
        export_btn.add_css_class("diag-export-btn")
        export_btn.connect("clicked", self._export_diagnostics)

        fmt_box.append(fmt_lbl); fmt_box.append(self._diag_fmt); fmt_box.append(export_btn)

        toolbar.append(title)
        toolbar.append(run_btn)
        toolbar.append(fmt_box)
        outer.append(toolbar)

        sep = Gtk.Separator(); sep.add_css_class("dim-sep"); outer.append(sep)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._diag_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._diag_box.set_margin_top(16); self._diag_box.set_margin_bottom(22)
        self._diag_box.set_margin_start(22); self._diag_box.set_margin_end(22)

        placeholder = Gtk.Label(label="Click  ▶ Run Scan  to collect system information.")
        placeholder.add_css_class("sudo-label")
        placeholder.set_halign(Gtk.Align.CENTER); placeholder.set_valign(Gtk.Align.CENTER)
        placeholder.set_vexpand(True)
        self._diag_placeholder = placeholder
        self._diag_box.append(placeholder)

        scroll.set_child(self._diag_box)
        outer.append(scroll)

        self._diag_data: dict = {}
        return outer

    def _run_diagnostics(self):
        self._diag_placeholder.set_visible(False)
        # Clear old cards
        child = self._diag_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            if child is not self._diag_placeholder:
                self._diag_box.remove(child)
            child = nxt

        spinner_lbl = Gtk.Label(label="Collecting system info…")
        spinner_lbl.add_css_class("sudo-label"); spinner_lbl.set_halign(Gtk.Align.CENTER)
        self._diag_box.append(spinner_lbl)
        threading.Thread(target=self._collect_diag_thread,
                         args=(spinner_lbl,), daemon=True).start()

    def _collect_diag_thread(self, spinner_lbl):
        def run(cmd):
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True,
                                   text=True, timeout=10)
                return r.stdout.strip()
            except Exception:
                return "N/A"

        data = {}
        data["OS"] = run("cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'")
        data["Kernel"] = run("uname -r")
        data["Architecture"] = run("uname -m")
        data["Hostname"] = run("hostname")
        data["Uptime"] = run("uptime -p")
        data["CPU"] = run("lscpu | grep 'Model name' | cut -d: -f2 | xargs")
        data["CPU Cores"] = run("nproc")
        data["RAM Total"] = run("free -h | awk '/^Mem:/{print $2}'")
        data["RAM Used"] = run("free -h | awk '/^Mem:/{print $3}'")
        data["GPU"] = run("lspci | grep -i 'vga\\|3d\\|display' | head -1 | cut -d: -f3 | xargs")
        data["GPU Driver"] = run("lspci -k | grep -A2 -i 'vga\\|3d' | grep 'driver in use' | head -1 | cut -d: -f2 | xargs")
        data["Disk Usage"] = run("df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\" used)\"}'")
        data["Active Services"] = run("systemctl list-units --state=running --no-legend --no-pager | wc -l") + " running"
        data["Installed Packages"] = run("pacman -Q 2>/dev/null | wc -l") + " packages"
        data["yay Version"] = run("yay --version 2>/dev/null | head -1") or "not installed"
        data["Journal Errors (24h)"] = run("journalctl -p err --since '24h ago' --no-pager -q | tail -5")
        data["Failed Services"] = run("systemctl --failed --no-legend --no-pager 2>/dev/null | head -5") or "none"
        data["Network Interfaces"] = run("ip -brief addr | head -6")

        self._diag_data = data
        GLib.idle_add(self._render_diag_cards, spinner_lbl, data)

    def _render_diag_cards(self, spinner_lbl, data: dict):
        self._diag_box.remove(spinner_lbl)

        sections = {
            "🖥️  System": ["OS", "Kernel", "Architecture", "Hostname", "Uptime"],
            "⚙️  Hardware": ["CPU", "CPU Cores", "RAM Total", "RAM Used", "GPU", "GPU Driver", "Disk Usage"],
            "📦  Software": ["Installed Packages", "yay Version", "Active Services"],
            "📡  Network": ["Network Interfaces"],
            "⚠️  Issues": ["Failed Services", "Journal Errors (24h)"],
        }

        for section_title, keys in sections.items():
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            card.add_css_class("diag-card")

            hdr = Gtk.Label(label=section_title)
            hdr.add_css_class("diag-section-title"); hdr.set_halign(Gtk.Align.START)
            card.append(hdr)

            sep = Gtk.Separator(); sep.add_css_class("dim-sep"); card.append(sep)

            for key in keys:
                val = data.get(key, "N/A")
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.set_margin_top(2)
                k_lbl = Gtk.Label(label=f"{key}:")
                k_lbl.add_css_class("diag-key")
                k_lbl.set_width_chars(22); k_lbl.set_halign(Gtk.Align.START)
                v_lbl = Gtk.Label(label=val or "N/A")
                v_lbl.add_css_class("diag-value"); v_lbl.set_halign(Gtk.Align.START)
                v_lbl.set_selectable(True); v_lbl.set_wrap(True)
                row.append(k_lbl); row.append(v_lbl)
                card.append(row)

            self._diag_box.append(card)

    def _export_diagnostics(self, _):
        if not self._diag_data:
            self._term_write("Run a scan first before exporting.\n", "err"); return
        import datetime
        fmt_idx = self._diag_fmt.get_selected()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        home = os.path.expanduser("~")

        if fmt_idx == 0:     # Markdown
            ext = "md"; path = f"{home}/wit-report-{ts}.md"
            lines = [f"# WIT Diagnostics Report\n*Generated: {datetime.datetime.now()}*\n"]
            sections = {
                "System": ["OS","Kernel","Architecture","Hostname","Uptime"],
                "Hardware": ["CPU","CPU Cores","RAM Total","RAM Used","GPU","GPU Driver","Disk Usage"],
                "Software": ["Installed Packages","yay Version","Active Services"],
                "Network": ["Network Interfaces"],
                "Issues": ["Failed Services","Journal Errors (24h)"],
            }
            for sec, keys in sections.items():
                lines.append(f"\n## {sec}\n")
                for k in keys:
                    v = self._diag_data.get(k, "N/A")
                    lines.append(f"| **{k}** | `{v}` |")
            content = "\n".join(lines)
        elif fmt_idx == 1:   # Plain text
            ext = "txt"; path = f"{home}/wit-report-{ts}.txt"
            lines = [f"WIT Diagnostics Report — {datetime.datetime.now()}\n{'='*60}"]
            for k, v in self._diag_data.items():
                lines.append(f"{k:<28}{v}")
            content = "\n".join(lines)
        else:                # HTML
            ext = "html"; path = f"{home}/wit-report-{ts}.html"
            rows = "".join(
                f"<tr><td><b>{k}</b></td><td><code>{v}</code></td></tr>"
                for k, v in self._diag_data.items()
            )
            content = (
                f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                f"<title>WIT Report</title>"
                f"<style>body{{font-family:monospace;background:#0b0b18;color:#dde3f0;padding:2em}}"
                f"table{{border-collapse:collapse;width:100%}}"
                f"td{{padding:6px 12px;border-bottom:1px solid #1c1c3a}}"
                f"b{{color:#818cf8}}code{{color:#30c984}}</style></head>"
                f"<body><h1>WIT Diagnostics Report</h1>"
                f"<p><i>{datetime.datetime.now()}</i></p>"
                f"<table>{rows}</table></body></html>"
            )

        try:
            with open(path, "w") as f:
                f.write(content)
            self._term_write(f"Report saved: {path}\n", "ok")
            self._log_history("system", f"Diagnostics exported ({ext.upper()})", path)
        except Exception as exc:
            self._term_write(f"Export failed: {exc}\n", "err")

    # =========================================================================
    # v8.1 — Backup via Timeshift before critical operations
    # =========================================================================
    def _try_timeshift_backup(self, reason: str, on_done):
        """Create a Timeshift snapshot if available, then call on_done()."""
        if not shutil.which("timeshift"):
            self._term_write("Timeshift not found — skipping backup.\n", "dim")
            on_done()
            return

        self._term_write(f"\n💾 Creating Timeshift snapshot before: {reason}\n", "info")
        cmd = "sudo timeshift --create --comments 'WIT auto-backup' --scripted"
        self._term_write(f"$ {cmd}\n", "cmd_echo")

        def done(ok):
            if ok:
                self._term_write("Snapshot created successfully.\n", "ok")
                self._log_history("backup", f"Timeshift snapshot ({reason})")
            else:
                self._term_write("Snapshot failed — continuing anyway.\n", "err")
            on_done()

        self._run_in_terminal(cmd, on_done=done)

    # =========================================================================
    # v8.1 — Override/wrap key actions to add history + undo + task bar
    # =========================================================================
    def _on_fix_critical(self, fix, btn):
        """Run a Timeshift backup first, then execute the fix."""
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        def do_fix():
            self._on_fix(fix, btn)
        self._try_timeshift_backup(fix["name"], do_fix)

    def _on_fix(self, fix, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        btn.set_label("…")
        btn.remove_css_class("btn-fix"); btn.add_css_class("btn-fix-running")
        btn.set_sensitive(False)
        cmd = " && ".join(fix["cmds"])
        self._term_write(f"\n--- {fix['name']} ---\n", "info")
        self._term_write(f"$ {cmd}\n", "cmd_echo")
        self._show_task(f"Running: {fix['name']}")

        def done(ok):
            btn.set_label("Run")
            btn.remove_css_class("btn-fix-running")
            btn.add_css_class("btn-fix"); btn.set_sensitive(True)
            if ok:
                self._log_history("fix", fix["name"])

        self._run_in_terminal(cmd, on_done=done)

    def _on_advanced_fix(self, steps, btn):
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        btn.set_label("Running…"); btn.set_sensitive(False)
        self._switch_tab("main")
        self._show_task(f"Advanced fix: {btn.get_label()}")
        self._run_step_chain(list(steps), btn)

    def _on_toggle_service_v7(self, unit, btn, status_lbl):
        """v7 wrapper that adds undo support to service toggle."""
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return
        starting = btn.get_label() == "Start"
        action = "start" if starting else "stop"
        undo_action = "stop" if starting else "start"
        btn.set_label("…"); btn.set_sensitive(False)
        cmd = f"sudo systemctl {action} {unit}"
        undo_cmd = f"sudo systemctl {undo_action} {unit}"
        self._term_write(f"\n--- {action.capitalize()}ing {unit} ---\n", "info")
        self._term_write(f"$ {cmd}\n", "cmd_echo")
        self._show_task(f"{action.capitalize()}ing {unit}")

        def done(ok):
            self._refresh_services_single(unit)
            if ok:
                self._push_undo(f"{action} {unit}", undo_cmd)
                self._log_history("system", f"{action} {unit}")

        self._run_in_terminal(cmd, on_done=done)

    def _on_install_with_history(self, app, btn, reinstall=False):
        """Wraps _on_install to add history + undo + task bar + optional backup."""
        if not self.yay_ok:
            self._term_write("Install yay first!\n", "err"); return
        if self._running:
            self._term_write("[busy] finish current task first.\n", "err"); return

        def do_install():
            rbtn = self._app_reinstall_btns.get(app["pkg"])
            ubtn = self._app_uninstall_btns.get(app["pkg"])
            btn.set_label("…")
            for cls in ("btn-install", "btn-error", "btn-done"):
                btn.remove_css_class(cls)
            btn.add_css_class("btn-installing"); btn.set_sensitive(False)
            if rbtn: rbtn.set_sensitive(False)
            if ubtn: ubtn.set_sensitive(False)

            cmd = f"yay -S {app['pkg']} --noconfirm --sudoflags '-A'"
            label = f"Reinstalling {app['name']}" if reinstall else f"Installing {app['name']}"
            self._term_write(f"\n--- {label} ---\n", "info")
            self._term_write(f"$ yay -S {app['pkg']} --noconfirm\n", "cmd_echo")
            self._show_task(label)

            def done(ok):
                if ok:
                    btn.set_label("Installed")
                    btn.remove_css_class("btn-installing")
                    btn.add_css_class("btn-done"); btn.set_sensitive(False)
                    if rbtn: rbtn.set_visible(True); rbtn.set_sensitive(True)
                    if ubtn: ubtn.set_visible(True); ubtn.set_sensitive(True)
                    self._log_history("install", app["name"], app["pkg"])
                    self._push_undo(
                        f"Installed {app['name']}",
                        f"sudo pacman -Rns --noconfirm {app['pkg']}"
                    )
                else:
                    btn.set_label("Retry")
                    btn.remove_css_class("btn-installing")
                    btn.add_css_class("btn-error"); btn.set_sensitive(True)
                    if rbtn: rbtn.set_sensitive(True)
                    if ubtn: ubtn.set_sensitive(True)

            self._run_in_terminal(cmd, on_done=done)

        do_install()

    # =========================================================================
    # About & Self-Uninstall
    # =========================================================================
    def _show_about_dialog(self, _):
        dlg = Adw.MessageDialog.new(
            self,
            "WIT — CachyOS Toolkit",
            "Version:      8.1.0\n"
            "Developer:  zenox / yolan\n"
            "Instagram:   @z7.nv\n"
            "License:      MIT\n"
            "Source:       github.com/zenox444x/WIT\n\n"
            "WIT installs apps, fixes system issues, manages\n"
            "GPU drivers, gaming tools, and more — all from\n"
            "a single GTK4 interface on CachyOS.",
        )
        dlg.add_response("close",     "Close")
        dlg.add_response("uninstall", "🗑  Uninstall WIT")
        dlg.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("close")
        dlg.set_close_response("close")
        dlg.connect("response", self._on_about_response)
        dlg.present()

    def _on_about_response(self, dlg, response):
        if response != "uninstall":
            return
        # Confirmation dialog
        confirm = Adw.MessageDialog.new(
            self,
            "Uninstall WIT?",
            "This will:\n"
            "  • Remove the WIT package  (pacman -Rns wit)\n"
            "  • Delete  /usr/lib/wit/wit.py  and all copies found on the system\n"
            "  • Delete  /usr/share/icons/.../wit.png\n"
            "  • Delete  /usr/share/applications/wit.desktop\n"
            "  • Delete  /usr/bin/wit\n\n"
            "The app will close itself when done.\n"
            "This cannot be undone.",
        )
        confirm.add_response("cancel",    "Cancel")
        confirm.add_response("confirmed", "Yes, Uninstall")
        confirm.set_response_appearance("confirmed", Adw.ResponseAppearance.DESTRUCTIVE)
        confirm.set_default_response("cancel")
        confirm.set_close_response("cancel")
        confirm.connect("response", self._on_uninstall_confirmed)
        confirm.present()

    def _on_uninstall_confirmed(self, dlg, response):
        if response != "confirmed":
            return
        if not self.sudo_ok:
            self._term_write("Authenticate sudo first before uninstalling.\n", "err")
            self._switch_tab("main")
            return
        self._switch_tab("main")
        self._term_write("\n--- Uninstalling WIT ---\n", "info")
        self._term_write("Building uninstall script and launching in terminal…\n", "info")
        self._do_self_uninstall()

    def _do_self_uninstall(self):
        """
        Build a single self-contained bash -c one-liner and hand it directly
        to an independent terminal.  The entire removal command is baked into
        the terminal's argv BEFORE WIT closes, so even if WIT's process dies
        mid-uninstall the terminal keeps running without ever asking WIT for
        the next instruction.
        """
        askpass  = self._askpass_path
        shim_dir = os.path.expanduser("~/.cache/wit-sudo-shim")

        # ── One-liner: every step separated by " && " or "; " so the shell
        #    executes them sequentially from its own memory, not from WIT. ──────
        one_liner = (
            f"export SUDO_ASKPASS='{askpass}'; "
            f"export PATH='{shim_dir}:$PATH'; "
            "echo ''; "
            "echo '========================================';"
            "echo '  WIT Self-Uninstall';"
            "echo '========================================';"
            "echo '';"
            # 1. pacman remove
            "echo '[1/5] Removing WIT package...';"
            "sudo pacman -Rns --noconfirm wit 2>/dev/null || true;"
            # 2. hunt every wit.py
            "echo '[2/5] Searching for wit.py copies...';"
            "sudo find / -xdev -name 'wit.py' -print -delete 2>/dev/null || true;"
            "sudo rm -rf /usr/lib/wit 2>/dev/null || true;"
            # 3. icon
            "echo '[3/5] Removing icon...';"
            "sudo find /usr/share/icons -name 'wit.png' -delete 2>/dev/null || true;"
            # 4. desktop entry + launcher
            "echo '[4/5] Removing desktop entry and /usr/bin/wit...';"
            "sudo rm -f /usr/share/applications/wit.desktop /usr/bin/wit 2>/dev/null || true;"
            # 5. refresh caches
            "echo '[5/5] Updating caches...';"
            "sudo gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true;"
            "update-desktop-database ~/.local/share/applications 2>/dev/null || true;"
            "echo '';"
            "echo '========================================';"
            "echo '  WIT removed successfully.';"
            "echo '========================================';"
            "echo '';"
            "echo 'This window will close in 5 seconds...';"
            "sleep 5"
        )

        # ── Terminal list — each receives ["terminal", <hold-flag>, "bash", "-c", one_liner]
        #    so the full command lives in the terminal's own argv from launch. ──
        def _make_cmd(term: str) -> list:
            if term == "konsole":
                return ["konsole", "--hold", "-e", "bash", "-c", one_liner]
            if term == "alacritty":
                return ["alacritty", "-e", "bash", "-c", one_liner]
            if term == "kitty":
                return ["kitty", "bash", "-c", one_liner]
            if term == "xterm":
                return ["xterm", "-hold", "-e", "bash", "-c", one_liner]
            if term == "xfce4-terminal":
                return ["xfce4-terminal", "--hold", "-x", "bash", "-c", one_liner]
            if term == "gnome-terminal":
                return ["gnome-terminal", "--wait", "--", "bash", "-c", one_liner]
            return []

        preferred = ["konsole", "alacritty", "kitty", "xterm", "xfce4-terminal", "gnome-terminal"]

        launched = False
        for term in preferred:
            if not shutil.which(term):
                continue
            term_cmd = _make_cmd(term)
            try:
                subprocess.Popen(
                    term_cmd,
                    start_new_session=True,   # fully detached from WIT's session
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                launched = True
                self._term_write(f"Launched in {term} — WIT will close now.\n", "ok")
                break
            except Exception as exc:
                self._term_write(f"Could not launch {term}: {exc}\n", "dim")

        if not launched:
            self._term_write(
                "No terminal emulator found!\n"
                "Run this manually in a terminal:\n"
                f"  bash -c \"{one_liner}\"\n", "err"
            )
            return

        # Close WIT — the external terminal carries on independently
        GLib.timeout_add_seconds(1, self._quit_app)

    def _quit_app(self):
        self.get_application().quit()
        return False


# ─── Entry ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import atexit, shutil as _shutil
    _askpass = os.path.expanduser("~/.cache/wit-askpass.sh")
    _shim_dir = os.path.expanduser("~/.cache/wit-sudo-shim")
    def _cleanup():
        try:
            if os.path.exists(_askpass):
                # Overwrite with zeros before deleting
                with open(_askpass, "w") as f:
                    f.write("#!/bin/sh\necho ''\n")
                os.remove(_askpass)
        except Exception:
            pass
        try:
            if os.path.isdir(_shim_dir):
                _shutil.rmtree(_shim_dir)
        except Exception:
            pass
    atexit.register(_cleanup)

    app = WITApp()
    app.run()
