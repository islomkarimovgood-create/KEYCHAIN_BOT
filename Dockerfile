FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    openscad \
    fontconfig \
    xvfb \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/share/fonts/keychain /root/.local/share/fonts
COPY download_fonts.py /tmp/download_fonts.py
RUN python3 /tmp/download_fonts.py && fc-cache -f -v

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-u", "bot.py"]
