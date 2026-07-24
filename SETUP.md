# Keychain Bot — Инструкция по запуску

## Что делает бот
Клиент вводит имя → выбирает шрифт → цвет текста → цвет подложки →
получает превью → оставляет контакт → **вам приходит готовый .3mf файл
для Bambu Studio с уже назначенными AMS-слотами**.

---

## Шаг 1 — Создать бота в Telegram

1. Откройте **@BotFather** → `/newbot`
2. Придумайте имя и username
3. Скопируйте **токен** (вида `1234567890:ABC...`)

---

## Шаг 2 — Узнать свой Chat ID

Напишите боту **@userinfobot** — он пришлёт ваш `id` (число).

---

## Шаг 3 — Деплой на Railway (бесплатно, 24/7)

1. Зарегистрируйтесь на [railway.app](https://railway.app) (GitHub аккаунт)
2. Создайте новый проект → **Deploy from GitHub repo**
3. Загрузите все файлы из этой папки в GitHub репозиторий
4. В Railway: **Variables** → добавьте:
   ```
   BOT_TOKEN     = <ваш токен от BotFather>
   OWNER_CHAT_ID = <ваш chat id>
   ```
5. Railway автоматически соберёт Dockerfile и запустит бота

---

## Шаг 4 — Открыть .3mf в Bambu Studio

1. Откройте полученный `.3mf` файл в Bambu Studio
2. Объект **back_plate** → AMS слот 1 (чёрный филамент)
3. Объект **text_layer** → AMS слот 2 (цветной филамент)
4. Слайсируйте и печатайте 🎉

---

## Структура файлов

```
keychain_bot/
├── bot.py          — Telegram бот (диалог с клиентом)
├── generator.py    — OpenSCAD → STL → .3mf
├── preview.py      — 2D превью через Pillow
├── Dockerfile      — сборка образа с OpenSCAD + шрифтами
├── requirements.txt
├── railway.toml    — конфиг деплоя
└── .env.example    — переменные окружения
```

---

## Локальный запуск (для теста)

```bash
# Установить зависимости
pip install python-telegram-bot==20.8 Pillow==10.4.0

# Установить OpenSCAD (https://openscad.org/downloads.html)

# Скачать шрифты в /usr/share/fonts/keychain/ (или изменить FONT_DIR в preview.py)

# Запустить
export BOT_TOKEN="ваш_токен"
export OWNER_CHAT_ID="ваш_chat_id"
python bot.py
```
