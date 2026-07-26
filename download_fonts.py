"""
Downloads Google Fonts at Docker build time.
Skips fonts that fail (non-fatal) so the build never breaks.
Fonts marked CYR support Cyrillic (Russian / Tajik).
"""
import os, time, urllib.request

FONT_DIR  = '/usr/share/fonts/keychain'
LOCAL_DIR = '/root/.local/share/fonts'
os.makedirs(FONT_DIR,  exist_ok=True)
os.makedirs(LOCAL_DIR, exist_ok=True)

BASE = 'https://github.com/google/fonts/raw/main/ofl'

FONTS = [
    # ── Поддерживают кириллицу ───────────────────────────────────────────────
    ('Pacifico-Regular.ttf',    f'{BASE}/pacifico/Pacifico-Regular.ttf'),
    ('Lobster-Regular.ttf',     f'{BASE}/lobster/Lobster-Regular.ttf'),
    ('RussoOne-Regular.ttf',    f'{BASE}/russoone/RussoOne-Regular.ttf'),
    ('YesevaOne-Regular.ttf',   f'{BASE}/yesevaone/YesevaOne-Regular.ttf'),
    ('Neucha.ttf',              f'{BASE}/neucha/Neucha.ttf'),
    ('Play-Bold.ttf',           f'{BASE}/play/Play-Bold.ttf'),
    ('Comfortaa-Bold.ttf',      f'{BASE}/comfortaa/static/Comfortaa-Bold.ttf'),
    ('RuslanDisplay.ttf',       f'{BASE}/ruslandisplay/RuslanDisplay.ttf'),
    # ── Только латиница ──────────────────────────────────────────────────────
    ('Cookie-Regular.ttf',      f'{BASE}/cookie/Cookie-Regular.ttf'),
    ('Courgette-Regular.ttf',   f'{BASE}/courgette/Courgette-Regular.ttf'),
    ('Bangers-Regular.ttf',     f'{BASE}/bangers/Bangers-Regular.ttf'),
    ('Satisfy-Regular.ttf',     f'{BASE}/satisfy/Satisfy-Regular.ttf'),
    ('Righteous-Regular.ttf',   f'{BASE}/righteous/Righteous-Regular.ttf'),
    ('DancingScript-Bold.ttf',  f'{BASE}/dancingscript/static/DancingScript-Bold.ttf'),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; font-downloader/1.0)',
    'Accept': '*/*',
}

ok, fail = 0, 0
for filename, url in FONTS:
    print(f'Downloading {filename} ...', flush=True)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            if len(data) < 5_000:
                raise ValueError(f'Too small: {len(data)} bytes')
            for d in (FONT_DIR, LOCAL_DIR):
                with open(os.path.join(d, filename), 'wb') as f:
                    f.write(data)
            print(f'  OK  {len(data)//1024} KB', flush=True)
            ok += 1
            time.sleep(0.4)
            break
        except Exception as e:
            wait = 3 * (attempt + 1)
            print(f'  attempt {attempt+1} failed: {e}  (retry in {wait}s)', flush=True)
            if attempt < 3:
                time.sleep(wait)
    else:
        print(f'  WARNING: skipping {filename}', flush=True)
        fail += 1

print(f'\nFonts: {ok} downloaded, {fail} skipped.', flush=True)
