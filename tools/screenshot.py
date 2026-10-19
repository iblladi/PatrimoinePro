"""Capture PNG des Ã©crans de PatrimoinePro (GDI + PrintWindow), sans dÃ©pendance externe.

Usage :
    python tools/screenshot.py [--db chemin] [--out dossier] [--pages dashboard,accounts,...]
"""
from __future__ import annotations

import argparse
import ctypes
import os
import struct
import sys
import time
import zlib
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

GA_ROOT = 2
SRCCOPY = 0x00CC0020
PW_CLIENTONLY = 1
PW_RENDERFULLCONTENT = 2
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path: str, width: int, height: int, bgra: bytes) -> None:
    rows = []
    stride = width * 4
    for y in range(height):
        line = bgra[y * stride:(y + 1) * stride]
        rgba = bytearray(stride)
        rgba[0::4] = line[2::4]
        rgba[1::4] = line[1::4]
        rgba[2::4] = line[0::4]
        rgba[3::4] = b"\xff" * width
        rows.append(b"\x00" + bytes(rgba))
    raw = b"".join(rows)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw, 6))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)


def _grab(hwnd, width, height, from_screen=False):
    hdc_window = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    bitmap = gdi32.CreateCompatibleBitmap(hdc_window, width, height)
    gdi32.SelectObject(hdc_mem, bitmap)
    ok = False
    if not from_screen:
        ok = bool(user32.PrintWindow(hwnd, hdc_mem, PW_CLIENTONLY | PW_RENDERFULLCONTENT))
    if not ok:
        gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_window, 0, 0, SRCCOPY)

    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0
    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(hdc_mem, bitmap, 0, height, buffer, ctypes.byref(info), DIB_RGB_COLORS)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_window)
    return buffer.raw


def capture(app, path: str):
    app.update_idletasks()
    app.update()
    hwnd = user32.GetAncestor(app.winfo_id(), GA_ROOT)
    if not hwnd:
        hwnd = app.winfo_id()
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    data = _grab(hwnd, width, height, from_screen=False)
    write_png(path, width, height, data)
    return width, height


def pump(app, seconds=0.35):
    end = time.time() + seconds
    while time.time() < end:
        app.update_idletasks()
        app.update()
        time.sleep(0.02)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.path.join(ROOT, ".tmp", "demo.db"))
    parser.add_argument("--out", default=os.path.join(ROOT, ".tmp", "shots"))
    parser.add_argument("--pages", default="dashboard,accounts,transactions,projects,budgets,settings")
    parser.add_argument("--dialogs", default="")
    parser.add_argument("--height", type=int, default=860)
    args = parser.parse_args()

    from app.db import Database
    from app.main import App

    db = Database(args.db)
    if db.is_empty():
        db.seed_demo()
    os.makedirs(args.out, exist_ok=True)

    app = App(db=db)
    app.geometry(f"1300x{args.height}+60+40")
    pump(app, 0.6)

    for page in [p for p in args.pages.split(",") if p]:
        app.navigate(page)
        pump(app, 0.5)
        path = os.path.join(args.out, f"{page}.png")
        w, h = capture(app, path)
        print(f"SHOT {page}: {w}x{h} -> {path}")

    for name in [d for d in args.dialogs.split(",") if d]:
        try:
            if name == "transaction":
                from app import dialogs as dlg_mod
                dlg = dlg_mod.TransactionDialog(app, db)
            elif name == "account":
                from app import dialogs as dlg_mod
                dlg = dlg_mod.AccountDialog(app)
            elif name == "project":
                from app import dialogs as dlg_mod
                dlg = dlg_mod.ProjectDialog(app, db)
            elif name == "contribution":
                from app import dialogs as dlg_mod
                dlg = dlg_mod.ContributionDialog(app, db, db.list_projects()[0])
            else:
                continue
            dlg.center()
            dlg.deiconify()
            pump(app, 0.5)
            path = os.path.join(args.out, f"dialog-{name}.png")
            w, h = capture(dlg, path)
            print(f"SHOT dialog-{name}: {w}x{h} -> {path}")
            dlg.destroy()
        except Exception as exc:  # pragma: no cover
            print(f"ERR dialog {name}: {exc}")

    app.destroy()


if __name__ == "__main__":
    main()

