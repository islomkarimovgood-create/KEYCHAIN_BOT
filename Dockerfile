FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# ── Системные пакеты ─────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    openscad \
    potrace \
    fontconfig \
    xvfb \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# ── Шрифты (латиница + кириллица) ────────────────────────────────────────────
RUN mkdir -p /usr/share/fonts/keychain /root/.local/share/fonts
COPY download_fonts.py /tmp/download_fonts.py
RUN python3 /tmp/download_fonts.py && fc-cache -f -v

# ── Эмблемы автомарок (SVG, Simple Icons) ────────────────────────────────────
RUN mkdir -p /usr/share/carlogos
COPY car_logos.py /tmp/car_logos.py
RUN cd /tmp && python3 car_logos.py || echo "Часть эмблем пропущена — не критично"

# Эмблемы, добавленные вручную — кладутся поверх скачанных
COPY carlogos* /usr/share/carlogos/
RUN rm -f /usr/share/carlogos/README.md && \
    echo "Эмблем в образе: $(ls /usr/share/carlogos/*.svg 2>/dev/null | wc -l)"

# ── Python-зависимости ───────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# ── Код бота ─────────────────────────────────────────────────────────────────
COPY . .

CMD ["python3", "-u", "bot.py"]
