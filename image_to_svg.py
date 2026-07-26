"""
image_to_svg.py
Превращает загруженную клиентом картинку (PNG/JPG) в SVG-контур,
пригодный для выдавливания в OpenSCAD.
Пайплайн: изображение -> ч/б -> PBM -> potrace -> SVG
"""

import subprocess
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter


def image_to_svg(src_path, out_svg, max_size=600, threshold=None, invert=False):
    """
    Возвращает путь к SVG. Бросает исключение с понятным текстом при неудаче.
    """
    src_path = Path(src_path)
    out_svg = Path(out_svg)
    out_svg.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(src_path)

    # Прозрачный фон -> белый
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)

    img = img.convert("L")

    # Уменьшаем — быстрее и чище контур
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize(
            (max(1, int(img.width * ratio)), max(1, int(img.height * ratio))),
            Image.LANCZOS,
        )

    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Порог: по среднему, если не задан явно
    if threshold is None:
        hist = img.histogram()
        total = sum(hist)
        acc, median = 0, 128
        for i, c in enumerate(hist):
            acc += c
            if acc >= total / 2:
                median = i
                break
        threshold = max(60, min(200, median))

    bw = img.point(lambda p: 255 if p > threshold else 0, mode="1")

    if invert:
        bw = ImageOps.invert(bw.convert("L")).convert("1")

    # Проверяем, что рисунок вообще есть
    px = list(bw.getdata())
    black_ratio = sum(1 for v in px if v == 0) / max(1, len(px))
    if black_ratio < 0.005:
        raise ValueError(
            "На картинке почти нет тёмных областей — "
            "пришлите контрастный чёрно-белый логотип"
        )
    if black_ratio > 0.95:
        raise ValueError(
            "Картинка почти полностью тёмная — "
            "пришлите логотип на светлом фоне"
        )

    pbm_path = out_svg.with_suffix(".pbm")
    bw.save(pbm_path)

    # potrace: PBM -> SVG
    cmd = [
        "potrace", str(pbm_path),
        "-s",                    # формат SVG
        "-o", str(out_svg),
        "--turdsize", "4",       # убрать мелкий мусор
        "--alphamax", "1.0",     # сглаживание углов
        "--opttolerance", "0.4",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)

    try:
        pbm_path.unlink(missing_ok=True)
    except Exception:
        pass

    if result.returncode != 0:
        raise RuntimeError(
            "potrace не смог обработать картинку: "
            + result.stderr.decode(errors="replace")[-300:]
        )
    if not out_svg.exists() or out_svg.stat().st_size < 200:
        raise RuntimeError("SVG получился пустым — попробуйте другое изображение")

    return str(out_svg)
