"""Génère assets/icon.ico (icône de l'application) avec Pillow."""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets")
SIZE = 1024
TOP = (59, 130, 246)      # #3B82F6
BOTTOM = (29, 78, 216)    # #1D4ED8


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # fond dégradé
    for y in range(SIZE):
        draw.line([(0, y), (SIZE, y)], fill=lerp(TOP, BOTTOM, y / SIZE))

    # masque arrondi
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1],
                                           radius=int(SIZE * 0.23), fill=255)
    img.putalpha(mask)

    # reflet discret en haut
    # lettre P
    font = None
    for candidate in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"):
        if os.path.exists(candidate):
            font = ImageFont.truetype(candidate, int(SIZE * 0.62))
            break
    draw = ImageDraw.Draw(img)
    if font is not None:
        box = draw.textbbox((0, 0), "P", font=font)
        w, h = box[2] - box[0], box[3] - box[1]
        draw.text(((SIZE - w) / 2 - box[0], (SIZE - h) / 2 - box[1] - SIZE * 0.015),
                  "P", font=font, fill=(255, 255, 255, 255))
    else:  # secours
        draw.text((SIZE * 0.36, SIZE * 0.2), "P", fill=(255, 255, 255, 255))

    # petite courbe ascendante en bas à droite
    pts = [(0.60, 0.80), (0.685, 0.735), (0.755, 0.775), (0.845, 0.655)]
    draw.line([(x * SIZE, y * SIZE) for x, y in pts], fill=(255, 255, 255, 235),
              width=int(SIZE * 0.035), joint="curve")
    r = SIZE * 0.018
    for x, y in pts[1:]:
        draw.ellipse([x * SIZE - r, y * SIZE - r, x * SIZE + r, y * SIZE + r],
                     fill=(255, 255, 255, 255))

    ico_path = os.path.join(OUT_DIR, "icon.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    img.resize((256, 256), Image.LANCZOS).save(
        ico_path, format="ICO", sizes=[(s, s) for s in sizes]
    )
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT_DIR, "icon.png"))
    print("ICO", ico_path, os.path.getsize(ico_path))
    print("PNG", os.path.join(OUT_DIR, "icon.png"))


if __name__ == "__main__":
    main()
