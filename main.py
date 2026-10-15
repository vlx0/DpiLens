# dpi_lens.py — DpiLens: лупа DPI-скейла монитора + смена масштаба
# Python 3.8+, stdlib only, Windows 8.1+/10/11, без прав админа
# MIT License
#
# Показывает per-monitor DPI для монитора под курсором.
# Кнопки масштаба (100/125/150/175/200%) реально меняют системный
# DPI через UI Automation (SendKeys + combobox AutomationId в
# «Параметры → Дисплей»). Без перелогина в большинстве случаев.

import ctypes
import ctypes.wintypes as w
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

if sys.platform != "win32":
    print("Windows only")
    sys.exit(1)

# ---------- WinAPI ----------
user32 = ctypes.windll.user32

try:
    shcore = ctypes.windll.shcore
    HAS_SHCORE = True
except OSError:
    shcore = None
    HAS_SHCORE = False

class POINT(ctypes.Structure):
    _fields_ = [("x", w.LONG), ("y", w.LONG)]

class RECT(ctypes.Structure):
    _fields_ = [("left", w.LONG), ("top", w.LONG),
                ("right", w.LONG), ("bottom", w.LONG)]

class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", w.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", w.DWORD),
                ("szDevice", w.WCHAR * 32)]

MONITOR_DEFAULTTONEAREST = 2
MDT_EFFECTIVE_DPI = 0

user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = w.BOOL

user32.MonitorFromPoint.argtypes = [POINT, w.DWORD]
user32.MonitorFromPoint.restype = w.HANDLE

