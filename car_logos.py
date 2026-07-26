"""
car_logos.py
Список марок авто и загрузка их SVG-эмблем во время сборки Docker.
Источник: Simple Icons (CC0) — https://simpleicons.org
"""

# (Отображаемое имя, slug в Simple Icons)
CAR_BRANDS = [
    ("BMW",            "bmw"),
    ("Mercedes-Benz",  "mercedes"),
    ("Audi",           "audi"),
    ("Volkswagen",     "volkswagen"),
    ("Porsche",        "porsche"),
    ("Opel",           "opel"),
    ("Toyota",         "toyota"),
    ("Honda",          "honda"),
    ("Nissan",         "nissan"),
    ("Mazda",          "mazda"),
    ("Mitsubishi",     "mitsubishi"),
    ("Subaru",         "subaru"),
    ("Suzuki",         "suzuki"),
    ("Lexus",          "lexus"),
    ("Infiniti",       "infiniti"),
    ("Acura",          "acura"),
    ("Hyundai",        "hyundai"),
    ("Kia",            "kia"),
    ("Genesis",        "genesis"),
    ("Ssangyong",      "ssangyong"),
    ("Ford",           "ford"),
    ("Chevrolet",      "chevrolet"),
    ("Jeep",           "jeep"),
    ("Dodge",          "dodge"),
    ("Cadillac",       "cadillac"),
    ("Chrysler",       "chrysler"),
    ("Tesla",          "tesla"),
    ("GMC",            "gmc"),
    ("Lincoln",        "lincoln"),
    ("Buick",          "buick"),
    ("Ferrari",        "ferrari"),
    ("Lamborghini",    "lamborghini"),
    ("Maserati",       "maserati"),
    ("Alfa Romeo",     "alfaromeo"),
    ("Fiat",           "fiat"),
    ("Lancia",         "lancia"),
    ("Bugatti",        "bugatti"),
    ("Aston Martin",   "astonmartin"),
    ("Bentley",        "bentley"),
    ("Rolls-Royce",    "rollsroyce"),
    ("Jaguar",         "jaguar"),
    ("Land Rover",     "landrover"),
    ("MINI",           "mini"),
    ("Lotus",          "lotuscars"),
    ("McLaren",        "mclaren"),
    ("Peugeot",        "peugeot"),
    ("Renault",        "renault"),
    ("Citroen",        "citroen"),
    ("DS",             "dsautomobiles"),
    ("Volvo",          "volvo"),
    ("Skoda",          "skoda"),
    ("SEAT",           "seat"),
    ("Dacia",          "dacia"),
    ("Chery",          "chery"),
    ("Haval",          "haval"),
    ("BYD",            "byd"),
    ("Geely",          "geely"),
    ("Great Wall",     "greatwallmotors"),
    ("Lada",           "lada"),
    ("UAZ",            "uaz"),
]

import os as _os

# Основная папка (заполняется при сборке Docker) и запасная (рантайм)
BUILD_DIR   = "/usr/share/carlogos"
RUNTIME_DIR = "/tmp/carlogos"
LOGO_DIR    = BUILD_DIR



# Запасные варианты имён в наборе иконок (у некоторых марок slug отличается)
ALT_SLUGS = {
    "lexus":           ["lexus", "lexusinternational"],
    "genesis":         ["genesis", "genesismotor", "genesismotors"],
    "ssangyong":       ["ssangyong", "ssangyongmotor", "kgmobility"],
    "dodge":           ["dodge", "dodgeofficial"],
    "gmc":             ["gmc", "generalmotors"],
    "lincoln":         ["lincoln", "lincolnmotorcompany"],
    "buick":           ["buick", "buickmotor"],
    "lancia":          ["lancia", "lanciaofficial"],
    "lotuscars":       ["lotuscars", "lotus", "grouplotus"],
    "chery":           ["chery", "cheryauto", "cheryautomobile"],
    "haval":           ["haval", "havalauto"],
    "byd":             ["byd", "bydauto", "bydcompany"],
    "geely":           ["geely", "geelyauto", "geelyautomobile"],
    "greatwallmotors": ["greatwallmotors", "greatwall", "gwm"],
    "uaz":             ["uaz", "uazofficial"],
}

# Второй источник: набор логотипов в PNG. Превращаем в контур через potrace.
PNG_SOURCES = [
    "https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/optimized/{slug}.png",
    "https://raw.githubusercontent.com/filippofilip95/car-logos-dataset/master/logos/original/{slug}.png",
]

# Имена файлов во втором наборе отличаются от наших slug
PNG_NAMES = {
    "mercedes":        "mercedes-benz",
    "volkswagen":      "volkswagen",
    "alfaromeo":       "alfa-romeo",
    "astonmartin":     "aston-martin",
    "rollsroyce":      "rolls-royce",
    "landrover":       "land-rover",
    "lotuscars":       "lotus",
    "greatwallmotors": "great-wall",
    "dsautomobiles":   "ds",
    "mini":            "mini",
    "gmc":             "gmc",
}


def _png_name(slug: str) -> str:
    return PNG_NAMES.get(slug, slug)


