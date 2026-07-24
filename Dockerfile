FROM python:3.11-slim

# ── System packages ──────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    openscad \
    fontconfig \
    libglu1-mesa \
    libxi6 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# ── Download Google Fonts via Python (retry-safe) ────────────────────────────
RUN mkdir -p /usr/share/fonts/keychain /root/.local/share/fonts
COPY download_fonts.py /tmp/download_fonts.py
RUN python3 /tmp/download_fonts.py && fc-cache -f -v

# ── Python dependencies ──────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App code ─────────────────────────────────────────────────────────────────
COPY . .

CMD ["xvfb-run", "--auto-servernum", "python", "bot.py"]