user32.GetMonitorInfoW.argtypes = [w.HANDLE, ctypes.POINTER(MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = w.BOOL

if HAS_SHCORE:
    shcore.GetDpiForMonitor.argtypes = [
        w.HANDLE, ctypes.c_int,
        ctypes.POINTER(w.UINT), ctypes.POINTER(w.UINT)]
    shcore.GetDpiForMonitor.restype = ctypes.c_long

# ---------- DPI: чтение ----------
def monitor_under_cursor():
    pt = POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        return None
    return user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)


def get_dpi_for(hmonitor):
    if not hmonitor:
        return None
    if HAS_SHCORE:
        dpiX = w.UINT()
        dpiY = w.UINT()
        hr = shcore.GetDpiForMonitor(hmonitor, MDT_EFFECTIVE_DPI,
                                     ctypes.byref(dpiX), ctypes.byref(dpiY))
        if hr == 0 and dpiX.value > 0:
            return dpiX.value
    hdc = user32.GetDC(None)
    try:
        LOGPIXELSX = 88
        gdi32 = ctypes.windll.gdi32
        gdi32.GetDeviceCaps.argtypes = [w.HDC, ctypes.c_int]
        gdi32.GetDeviceCaps.restype = ctypes.c_int
        dpi = gdi32.GetDeviceCaps(hdc, LOGPIXELSX)
        return dpi if dpi > 0 else None
    finally:
        user32.ReleaseDC(None, hdc)


def monitor_info(hmonitor):
    mi = MONITORINFOEXW()
    mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
    if not user32.GetMonitorInfoW(hmonitor, ctypes.byref(mi)):
        return None
    r = mi.rcMonitor
    return {
        "device": mi.szDevice,
        "primary": bool(mi.dwFlags & 1),
        "w": r.right - r.left,
        "h": r.bottom - r.top,
    }


def dpi_to_percent(dpi):
    if dpi is None:
        return None
    return int(round(dpi / 96 * 100))


# ---------- Смена DPI через UIA + PowerShell ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SET_DPI_PS = os.path.join(SCRIPT_DIR, "set_dpi.ps1")


def set_dpi(percent: int) -> tuple[bool, str]:
    """
    Реально меняет системный DPI на `percent` через UIA.
    Returns (success, message).
    """
    if not os.path.exists(SET_DPI_PS):
        return False, f"PS-скрипт не найден: {SET_DPI_PS}"
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", SET_DPI_PS, "-Percent", str(percent)],
            capture_output=True, text=True, timeout=20,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
        out = (res.stdout or "").strip()
        if res.returncode == 0 and "OK" in out:
            return True, out
        return False, out or f"PowerShell exit {res.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Таймаут UIA-скрипта"
    except Exception as e:
        return False, str(e)


# ---------- GUI ----------
class DpiLens(tk.Tk):
    REFRESH_MS = 1000
    BG = "#1e1e2e"
    SURFACE = "#313244"
    FG = "#cdd6f4"
    FG_DIM = "#a6adc8"
    ACCENT = "#fab387"
    SUCCESS = "#a6e3a1"
    DANGER = "#f38ba8"

    def __init__(self):
        super().__init__()
        self.title("DpiLens — DPI-лупа")
        self.geometry("440x420")
        self.resizable(False, False)
        self.configure(bg=self.BG)
        self.attributes("-topmost", True)
        self.after(500, lambda: self.attributes("-topmost", False))

        # Заголовок
        tk.Label(
            self, text="🔍  DpiLens",
            font=("Segoe UI", 18, "bold"),
            bg=self.BG, fg=self.FG,
        ).pack(pady=(18, 2))
        tk.Label(
            self, text="DPI-скейл монитора под курсором",
            font=("Segoe UI", 9), bg=self.BG, fg=self.FG_DIM,
        ).pack(pady=(0, 12))

        # Карточка: монитор
        mon_card = tk.Frame(self, bg=self.SURFACE)
        mon_card.pack(fill="x", padx=20, pady=4)
        tk.Label(
            mon_card, text="Монитор",
            font=("Segoe UI", 9, "bold"),
            bg=self.SURFACE, fg=self.FG_DIM, anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 0))
        self.mon_label = tk.Label(
            mon_card, text="—",
            font=("Consolas", 10),
            bg=self.SURFACE, fg=self.FG, anchor="w",
        )
        self.mon_label.pack(fill="x", padx=12, pady=(0, 8))

        # Карточка: DPI
        dpi_card = tk.Frame(self, bg=self.SURFACE)
        dpi_card.pack(fill="x", padx=20, pady=4)
        tk.Label(
            dpi_card, text="Масштаб",
            font=("Segoe UI", 9, "bold"),
            bg=self.SURFACE, fg=self.FG_DIM, anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 0))
        self.dpi_label = tk.Label(
            dpi_card, text="—",
            font=("Segoe UI", 22, "bold"),
            bg=self.SURFACE, fg=self.ACCENT, anchor="w",
        )
        self.dpi_label.pack(fill="x", padx=12, pady=(0, 8))

        # Кнопки масштаба
        tk.Label(
            self, text="Установить масштаб:",
            font=("Segoe UI", 9, "bold"),
            bg=self.BG, fg=self.FG_DIM, anchor="w",
        ).pack(fill="x", padx=20, pady=(10, 4))

        btn_row = tk.Frame(self, bg=self.BG)
        btn_row.pack(fill="x", padx=20, pady=2)
        for pct in (100, 125, 150, 175, 200):
            tk.Button(
                btn_row, text=f"{pct}%",
                command=lambda p=pct: self.apply(p),
                bg=self.SURFACE, fg=self.FG,
                activebackground=self.ACCENT, activeforeground="#1e1e2e",
                font=("Segoe UI", 10, "bold"),
                bd=0, relief="flat", padx=8, pady=6, cursor="hand2",
            ).pack(side="left", expand=True, fill="x", padx=2)

        # Статус
        self.status = tk.Label(
            self, text="", bg=self.BG, fg=self.FG_DIM,
            font=("Segoe UI", 9), wraplength=400, justify="center",
        )
        self.status.pack(side="bottom", pady=8)

        if not HAS_SHCORE:
            self.status.config(
                text="shcore.dll не найден — используется GDI fallback",
                fg=self.DANGER,
            )

        self.refresh()
        self.after(self.REFRESH_MS, self.auto_refresh)

    def auto_refresh(self):
        self.refresh()
        self.after(self.REFRESH_MS, self.auto_refresh)

    def refresh(self):
        hm = monitor_under_cursor()
        if not hm:
            self.mon_label.config(text="(не удалось определить)")
            self.dpi_label.config(text="—")
            return

        info = monitor_info(hm)
        dpi = get_dpi_for(hm)
        pct = dpi_to_percent(dpi)

        if info:
            primary = " ★" if info["primary"] else ""
            self.mon_label.config(
                text=f"{info['device']}{primary}  {info['w']}x{info['h']}"
            )
        else:
            self.mon_label.config(text="(нет данных)")

        if pct is None:
            self.dpi_label.config(text="N/A")
        else:
            self.dpi_label.config(text=f"{pct}%   (DPI {dpi})")

    def apply(self, percent: int) -> None:
        self.status.config(text=f"Ставлю {percent}%…", fg=self.FG_DIM)
        self.update_idletasks()
        ok, msg = set_dpi(percent)
        if ok:
            self.status.config(
                text=f"✅ {percent}% применено. {msg.splitlines()[-1] if msg else ''}".strip(),
                fg=self.SUCCESS,
            )
            self.refresh()
        else:
            self.status.config(
                text=f"❌ Ошибка: {msg[:200]}",
                fg=self.DANGER,
            )


if __name__ == "__main__":
    DpiLens().mainloop()