def _png_to_svg(png_bytes: bytes, out_svg: str) -> bool:
    """PNG -> контур SVG через potrace. True если получилось."""
    import io, subprocess, os
    try:
        from PIL import Image, ImageOps
    except Exception:
        return False

    try:
        img = Image.open(io.BytesIO(png_bytes))

        # Прозрачный фон делаем белым
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            img = Image.alpha_composite(bg, img)

        img = img.convert("L")
        if max(img.size) > 700:
            k = 700 / max(img.size)
            img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)

        img = ImageOps.autocontrast(img)
        bw = img.point(lambda v: 255 if v > 140 else 0, mode="1")

        # Проверяем, что рисунок не пустой
        px = list(bw.getdata())
        ratio = sum(1 for v in px if v == 0) / max(1, len(px))
        if ratio < 0.01 or ratio > 0.95:
            return False

        pbm = out_svg.replace(".svg", ".pbm")
        bw.save(pbm)
        r = subprocess.run(
            ["potrace", pbm, "-s", "-o", out_svg,
             "--turdsize", "3", "--alphamax", "1.0"],
            capture_output=True, timeout=60,
        )
        try:
            os.remove(pbm)
        except Exception:
            pass

        return r.returncode == 0 and os.path.exists(out_svg) and os.path.getsize(out_svg) > 200
    except Exception:
        return False


def _writable_dir():
    """Возвращает папку, в которую реально можно писать."""
    for d in (BUILD_DIR, RUNTIME_DIR):
        try:
            _os.makedirs(d, exist_ok=True)
            test = _os.path.join(d, ".w")
            with open(test, "w") as f:
                f.write("1")
            _os.remove(test)
            return d
        except Exception:
            continue
    return RUNTIME_DIR


def slug_to_file(slug: str) -> str:
    """Ищет эмблему в обеих папках."""
    for d in (BUILD_DIR, RUNTIME_DIR):
        path = f"{d}/{slug}.svg"
        if _os.path.exists(path):
            return path
    return f"{BUILD_DIR}/{slug}.svg"


def count_downloaded() -> int:
    import glob
    found = set()
    for d in (BUILD_DIR, RUNTIME_DIR):
        for f in glob.glob(f"{d}/*.svg"):
            found.add(_os.path.basename(f))
    return len(found)


def downloaded_slugs():
    import glob
    found = set()
    for d in (BUILD_DIR, RUNTIME_DIR):
        for f in glob.glob(f"{d}/*.svg"):
            found.add(_os.path.splitext(_os.path.basename(f))[0])
    return sorted(found)


def download_all():
    """Вызывается в Dockerfile. Пропускает недоступные эмблемы."""
    import os, time, urllib.request
    target_dir = _writable_dir()
    os.makedirs(target_dir, exist_ok=True)

    bases = [
        "https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg",
        "https://cdn.jsdelivr.net/npm/simple-icons@11/icons/{slug}.svg",
        "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/{slug}.svg",
        "https://unpkg.com/simple-icons@13/icons/{slug}.svg",
        "https://unpkg.com/simple-icons@11/icons/{slug}.svg",
        "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{slug}.svg",
        "https://fastly.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg",
    ]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; logo-fetch/1.0)"}

    ok, fail, failed_names = 0, 0, []

    for name, slug in CAR_BRANDS:
        # Уже скачано раньше — пропускаем
        existing = slug_to_file(slug)
        if os.path.exists(existing) and os.path.getsize(existing) > 100:
            ok += 1
            continue

        target = os.path.join(target_dir, f"{slug}.svg")
        got = False

        # ── Источник 1: векторные иконки (пробуем все варианты имени) ──────
        for candidate in ALT_SLUGS.get(slug, [slug]):
            for base in bases:
                url = base.format(slug=candidate)
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=25) as r:
                        data = r.read()
                    if len(data) < 100 or b"<svg" not in data[:400]:
                        continue
                    with open(target, "wb") as f:
                        f.write(data)
                    print(f"  OK   {name:16s} SVG ({len(data)} B)", flush=True)
                    ok += 1
                    got = True
                    time.sleep(0.15)
                    break
                except Exception:
                    continue
            if got:
                break

        # ── Источник 2: растровые логотипы -> контур через potrace ─────────
        if not got:
            png_slug = _png_name(slug)
            for base in PNG_SOURCES:
                url = base.format(slug=png_slug)
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=30) as r:
                        png = r.read()
                    if len(png) < 500:
                        continue
                    if _png_to_svg(png, target):
                        print(f"  OK   {name:16s} PNG->SVG ({len(png)} B)", flush=True)
                        ok += 1
                        got = True
                        time.sleep(0.15)
                        break
                except Exception:
                    continue

        if not got:
            print(f"  SKIP {name}", flush=True)
            fail += 1
            failed_names.append(slug)

    with open(os.path.join(target_dir, "available.txt"), "w", encoding="utf-8") as f:
        for name, slug in CAR_BRANDS:
            if slug not in failed_names:
                f.write(f"{name}|{slug}\n")

    with open(os.path.join(target_dir, "download.log"), "w", encoding="utf-8") as f:
        f.write(f"Скачано: {ok} из {len(CAR_BRANDS)}\n")
        if failed_names:
            f.write("Не удалось: " + ", ".join(failed_names) + "\n")

    print(f"\nЭмблемы: {ok} скачано, {fail} пропущено.", flush=True)
    if ok == 0:
        print("ВНИМАНИЕ: ни одной эмблемы. Бот будет делать текстовые брелоки.", flush=True)


def load_available():
    """Возвращает [(имя, slug), ...] — только те марки, чей SVG реально есть."""
    have = set(downloaded_slugs())
    if not have:
        return []
    return [(name, slug) for name, slug in CAR_BRANDS if slug in have]


if __name__ == "__main__":
    download_all()
