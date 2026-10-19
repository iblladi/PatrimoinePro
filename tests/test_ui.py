"""Test de fumée de l'interface : construit chaque widget puis chaque écran."""
from __future__ import annotations

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import tkinter as tk  # noqa: E402

from app import theme, utils, widgets  # noqa: E402
from app.db import Database  # noqa: E402

FAILED = []


def check(label, condition, detail=""):
    if condition:
        print(f"  OK   {label}")
    else:
        print(f"  FAIL {label} {detail}")
        FAILED.append(label)


def pump(root, n=3):
    for _ in range(n):
        root.update_idletasks()
        root.update()


def main():
    workdir = os.path.join(ROOT, ".tmp")
    os.makedirs(workdir, exist_ok=True)
    path = os.path.join(workdir, "ui.db")
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except OSError:
            pass
    db = Database(path)
    db.seed_demo()

    root = tk.Tk()
    root.geometry("1360x900+40+20")
    theme.setup(root)
    root.title("Smoke test")
    root.configure(bg=theme.BG)

    try:
        print("· widgets")
        frame = tk.Frame(root, bg=theme.BG)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        card = widgets.Card(frame, title="Carte de test", subtitle="Sous-titre")
        card.pack(fill="x")
        widgets.lbl(card.content, "Contenu", bg=theme.SURFACE).pack(anchor="w")

        row = tk.Frame(frame, bg=theme.BG)
        row.pack(fill="x", pady=10)
        for variant in ("primary", "secondary", "ghost", "subtle", "danger"):
            b = widgets.Button(row, f"Bouton {variant}", lambda: None, variant=variant)
            b.pack(side="left", padx=4)

        kpi = widgets.KpiCard(frame, "Patrimoine net", "40 195 €", "+1 200 € ce mois", "blue")
        kpi.pack(fill="x", pady=6)

        pb = widgets.ProgressBar(frame, height=10)
        pb.pack(fill="x", pady=6)
        pb.set(0.62)

        seg = widgets.Segmented(frame, ["Mois", "3 mois", "12 mois", "Tout"], "Mois")
        seg.pack(anchor="w", pady=6)

        df = widgets.DateField(frame)
        df.pack(anchor="w", pady=6)
        check("date lue", df.get() == utils.today(), str(df.get()))

        lc = widgets.LineChart(frame, height=180)
        lc.pack(fill="x", pady=6)
        lc.set_data([("janv.", 1000), ("févr.", 1400), ("mars", 1200), ("avr.", 1900)])

        bars = widgets.BarsChart(frame, height=160)
        bars.pack(fill="x", pady=6)
        bars.set_data([("janv.", [(2000, theme.GREEN), (1500, theme.RED)]),
                       ("févr.", [(2100, theme.GREEN), (1700, theme.RED)])])

        donut = widgets.DonutChart(frame, size=160)
        donut.pack(anchor="w", pady=6)
        donut.set_data([(4000, theme.PRIMARY, "A"), (2000, theme.GREEN, "B")])

        chips = tk.Frame(frame, bg=theme.BG)
        chips.pack(anchor="w", pady=6)
        widgets.Chip(chips, "Objectif atteint", theme.GREEN_DARK, theme.GREEN_SOFT).pack(side="left")
        widgets.Dot(chips, theme.VIOLET).pack(side="left", padx=6)
        widgets.ColorPicker(chips, theme.PRIMARY).pack(side="left", padx=6)

        sf = widgets.ScrollFrame(frame)
        sf.pack(fill="both", expand=True, pady=6)
        for i in range(20):
            widgets.lbl(sf.body, f"Ligne {i}", bg=theme.BG).pack(anchor="w")

        pump(root)
        check("fenêtre dimensionnée", root.winfo_width() > 800, str(root.winfo_width()))
        check("canvas courbe", len(lc.find_all()) > 5, str(len(lc.find_all())))
        check("canvas donut", len(donut.find_all()) >= 3, str(len(donut.find_all())))
        check("canvas barres", len(bars.find_all()) > 5, str(len(bars.find_all())))
        check("boutons dessinés", len(b.find_all()) > 0)

        # dialogues
        print("· dialogues")
        dlg = widgets.Modal(root, "Dialogue de test", "Sous-titre", width=420, ok_label="Valider")
        widgets.lbl(dlg.body, "Corps", bg=theme.BG).pack(anchor="w")
        dlg.center()
        dlg.deiconify()
        pump(root)
        check("modale visible", dlg.winfo_exists())
        dlg.destroy()

        widgets.Toast.show(root, "Test de notification")
        pump(root)

        print("· écrans")
        from app.main import App
        app_root = App(db=db)
        app_root.update()
        for key in ("dashboard", "accounts", "transactions", "projects", "budgets", "settings"):
            app_root.navigate(key)
            pump(app_root)
            view = app_root.views[key]
            check(f"écran {key}", len(view.winfo_children()) > 0)
        app_root.destroy()

    finally:
        try:
            root.destroy()
        except Exception:
            pass

    print()
    if FAILED:
        print(f"ÉCHECS : {len(FAILED)} -> {FAILED}")
        return 1
    print("Interface : aucun plantage détecté.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
