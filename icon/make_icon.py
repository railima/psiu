"""Gera o ícone do app (onda sonora virando linhas de texto) em PNG, .icns (macOS) e .ico (Windows).

Uso (requer Pillow; no macOS também gera o .icns com iconutil):
    python icon/make_icon.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SCALE = 4  # desenha maior e reduz, para bordas suaves
SIZE = 1024 * SCALE


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def draw_icon():
    s = SCALE
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Fundo: "squircle" no grid de ícones do macOS (824 px de 1024, com margem para a sombra).
    margin, radius = 100 * s, 185 * s
    box = (margin, margin, SIZE - margin, SIZE - margin)

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (box[0], box[1] + 14 * s, box[2], box[3] + 14 * s), radius, fill=(0, 0, 0, 90))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(22 * s)))

    top, bottom = (92, 110, 255), (138, 63, 224)
    gradient = Image.new("RGBA", (SIZE, SIZE))
    gd = ImageDraw.Draw(gradient)
    for y in range(box[1], box[3]):
        gd.line((0, y, SIZE, y), fill=lerp(top, bottom, (y - box[1]) / (box[3] - box[1])))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius, fill=255)
    img.paste(gradient, (0, 0), mask)

    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    cy = 512 * s

    # Onda sonora à esquerda.
    bar_w, gap = 46 * s, 30 * s
    heights = [150, 300, 420, 260, 170]
    x = 205 * s
    for h in heights:
        h *= s
        d.rounded_rectangle((x, cy - h // 2, x + bar_w, cy + h // 2), bar_w // 2, fill=white)
        x += bar_w + gap

    # Linhas de texto à direita (a transcrição), com opacidade decrescente.
    x0 = x + 34 * s
    for i, (w, alpha) in enumerate([(210, 255), (160, 215), (190, 175)]):
        y = cy - 110 * s + i * 110 * s
        d.rounded_rectangle((x0, y - 23 * s, x0 + w * s, y + 23 * s), 23 * s, fill=(255, 255, 255, alpha))

    # Ponto vermelho de "gravando".
    r, c = 52 * s, (750 * s, 255 * s)
    d.ellipse((c[0] - r - 12 * s, c[1] - r - 12 * s, c[0] + r + 12 * s, c[1] + r + 12 * s), fill=white)
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(240, 68, 82, 255))

    return img.resize((1024, 1024), Image.LANCZOS)


def main():
    icon = draw_icon()
    icon.save(HERE / "icon.png")
    icon.resize((256, 256), Image.LANCZOS).save(HERE.parent / "ui" / "icon.png")
    icon.save(HERE / "Psiu.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    if sys.platform == "darwin":
        iconset = HERE / "Psiu.iconset"
        iconset.mkdir(exist_ok=True)
        for size in (16, 32, 128, 256, 512):
            icon.resize((size, size), Image.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
            icon.resize((size * 2, size * 2), Image.LANCZOS).save(iconset / f"icon_{size}x{size}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(HERE / "Psiu.icns")], check=True)
        shutil.rmtree(iconset)
    print("Ícones gerados em", HERE)


if __name__ == "__main__":
    main()
