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
        for base in bases:
            url = base.format(slug=slug)
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=25) as r:
                    data = r.read()
                if len(data) < 100 or b"<svg" not in data[:400]:
                    continue
                with open(target, "wb") as f:
                    f.write(data)
                print(f"  OK   {name:16s} ({len(data)} B)", flush=True)
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

    # Сохраняем список успешно скачанных — бот покажет только их
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
