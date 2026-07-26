"""
colors.py
Простая палитра — по одному чистому цвету, без оттенков.
У всех кнопок одинаковый эмодзи.
"""

EMOJI = "🎨"

PALETTE = {
    f"{EMOJI} Чёрный":     ("Black",     (24, 24, 24)),
    f"{EMOJI} Белый":      ("White",     (245, 245, 245)),
    f"{EMOJI} Серый":      ("Gray",      (128, 128, 128)),
    f"{EMOJI} Красный":    ("Red",       (214, 40, 40)),
    f"{EMOJI} Оранжевый":  ("Orange",    (255, 130, 20)),
    f"{EMOJI} Жёлтый":     ("Yellow",    (255, 205, 0)),
    f"{EMOJI} Зелёный":    ("Green",     (48, 168, 76)),
    f"{EMOJI} Голубой":    ("Turquoise", (60, 195, 215)),
    f"{EMOJI} Синий":      ("Blue",      (44, 96, 205)),
    f"{EMOJI} Фиолетовый": ("Purple",    (150, 76, 200)),
    f"{EMOJI} Розовый":    ("Pink",      (255, 140, 175)),
    f"{EMOJI} Коричневый": ("Brown",     (118, 76, 48)),
    f"{EMOJI} Золотой":    ("Gold",      (198, 160, 68)),
    f"{EMOJI} Серебряный": ("Silver",    (186, 190, 196)),
}

COLOR_MAP = {v[0]: v[1] for v in PALETTE.values()}


def color_name(label: str, default: str = "Black") -> str:
    entry = PALETTE.get(label)
    return entry[0] if entry else default


def color_rgb(name: str, default=(24, 24, 24)):
    return COLOR_MAP.get(name, default)


def labels():
    return list(PALETTE.keys())


def page(index: int, per_page: int = 14):
    all_labels = labels()
    total = max(1, (len(all_labels) + per_page - 1) // per_page)
    index = max(0, min(index, total - 1))
    return all_labels[index * per_page:(index + 1) * per_page], total
