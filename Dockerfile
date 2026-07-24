FROM python:3.11-slim

# ── System packages ──────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    openscad \
    curl \
    fontconfig \
    libglu1-mesa \
    libxi6 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# ── Google Fonts (static versions — без спецсимволов в именах) ───────────────
RUN mkdir -p /usr/share/fonts/keychain /root/.local/share/fonts

RUN BASE="https://github.com/google/fonts/raw/main/ofl" && \
    curl -fL -o /usr/share/fonts/keychain/Pacifico-Regular.ttf \
      "$BASE/pacifico/Pacifico-Regular.ttf" && \
    curl -fL -o /usr/share/fonts/keychain/Lobster-Regular.ttf \
      "$BASE/lobster/Lobster-Regular.ttf" && \
    curl -fL -o /usr/share/fonts/keychain/Cookie-Regular.ttf \
      "$BASE/cookie/Cookie-Regular.ttf" && \
    curl -fL -o /usr/share/fonts/keychain/Chewy-Regular.ttf \
      "$BASE/chewy/Chewy-Regular.ttf" && \
    curl -fL -o /usr/share/fonts/keychain/Courgette-Regular.ttf \
      "$BASE/courgette/Courgette-Regular.ttf" && \
    curl -fL -o /usr/share/fonts/keychain/Bangers-Regular.ttf \
      "$BASE/bangers/Bangers-Regular.ttf" && \
    curl -fL -o /usr/share/fonts/keychain/DancingScript-Bold.ttf \
      "$BASE/dancingscript/static/DancingScript-Bold.ttf" && \
    curl -fL -o /usr/share/fonts/keychain/DynaPuff-Regular.ttf \
      "$BASE/dynapuff/static/DynaPuff-Regular.ttf"

# Refresh font cache
RUN cp /usr/share/fonts/keychain/*.ttf /root/.local/share/fonts/ && \
    fc-cache -f -v

# ── Python dependencies ──────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App code ─────────────────────────────────────────────────────────────────
COPY . .

CMD ["xvfb-run", "--auto-servernum", "python", "bot.py"]
