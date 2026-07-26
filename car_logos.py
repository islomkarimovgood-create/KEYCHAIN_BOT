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

LOGO_DIR = "/usr/share/carlogos"


def slug_to_file(slug: str) -> str:
    return f"{LOGO_DIR}/{slug}.svg"


def download_all():
    """Вызывается в Dockerfile. Пропускает недоступные эмблемы."""
    import os, time, urllib.request
    os.makedirs(LOGO_DIR, exist_ok=True)

    bases = [
        "https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg",
        "https://unpkg.com/simple-icons@13/icons/{slug}.svg",
        "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{slug}.svg",
    ]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; logo-fetch/1.0)"}

    ok, fail, failed_names = 0, 0, []
    for name, slug in CAR_BRANDS:
        target = slug_to_file(slug)
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
    with open(f"{LOGO_DIR}/available.txt", "w", encoding="utf-8") as f:
        for name, slug in CAR_BRANDS:
            if slug not in failed_names:
                f.write(f"{name}|{slug}\n")

    print(f"\nЭмблемы: {ok} скачано, {fail} пропущено.", flush=True)


def load_available():
    """Читается ботом при старте. Возвращает [(имя, slug), ...]."""
    import os
    path = f"{LOGO_DIR}/available.txt"
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "|" in line:
                name, slug = line.split("|", 1)
                out.append((name, slug))
    return out


if __name__ == "__main__":
    download_all()
