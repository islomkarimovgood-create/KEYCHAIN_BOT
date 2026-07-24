FROM python:3.11-slim

# ── System packages ──────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    openscad \
    wget \
    fontconfig \
    libglu1-mesa \
    libxi6 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# ── Google Fonts (needed by OpenSCAD and Pillow preview) ────────────────────
RUN mkdir -p /usr/share/fonts/keychain /root/.local/share/fonts

RUN cd /usr/share/fonts/keychain && \
    BASE="https://github.com/google/fonts/raw/main/ofl" && \
    wget -q "$BASE/pacifico/Pacifico-Regular.ttf" && \
    wget -q "$BASE/lobster/Lobster-Regular.ttf" && \
    wget -q "$BASE/cookie/Cookie-Regular.ttf" && \
    wget -q "$BASE/chewy/Chewy-Regular.ttf" && \
    wget -q "$BASE/courgette/Courgette-Regular.ttf" && \
    wget -q "$BASE/bangers/Bangers-Regular.ttf" && \
    wget -q "$BASE/dancingscript/DancingScript%5Bwght%5D.ttf" -O DancingScript-Bold.ttf && \
    wget -q "$BASE/dynapuff/DynaPuff%5Bwdth%2Cwght%5D.ttf"   -O DynaPuff-Regular.ttf

# Refresh font cache + make fonts available to OpenSCAD user-font dir
RUN cp /usr/share/fonts/keychain/*.ttf /root/.local/share/fonts/ && \
    fc-cache -f -v

# ── Python dependencies ──────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App code ─────────────────────────────────────────────────────────────────
COPY . .

# OpenSCAD needs a virtual display on some Linux environments
CMD ["xvfb-run", "--auto-servernum", "python", "bot.py"]
