"""Gera o fundo da janela do .dmg (seta "arraste para Aplicativos"), em 1x e 2x num único .tiff.

Uso (macOS, requer Pillow): python icon/make_dmg_background.py
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
APP = "Psiu"
ACCENT = (120, 90, 230)
WIDTH, HEIGHT = 640, 400
# Posições dos ícones (centro), as mesmas de dmg_settings.py
APP_X, APPS_X, ICON_Y = 170, 470, 190


def draw(scale):
    w, h = WIDTH * scale, HEIGHT * scale
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    top, bottom = (252, 248, 242), (240, 232, 220)
    for y in range(h):
        k = y / h
        d.line((0, y, w, y), fill=tuple(round(a + (b - a) * k) for a, b in zip(top, bottom)))

    # Seta entre os dois ícones
    y = ICON_Y * scale
    x0, x1 = (APP_X + 75) * scale, (APPS_X - 75) * scale
    d.line((x0, y, x1 - 14 * scale, y), fill=ACCENT, width=6 * scale)
    d.polygon([(x1, y), (x1 - 24 * scale, y - 16 * scale), (x1 - 24 * scale, y + 16 * scale)], fill=ACCENT)

    font = ImageFont.load_default(size=20 * scale)
    small = ImageFont.load_default(size=15 * scale)
    d.text((w / 2, 318 * scale), f"Drag {APP} to Applications", fill=(60, 50, 40), font=font, anchor="mm")
    d.text((w / 2, 346 * scale), f"Arraste o {APP} para Aplicativos", fill=(120, 105, 90), font=small, anchor="mm")
    return img


def main():
    one, two = HERE / "dmg-background.png", HERE / "dmg-background@2x.png"
    draw(1).save(one)
    draw(2).save(two)
    # .tiff com as duas resoluções: o Finder usa a 2x em telas Retina.
    subprocess.run(["tiffutil", "-cathidpicheck", str(one), str(two), "-out", str(HERE / "dmg-background.tiff")],
                   check=True, capture_output=True)
    one.unlink()
    two.unlink()


if __name__ == "__main__":
    main()
