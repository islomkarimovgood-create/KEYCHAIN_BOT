"""
preview.py
Generates a 2D PNG preview of the keychain using Pillow.
Looks like: black rounded plate + coloured text + ring hole.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path("/usr/share/fonts/keychain")
PREVIEW_DIR = Path("/tmp/previews")

# Палитра берётся из colors.py — один источник правды
try:
    from colors import COLOR_MAP
except Exception:
    COLOR_MAP = {
        "Black": (24, 24, 24), "White": (245, 245, 245), "Gray": (128, 128, 128),
    }

FONT_FILES = {
    # Кириллица + латиница
    "Pacifico":       "Pacifico-Regular.ttf",
    "Lobster":        "Lobster-Regular.ttf",
    "Russo One":      "RussoOne-Regular.ttf",
    "Yeseva One":     "YesevaOne-Regular.ttf",
    "Neucha":         "Neucha.ttf",
    "Play":           "Play-Bold.ttf",
    "Comfortaa":      "Comfortaa-Bold.ttf",
    "Ruslan Display": "RuslanDisplay.ttf",
    # Только латиница
    "Cookie":         "Cookie-Regular.ttf",
    "Courgette":      "Courgette-Regular.ttf",
    "Bangers":        "Bangers-Regular.ttf",
    "Satisfy":        "Satisfy-Regular.ttf",
    "Righteous":      "Righteous-Regular.ttf",
    "Dancing Script": "DancingScript-Bold.ttf",
}


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, r, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.ellipse([x0,      y0,      x0 + 2*r, y0 + 2*r], fill=fill)
    draw.ellipse([x1 - 2*r, y0,      x1,       y0 + 2*r], fill=fill)
    draw.ellipse([x0,      y1 - 2*r, x0 + 2*r, y1      ], fill=fill)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1,       y1      ], fill=fill)


def generate_preview(
    name: str,
    font_name: str,
    text_color: str,
    back_color: str,
) -> str:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    bg_rgb  = COLOR_MAP.get(back_color, (25, 25, 25))
    txt_rgb = COLOR_MAP.get(text_color, (255, 140, 175))

    # Load font (fall back to default if file missing)
    font_file = FONT_DIR / FONT_FILES.get(font_name, "Pacifico-Regular.ttf")
    pil_font = None
    for candidate in (font_file, FONT_DIR / "Pacifico-Regular.ttf",
                      FONT_DIR / "Lobster-Regular.ttf"):
        try:
            pil_font = ImageFont.truetype(str(candidate), 72)
            break
        except Exception:
            continue
    if pil_font is None:
        pil_font = ImageFont.load_default()

    # Measure text
    tmp = Image.new("RGB", (1, 1))
    bbox = ImageDraw.Draw(tmp).textbbox((0, 0), name, font=pil_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Canvas layout
    pad     = 40
    hole_w  = 56   # space for the ring on the left
    img_w   = tw + pad * 2 + hole_w
    img_h   = th + pad * 2

    canvas_color = (220, 220, 220)   # neutral grey background
    img  = Image.new("RGB", (img_w, img_h), canvas_color)
    draw = ImageDraw.Draw(img)

    # Drop shadow
    _rounded_rect(draw, [hole_w + 4, 4, img_w - 1, img_h - 1], 22, (90, 90, 90))

    # Back plate
    _rounded_rect(draw, [hole_w, 0, img_w - 5, img_h - 5], 22, bg_rgb)

    # Ring connector (small stem + circle)
    stem_x = hole_w - 10
    mid_y  = img_h // 2
    draw.rectangle([stem_x, mid_y - 5, hole_w, mid_y + 5], fill=bg_rgb)

    ring_cx, ring_cy, ring_r = hole_w - 26, mid_y, 18
    # Outer ring
    draw.ellipse(
        [ring_cx - ring_r, ring_cy - ring_r, ring_cx + ring_r, ring_cy + ring_r],
        outline=bg_rgb, width=6, fill=canvas_color,
    )
    # Inner hole
    draw.ellipse(
        [ring_cx - 8, ring_cy - 8, ring_cx + 8, ring_cy + 8],
        fill=(190, 190, 190),
    )

    # Text shadow
    sx = hole_w + pad - bbox[0]
    sy = (img_h - th) // 2 - bbox[1]
    shadow = tuple(max(0, c - 55) for c in bg_rgb)
    draw.text((sx + 3, sy + 3), name, font=pil_font, fill=shadow)

    # Main text
    draw.text((sx, sy), name, font=pil_font, fill=txt_rgb)

    safe = "".join(c for c in name if c.isalnum() or c in "-_")[:15] or "keychain"
    out  = PREVIEW_DIR / f"{safe}_preview.png"
    img.save(str(out))
    return str(out)
