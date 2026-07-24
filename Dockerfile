# Ubuntu 22.04 — openscad есть в стандартных репозиториях
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ── Системные пакеты ─────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    openscad \
    fontconfig \
    xvfb \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# ── Скачать шрифты (ошибки не фатальны — упавший шрифт пропускается) ─────────
RUN mkdir -p /usr/share/fonts/keychain /root/.local/share/fonts
COPY download_fonts.py /tmp/download_fonts.py
RUN python3 /tmp/download_fonts.py && fc-cache -f -v

# ── Python зависимости ───────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# ── Код бота ─────────────────────────────────────────────────────────────────
COPY . .

CMD ["python3", "bot.py"]
