"""Downloads Google Fonts at Docker build time with retries."""
import os, sys, time, urllib.request

FONT_DIR  = '/usr/share/fonts/keychain'
LOCAL_DIR = '/root/.local/share/fonts'
os.makedirs(FONT_DIR,  exist_ok=True)
os.makedirs(LOCAL_DIR, exist_ok=True)

BASE = 'https://github.com/google/fonts/raw/main/ofl'

FONTS = [
    ('Pacifico-Regular.ttf',   f'{BASE}/pacifico/Pacifico-Regular.ttf'),
    ('Lobster-Regular.ttf',    f'{BASE}/lobster/Lobster-Regular.ttf'),
    ('Cookie-Regular.ttf',     f'{BASE}/cookie/Cookie-Regular.ttf'),
    ('Chewy-Regular.ttf',      f'{BASE}/chewy/Chewy-Regular.ttf'),
    ('Courgette-Regular.ttf',  f'{BASE}/courgette/Courgette-Regular.ttf'),
    ('Bangers-Regular.ttf',    f'{BASE}/bangers/Bangers-Regular.ttf'),
    ('DancingScript-Bold.ttf', f'{BASE}/dancingscript/static/DancingScript-Bold.ttf'),
    ('DynaPuff-Regular.ttf',   f'{BASE}/dynapuff/static/DynaPuff-Regular.ttf'),
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; font-downloader/1.0)', 'Accept': '*/*'}

for filename, url in FONTS:
    print(f'Downloading {filename} ...', flush=True)
    for attempt in range(5):
        try:
            req  = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            if len(data) < 5_000:
                raise ValueError(f'Too small: {len(data)} bytes')
            for d in (FONT_DIR, LOCAL_DIR):
                with open(os.path.join(d, filename), 'wb') as f:
                    f.write(data)
            print(f'  OK  {len(data)//1024} KB', flush=True)
            time.sleep(0.5)   # small pause to avoid rate-limit
            break
        except Exception as e:
            wait = 3 * (attempt + 1)
            print(f'  attempt {attempt+1} failed: {e}  (retry in {wait}s)', flush=True)
            time.sleep(wait)
    else:
        print(f'FATAL: could not download {filename}', flush=True)
        sys.exit(1)

print('All fonts ready.', flush=True)
