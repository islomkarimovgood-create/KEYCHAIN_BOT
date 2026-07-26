import os, sys, logging, asyncio, functools, traceback, urllib.request, urllib.parse

# ── Диагностика при старте (без сторонних библиотек) ─────────────────────────
TOKEN   = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("OWNER_CHAT_ID", "")


def tg_send(text):
    if not TOKEN or not CHAT_ID:
        print("ENV MISSING", flush=True)
        return
    try:
        url  = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
        urllib.request.urlopen(url, data, timeout=10)
    except Exception as e:
        print(f"TG error: {e}", flush=True)


print("=== BOT STARTING ===", flush=True)
if not TOKEN:
    print("NO BOT_TOKEN", flush=True); sys.exit(1)
if not CHAT_ID:
    print("NO OWNER_CHAT_ID", flush=True); sys.exit(1)
tg_send("⚙️ Python OK, загружаю библиотеки...")

try:
    from PIL import Image, ImageDraw, ImageFont
    tg_send("⚙️ Pillow OK")
except Exception as e:
    tg_send(f"❌ Pillow: {e}"); sys.exit(1)

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        CallbackQueryHandler, ConversationHandler, filters,
    )
    tg_send("⚙️ telegram-bot OK")
except Exception as e:
    tg_send(f"❌ telegram-bot: {e}"); sys.exit(1)

try:
    from preview import generate_preview
    from generator import generate_keychain_3mf, generate_logo_3mf
    from image_to_svg import image_to_svg
    import colors as C
    import car_logos
    tg_send("⚙️ Модули OK — запускаю бота!")
except Exception as e:
    tg_send(f"❌ Модули: {e}"); sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN     = TOKEN
OWNER_CHAT_ID = CHAT_ID
WORK_DIR      = Path("/tmp/keychains")
PREVIEW_DIR   = Path("/tmp/previews")

# Только одна тяжёлая генерация одновременно — иначе не хватит памяти
GEN_LOCK = asyncio.Semaphore(1)


def cleanup_temp(*paths):
    for p in paths:
        try:
            if p and Path(p).exists():
                Path(p).unlink()
        except Exception:
            pass


def cleanup_old_files(max_age_sec=600):
    import time
    now = time.time()
    for folder in (WORK_DIR, PREVIEW_DIR):
        try:
            for f in folder.rglob("*"):
                if f.is_file() and now - f.stat().st_mtime > max_age_sec:
                    f.unlink(missing_ok=True)
        except Exception:
            pass


# ── Состояния диалога ────────────────────────────────────────────────────────
(LANG, TYPE,
 NAME, FONT, FONT_SIZE, TEXT_HEIGHT, BACK_HEIGHT, RING_SIZE,
 TEXT_COLOR, BACK_COLOR,
 LOGO_UPLOAD, CAR_BRAND, LOGO_SIZE,
 CONFIRM, CONTACT) = range(15)

# ── Переводы ─────────────────────────────────────────────────────────────────
T = {
    "ru": {
        "welcome": (
            "👋 Добро пожаловать в магазин именных 3D-брелоков!\n\n"
            "🎨 Мы создаём уникальные брелоки на заказ:\n"
            "• Именные с любым шрифтом\n"
            "• С вашим логотипом\n"
            "• С эмблемой любимого авто\n\n"
            "🖨️ Печатаем на профессиональном принтере Bambu Lab\n"
            "⚡ Срок: 1-2 дня | 💎 Качество: премиум\n\n"
            "Выберите тип брелока:"
        ),
        "choose_type": "🔑 Какой брелок вы хотите?",
        "type_named": "🏷️ Именной брелок",
        "type_logo":  "🎨 Брелок с логотипом",
        "type_car":   "🚗 Брелок с лого авто",
        "enter_name": "✏️ Введите имя или текст для брелка\n_(макс. 15 символов)_",
        "choose_font": "🔤 Выберите шрифт:",
        "choose_font_size": "📏 Выберите размер текста (высота букв в мм):",
        "choose_text_height": "📐 Высота слоя текста (мм)\n_Чем больше — тем рельефнее надпись:_",
        "choose_back_height": "🧱 Толщина подложки (мм)\n_Чем больше — тем прочнее брелок:_",
        "choose_ring": "🔘 Диаметр отверстия для кольца (мм):",
        "choose_text_color": "🎨 Цвет текста:",
        "choose_back_color": "🖤 Цвет подложки:",
        "generating_preview": "⏳ Генерирую превью...",
        "your_keychain": "👀 *Ваш брелок:*",
        "order_btn": "✅ Заказать",
        "restart_btn": "🔄 Начать заново",
        "enter_contact": "📞 Введите ваш номер телефона или @username для связи:",
        "generating_file": "⏳ Генерирую файл для 3D-печати...",
        "order_accepted": "✅ *Заказ принят!*\n\nМы свяжемся с вами в ближайшее время. 🎉\n\n/start — создать ещё брелок",
        "name_too_long": "⚠️ Максимум 15 символов. Попробуйте ещё раз:",
        "upload_logo": "🖼️ Пришлите фото вашего логотипа (чёрно-белый PNG — лучший результат):",
        "choose_car": "🚗 Выберите марку автомобиля:",
        "cancelled": "❌ Отменено. /start — начать заново.",
        "name_lbl": "📛 Имя",
        "font_lbl": "🔤 Шрифт",
        "size_lbl": "📏 Размер текста",
        "text_h_lbl": "📐 Высота текста",
        "back_h_lbl": "🧱 Толщина подложки",
        "ring_lbl": "🔘 Отверстие",
        "text_c_lbl": "🎨 Цвет текста",
        "back_c_lbl": "🖤 Подложка",
    },
    "tj": {
        "welcome": (
            "👋 Хуш омадед ба мағозаи тасмаҳои калиди 3D!\n\n"
            "🎨 Мо тасмаҳои калиди фармоишӣ месозем:\n"
            "• Бо ном ва хати дилхоҳ\n"
            "• Бо логотипи шумо\n"
            "• Бо нишони мошини дӯстдоштаи шумо\n\n"
            "🖨️ Чопи касбӣ | ⚡ Мӯҳлат: 1-2 рӯз | 💎 Сифат: аъло\n\n"
            "Намуди тасмаи калидро интихоб кунед:"
        ),
        "choose_type": "🔑 Кадом тасмаи калид мехоҳед?",
        "type_named": "🏷️ Тасмаи калиди номӣ",
        "type_logo":  "🎨 Тасмаи калид бо логотип",
        "type_car":   "🚗 Тасмаи калид бо логои мошин",
        "enter_name": "✏️ Ном ё матни тасмаи калидро ворид кунед\n_(ҳадди аксар 15 аломат)_",
        "choose_font": "🔤 Хатро интихоб кунед:",
        "choose_font_size": "📏 Андозаи матн (баландии ҳарфҳо дар мм):",
        "choose_text_height": "📐 Баландии қабати матн (мм):",
        "choose_back_height": "🧱 Ғафсии зерсохт (мм):",
        "choose_ring": "🔘 Диаметри сӯрохи ҳалқа (мм):",
        "choose_text_color": "🎨 Ранги матн:",
        "choose_back_color": "🖤 Ранги зерсохт:",
        "generating_preview": "⏳ Тасвирро тайёр мекунам...",
        "your_keychain": "👀 *Тасмаи калиди шумо:*",
        "order_btn": "✅ Фармоиш додан",
        "restart_btn": "🔄 Аз нав оғоз кардан",
        "enter_contact": "📞 Рақами телефон ё @username-и худро ворид кунед:",
        "generating_file": "⏳ Файлро барои чоп омода мекунам...",
        "order_accepted": "✅ *Фармоиш қабул шуд!*\n\nМо ба зудӣ бо шумо тамос мегирем. 🎉\n\n/start — фармоиши дигар",
        "name_too_long": "⚠️ Ҳадди аксар 15 аломат. Дубора кӯшиш кунед:",
        "upload_logo": "🖼️ Акси логотипатонро бифиристед (PNG сиёҳу сафед — беҳтарин натиҷа):",
        "choose_car": "🚗 Маркаи мошинро интихоб кунед:",
        "cancelled": "❌ Бекор шуд. /start — аз нав оғоз кардан.",
        "name_lbl": "📛 Ном",
        "font_lbl": "🔤 Хат",
        "size_lbl": "📏 Андозаи матн",
        "text_h_lbl": "📐 Баландии матн",
        "back_h_lbl": "🧱 Ғафсии зерсохт",
        "ring_lbl": "🔘 Сӯрох",
        "text_c_lbl": "🎨 Ранги матн",
        "back_c_lbl": "🖤 Зерсохт",
    },
    "en": {
        "welcome": (
            "👋 Welcome to the 3D Keychain Shop!\n\n"
            "🎨 We create custom keychains:\n"
            "• Named keychains with any font\n"
            "• With your logo\n"
            "• With your favourite car brand\n\n"
            "🖨️ Printed on Bambu Lab | ⚡ Ready in 1-2 days | 💎 Premium quality\n\n"
            "Choose your keychain type:"
        ),
        "choose_type": "🔑 What keychain do you want?",
        "type_named": "🏷️ Named keychain",
        "type_logo":  "🎨 Logo keychain",
        "type_car":   "🚗 Car logo keychain",
        "enter_name": "✏️ Enter the name or text for your keychain\n_(max 15 characters)_",
        "choose_font": "🔤 Choose a font:",
        "choose_font_size": "📏 Text size (letter height in mm):",
        "choose_text_height": "📐 Text layer height (mm)\n_Higher = more raised letters:_",
        "choose_back_height": "🧱 Back plate thickness (mm)\n_Thicker = stronger keychain:_",
        "choose_ring": "🔘 Ring hole diameter (mm):",
        "choose_text_color": "🎨 Text colour:",
        "choose_back_color": "🖤 Back plate colour:",
        "generating_preview": "⏳ Generating preview...",
        "your_keychain": "👀 *Your keychain:*",
        "order_btn": "✅ Order",
        "restart_btn": "🔄 Start over",
        "enter_contact": "📞 Enter your phone number or @username:",
        "generating_file": "⏳ Generating 3D print file...",
        "order_accepted": "✅ *Order accepted!*\n\nWe will contact you shortly. 🎉\n\n/start — create another keychain",
        "name_too_long": "⚠️ Maximum 15 characters. Please try again:",
        "upload_logo": "🖼️ Send a photo of your logo (black & white PNG gives the best result):",
        "choose_car": "🚗 Choose your car brand:",
        "cancelled": "❌ Cancelled. /start — start again.",
        "name_lbl": "📛 Name",
        "font_lbl": "🔤 Font",
        "size_lbl": "📏 Text size",
        "text_h_lbl": "📐 Text height",
        "back_h_lbl": "🧱 Back height",
        "ring_lbl": "🔘 Ring hole",
        "text_c_lbl": "🎨 Text colour",
        "back_c_lbl": "🖤 Back colour",
    },
}


def t(context, key):
    lang = context.user_data.get("lang", "ru")
    return T[lang].get(key, T["ru"].get(key, key))


# ── Шрифты ───────────────────────────────────────────────────────────────────
FONTS_CYRILLIC = [
    "Pacifico", "Lobster", "Russo One", "Yeseva One",
    "Neucha", "Play", "Comfortaa", "Ruslan Display",
]
FONTS_LATIN = [
    "Pacifico", "Lobster", "Cookie", "Dancing Script",
    "Satisfy", "Righteous", "Courgette", "Bangers",
]


def has_cyrillic(text: str) -> bool:
    return any("\u0400" <= ch <= "\u04FF" for ch in text)


def fonts_for(text: str):
    return FONTS_CYRILLIC if has_cyrillic(text) else FONTS_LATIN


# ── Параметры ────────────────────────────────────────────────────────────────
FONT_SIZES   = ["10", "12", "14", "16", "18", "20"]
TEXT_HEIGHTS = ["1", "2", "3"]
BACK_HEIGHTS = ["2", "3", "4", "5"]
RING_SIZES   = ["3", "4", "5", "6"]
LOGO_SIZES   = ["20", "25", "30", "35", "40", "50"]

COLORS_PER_PAGE = 12
CARS_PER_PAGE   = 12

AVAILABLE_CARS = car_logos.load_available()
if not AVAILABLE_CARS:
    AVAILABLE_CARS = list(car_logos.CAR_BRANDS)


# ── Клавиатуры ───────────────────────────────────────────────────────────────
def kb(items, cols=2):
    buttons = [InlineKeyboardButton(txt, callback_data=txt) for txt in items]
    rows = [buttons[i:i + cols] for i in range(0, len(buttons), cols)]
    return InlineKeyboardMarkup(rows)


def kb_data(pairs, cols=2):
    buttons = [InlineKeyboardButton(lbl, callback_data=dat) for lbl, dat in pairs]
    rows = [buttons[i:i + cols] for i in range(0, len(buttons), cols)]
    return InlineKeyboardMarkup(rows)


def paged_kb(items, page, per_page, prefix, cols=2):
    """items = [(подпись, значение), ...] + кнопки листания."""
    total = max(1, (len(items) + per_page - 1) // per_page)
    page  = max(0, min(page, total - 1))
    chunk = items[page * per_page:(page + 1) * per_page]

    buttons = [InlineKeyboardButton(lbl, callback_data=f"{prefix}:{val}")
               for lbl, val in chunk]
    rows = [buttons[i:i + cols] for i in range(0, len(buttons), cols)]

    if total > 1:
        rows.append([
            InlineKeyboardButton("◀️", callback_data=f"{prefix}page:{(page - 1) % total}"),
            InlineKeyboardButton(f"{page + 1}/{total}", callback_data="noop"),
            InlineKeyboardButton("▶️", callback_data=f"{prefix}page:{(page + 1) % total}"),
        ])
    return InlineKeyboardMarkup(rows)


def color_items():
    return [(lbl, lbl) for lbl in C.labels()]


def car_items():
    return [(name, slug) for name, slug in AVAILABLE_CARS]


def parse_cb(data: str, prefix: str):
    """Разбирает callback_data. Возвращает ('page', N) | ('value', X) | ('noop', None)."""
    data = data or ""
    if data == "noop":
        return "noop", None
    if data.startswith(f"{prefix}page:"):
        try:
            return "page", int(data.split(":", 1)[1])
        except ValueError:
            return "page", 0
    if data.startswith(f"{prefix}:"):
        return "value", data.split(":", 1)[1]
    return "value", data


LANG_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("🇷🇺 Русский", callback_data="ru"),
    InlineKeyboardButton("🇹🇯 Тоҷикӣ",  callback_data="tj"),
    InlineKeyboardButton("🇬🇧 English", callback_data="en"),
]])
LANG_PROMPT = "🌍 Выберите язык / Забонро интихоб кунед / Choose language:"


# ═════════════════════════════════════════════════════════════════════════════
#  СТАРТ И ВЫБОР ЯЗЫКА
# ═════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context):
    context.user_data.clear()
    await update.message.reply_text(LANG_PROMPT, reply_markup=LANG_KB)
    return LANG


async def get_lang(update: Update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["lang"] = q.data if q.data in T else "ru"

    type_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "type_named"), callback_data="named")],
        [InlineKeyboardButton(t(context, "type_logo"),  callback_data="logo")],
        [InlineKeyboardButton(t(context, "type_car"),   callback_data="car")],
    ])
    await q.edit_message_text(t(context, "welcome"), reply_markup=type_kb)
    return TYPE


async def get_type(update: Update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["type"] = q.data

    if q.data == "named":
        await q.edit_message_text(t(context, "enter_name"), parse_mode="Markdown")
        return NAME
    if q.data == "logo":
        await q.edit_message_text(t(context, "upload_logo"))
        return LOGO_UPLOAD
    await q.edit_message_text(
        t(context, "choose_car"),
        reply_markup=paged_kb(car_items(), 0, CARS_PER_PAGE, "car", cols=2),
    )
    return CAR_BRAND


# ═════════════════════════════════════════════════════════════════════════════
#  ВЕТКА 1: ИМЕННОЙ БРЕЛОК
# ═════════════════════════════════════════════════════════════════════════════

async def get_name(update: Update, context):
    name = update.message.text.strip()
    if not name or len(name) > 15:
        await update.message.reply_text(t(context, "name_too_long"))
        return NAME

    context.user_data["name"] = name
    available = fonts_for(name)

    note = ""
    if has_cyrillic(name):
        note = {
            "ru": "\n\n_Показаны шрифты с поддержкой кириллицы_",
            "tj": "\n\n_Хатҳои дорои дастгирии кириллица_",
            "en": "\n\n_Showing fonts that support Cyrillic_",
        }.get(context.user_data.get("lang", "ru"), "")

    await update.message.reply_text(
        t(context, "choose_font") + note,
        parse_mode="Markdown",
        reply_markup=kb(available, cols=2),
    )
    return FONT


async def get_font(update: Update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["font"] = (
        q.data if q.data in FONTS_CYRILLIC or q.data in FONTS_LATIN else "Pacifico"
    )
    await q.edit_message_text(
        t(context, "choose_font_size"),
        reply_markup=kb_data([(f"{s} мм", s) for s in FONT_SIZES], cols=3),
    )
    return FONT_SIZE


async def get_font_size(update: Update, context):
    q = update.callback_query
    await q.answer()
    try:
        context.user_data["font_size"] = int(q.data)
    except (TypeError, ValueError):
        context.user_data["font_size"] = 16
    await q.edit_message_text(
        t(context, "choose_text_height"),
        parse_mode="Markdown",
        reply_markup=kb_data([(f"{h} мм", h) for h in TEXT_HEIGHTS], cols=3),
    )
    return TEXT_HEIGHT


async def get_text_height(update: Update, context):
    q = update.callback_query
    await q.answer()
    try:
        context.user_data["text_height"] = float(q.data)
    except (TypeError, ValueError):
        context.user_data["text_height"] = 2.0
    await q.edit_message_text(
        t(context, "choose_back_height"),
        parse_mode="Markdown",
        reply_markup=kb_data([(f"{h} мм", h) for h in BACK_HEIGHTS], cols=4),
    )
    return BACK_HEIGHT


async def get_back_height(update: Update, context):
    q = update.callback_query
    await q.answer()
    try:
        context.user_data["back_height"] = float(q.data)
    except (TypeError, ValueError):
        context.user_data["back_height"] = 3.0
    await q.edit_message_text(
        t(context, "choose_ring"),
        reply_markup=kb_data([(f"⌀ {r} мм", r) for r in RING_SIZES], cols=4),
    )
    return RING_SIZE


async def get_ring_size(update: Update, context):
    q = update.callback_query
    await q.answer()
    try:
        context.user_data["ring_size"] = float(q.data)
    except (TypeError, ValueError):
        context.user_data["ring_size"] = 4.0
    await q.edit_message_text(
        t(context, "choose_text_color"),
        reply_markup=paged_kb(color_items(), 0, COLORS_PER_PAGE, "tc", cols=2),
    )
    return TEXT_COLOR


# ═════════════════════════════════════════════════════════════════════════════
#  ВЕТКА 2: ЛОГОТИП КЛИЕНТА
# ═════════════════════════════════════════════════════════════════════════════

async def get_logo(update: Update, context):
    if not update.message.photo:
        await update.message.reply_text(t(context, "upload_logo"))
        return LOGO_UPLOAD

    photo = update.message.photo[-1]
    file  = await context.bot.get_file(photo.file_id)
    uid   = update.effective_user.id
    logo_path = f"/tmp/logo_{uid}.jpg"
    svg_path  = f"/tmp/logo_{uid}.svg"
    await file.download_to_drive(logo_path)

    d = context.user_data
    d["logo_path"] = logo_path
    d["name"] = "Логотип"

    msg = await update.message.reply_text("⏳ Обрабатываю изображение...")

    try:
        loop = asyncio.get_running_loop()
        async with GEN_LOCK:
            await asyncio.wait_for(
                loop.run_in_executor(
                    None, functools.partial(image_to_svg, logo_path, svg_path)
                ),
                timeout=60,
            )
        d["svg_path"] = svg_path
        note = "✅ Логотип распознан!\n\n"
    except Exception as e:
        logger.error(f"Vectorize error: {e}")
        d["svg_path"] = None
        note = (f"⚠️ Не удалось перевести картинку в 3D:\n_{str(e)[:150]}_\n\n"
                "Заказ оформим — модель сделаем вручную.\n\n")

    try:
        await msg.delete()
    except Exception:
        pass

    await update.message.reply_text(
        note + "📐 Выберите размер логотипа (мм):",
        parse_mode="Markdown",
        reply_markup=kb_data([(f"{s} мм", s) for s in LOGO_SIZES], cols=3),
    )
    return LOGO_SIZE


# ═════════════════════════════════════════════════════════════════════════════
#  ВЕТКА 3: ЭМБЛЕМА АВТО
# ═════════════════════════════════════════════════════════════════════════════

async def get_car_brand(update: Update, context):
    q = update.callback_query
    await q.answer()
    kind, val = parse_cb(q.data, "car")

    if kind == "noop":
        return CAR_BRAND
    if kind == "page":
        await q.edit_message_text(
            t(context, "choose_car"),
            reply_markup=paged_kb(car_items(), val, CARS_PER_PAGE, "car", cols=2),
        )
        return CAR_BRAND

    slug = val
    brand = next((n for n, sl in AVAILABLE_CARS if sl == slug), slug)

    d = context.user_data
    d["car_brand"] = brand
    d["car_slug"]  = slug
    d["svg_path"]  = car_logos.slug_to_file(slug)
    d["name"]      = brand

    await q.edit_message_text(
        f"🚗 *{brand}*\n\n📐 Выберите размер эмблемы (мм):",
        parse_mode="Markdown",
        reply_markup=kb_data([(f"{s} мм", s) for s in LOGO_SIZES], cols=3),
    )
    return LOGO_SIZE


async def get_logo_size(update: Update, context):
    """Общий шаг для логотипа и эмблемы авто."""
    q = update.callback_query
    await q.answer()
    try:
        context.user_data["logo_size"] = float(q.data)
    except (TypeError, ValueError):
        context.user_data["logo_size"] = 30.0

    await q.edit_message_text(
        t(context, "choose_text_height"),
        parse_mode="Markdown",
        reply_markup=kb_data([(f"{h} мм", h) for h in TEXT_HEIGHTS], cols=3),
    )
    return TEXT_HEIGHT


# ═════════════════════════════════════════════════════════════════════════════
#  ЦВЕТА (общий шаг для всех типов)
# ═════════════════════════════════════════════════════════════════════════════

async def get_text_color(update: Update, context):
    q = update.callback_query
    await q.answer()
    kind, val = parse_cb(q.data, "tc")

    if kind == "noop":
        return TEXT_COLOR
    if kind == "page":
        await q.edit_message_text(
            t(context, "choose_text_color"),
            reply_markup=paged_kb(color_items(), val, COLORS_PER_PAGE, "tc", cols=2),
        )
        return TEXT_COLOR

    context.user_data["text_color_label"] = val
    context.user_data["text_color"] = C.color_name(val, "Pink")

    await q.edit_message_text(
        t(context, "choose_back_color"),
        reply_markup=paged_kb(color_items(), 0, COLORS_PER_PAGE, "bc", cols=2),
    )
    return BACK_COLOR


async def get_back_color(update: Update, context):
    q = update.callback_query
    await q.answer()
    kind, val = parse_cb(q.data, "bc")

    if kind == "noop":
        return BACK_COLOR
    if kind == "page":
        await q.edit_message_text(
            t(context, "choose_back_color"),
            reply_markup=paged_kb(color_items(), val, COLORS_PER_PAGE, "bc", cols=2),
        )
        return BACK_COLOR

    d = context.user_data
    d["back_color_label"] = val
    d["back_color"] = C.color_name(val, "Black")

    # Значения по умолчанию — чтобы нигде не было KeyError
    d.setdefault("name", "Keychain")
    d.setdefault("font", "Pacifico")
    d.setdefault("font_size", 16)
    d.setdefault("logo_size", 30.0)
    d.setdefault("text_height", 2.0)
    d.setdefault("back_height", 3.0)
    d.setdefault("ring_size", 4.0)
    d.setdefault("text_color", "Pink")
    d.setdefault("text_color_label", "🩷 Розовый")

    await q.edit_message_text(t(context, "generating_preview"))

    lang       = d.get("lang", "ru")
    order_type = d.get("type", "named")

    common = (
        f"📐 {T[lang]['text_h_lbl']}: *{d['text_height']} мм*\n"
        f"🧱 {T[lang]['back_h_lbl']}: *{d['back_height']} мм*\n"
        f"🔘 {T[lang]['ring_lbl']}: *⌀{d['ring_size']} мм*\n"
        f"🎨 {T[lang]['text_c_lbl']}: *{d['text_color_label']}*\n"
        f"🖤 {T[lang]['back_c_lbl']}: *{d['back_color_label']}*"
    )

    if order_type == "named":
        caption = (
            f"{T[lang]['your_keychain']}\n\n"
            f"{T[lang]['name_lbl']}: *{d['name']}*\n"
            f"{T[lang]['font_lbl']}: *{d['font']}*\n"
            f"{T[lang]['size_lbl']}: *{d['font_size']} мм*\n" + common
        )
    elif order_type == "car":
        caption = (
            f"{T[lang]['your_keychain']}\n\n"
            f"🚗 Марка: *{d.get('car_brand', '?')}*\n"
            f"📏 Размер эмблемы: *{d['logo_size']} мм*\n" + common
        )
    else:
        mark = "✅" if d.get("svg_path") else "⚠️"
        caption = (
            f"{T[lang]['your_keychain']}\n\n"
            f"🖼️ Ваш логотип {mark}\n"
            f"📏 Размер: *{d['logo_size']} мм*\n" + common
        )

    confirm_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "order_btn"),   callback_data="confirm")],
        [InlineKeyboardButton(t(context, "restart_btn"), callback_data="restart")],
    ])

    chat_id = q.message.chat_id

    preview_path = None
    if order_type == "named":
        try:
            preview_path = generate_preview(
                d["name"], d["font"], d["text_color"], d["back_color"]
            )
            if not preview_path or not Path(preview_path).exists():
                preview_path = None
        except Exception as e:
            logger.error(f"Preview error: {e}")
            preview_path = None

    try:
        await q.message.delete()
    except Exception:
        pass

    if preview_path:
        with open(preview_path, "rb") as f:
            await context.bot.send_photo(
                chat_id=chat_id, photo=f, caption=caption,
                parse_mode="Markdown", reply_markup=confirm_kb)
    elif order_type == "logo" and d.get("logo_path") and Path(d["logo_path"]).exists():
        with open(d["logo_path"], "rb") as f:
            await context.bot.send_photo(
                chat_id=chat_id, photo=f, caption=caption,
                parse_mode="Markdown", reply_markup=confirm_kb)
    else:
        await context.bot.send_message(
            chat_id=chat_id, text=caption,
            parse_mode="Markdown", reply_markup=confirm_kb)

    return CONFIRM


# ═════════════════════════════════════════════════════════════════════════════
#  ПОДТВЕРЖДЕНИЕ И ОФОРМЛЕНИЕ
# ═════════════════════════════════════════════════════════════════════════════

async def confirm(update: Update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "restart":
        try:
            await q.message.delete()
        except Exception:
            pass
        context.user_data.clear()
        await context.bot.send_message(
            chat_id=q.message.chat_id, text=LANG_PROMPT, reply_markup=LANG_KB)
        return LANG

    try:
        if q.message.caption is not None:
            await q.edit_message_caption(
                q.message.caption + "\n\n✅ Оформляем заказ!", parse_mode="Markdown")
        else:
            await q.edit_message_text(
                (q.message.text or "") + "\n\n✅ Оформляем заказ!", parse_mode="Markdown")
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=q.message.chat_id, text=t(context, "enter_contact"))
    return CONTACT


async def get_contact(update: Update, context):
    contact = update.message.text.strip()
    d = context.user_data
    d["contact"] = contact

    msg = await update.message.reply_text(t(context, "generating_file"))

    order_type = d.get("type", "named")
    type_label = {"named": "🏷️ Именной", "logo": "🎨 Логотип",
                  "car": "🚗 Авто"}.get(order_type, "Именной")

    file_3mf, error_note = None, ""
    cleanup_old_files()
    work_dir = WORK_DIR / str(update.effective_user.id)
    loop = asyncio.get_running_loop()

    try:
        if order_type == "named":
            async with GEN_LOCK:
                file_3mf = await asyncio.wait_for(
                    loop.run_in_executor(None, functools.partial(
                        generate_keychain_3mf,
                        name=d["name"], font=d["font"],
                        back_color=d.get("back_color", "Black"),
                        text_color=d.get("text_color", "Pink"),
                        work_dir=work_dir,
                        font_size=d.get("font_size", 16),
                        text_height=d.get("text_height", 2.0),
                        back_height=d.get("back_height", 3.0),
                        ring_radius=d.get("ring_size", 4.0) / 2,
                    )), timeout=110)

        elif d.get("svg_path") and Path(d["svg_path"]).exists():
            async with GEN_LOCK:
                file_3mf = await asyncio.wait_for(
                    loop.run_in_executor(None, functools.partial(
                        generate_logo_3mf,
                        svg_path=d["svg_path"],
                        back_color=d.get("back_color", "Black"),
                        text_color=d.get("text_color", "White"),
                        work_dir=work_dir,
                        name=d.get("name", "logo"),
                        logo_size=d.get("logo_size", 30.0),
                        text_height=d.get("text_height", 2.0),
                        back_height=d.get("back_height", 3.0),
                        ring_radius=d.get("ring_size", 4.0) / 2,
                    )), timeout=140)
        else:
            error_note = "\n⚠️ Модель не создана — нет исходного контура."

    except asyncio.TimeoutError:
        logger.error("3MF timeout")
        error_note = "\n⚠️ Генерация заняла слишком долго — сделайте файл вручную."
    except Exception as e:
        logger.error(f"3MF error: {e}")
        error_note = f"\n⚠️ Файл не сгенерирован.\nПричина: {str(e)[:350]}"

    lang = d.get("lang", "ru")
    lines = [
        f"🆕 *НОВЫЙ ЗАКАЗ* — {type_label}{error_note}",
        "",
        f"👤 {update.effective_user.full_name}"
        + (f" (@{update.effective_user.username})" if update.effective_user.username else ""),
        f"📞 {contact}",
        f"🌍 Язык: {lang.upper()}",
        "",
    ]

    if order_type == "named":
        lines += [
            f"📛 Имя: *{d.get('name','?')}*",
            f"🔤 Шрифт: {d.get('font','?')}",
            f"📏 Размер текста: {d.get('font_size','?')} мм",
        ]
    elif order_type == "car":
        lines += [
            f"🚗 Марка: *{d.get('car_brand','?')}*",
            f"📏 Размер эмблемы: {d.get('logo_size','?')} мм",
        ]
    else:
        lines += [
            "🖼️ Логотип клиента — фото ниже",
            f"📏 Размер: {d.get('logo_size','?')} мм",
        ]

    lines += [
        f"📐 Высота рельефа: {d.get('text_height','?')} мм",
        f"🧱 Подложка: {d.get('back_height','?')} мм",
        f"🔘 Отверстие: ⌀{d.get('ring_size','?')} мм",
        f"🎨 Цвет верха: {d.get('text_color_label','?')}",
        f"🖤 Цвет подложки: {d.get('back_color_label','?')}",
    ]

    order_text = "\n".join(lines)
    try:
        await context.bot.send_message(OWNER_CHAT_ID, order_text, parse_mode="Markdown")
    except Exception:
        import re as _re
        await context.bot.send_message(
            OWNER_CHAT_ID, _re.sub(r"[*_`\[\]]", "", order_text))

    if order_type == "logo" and d.get("logo_path") and Path(d["logo_path"]).exists():
        try:
            with open(d["logo_path"], "rb") as f:
                await context.bot.send_photo(
                    OWNER_CHAT_ID, photo=f, caption="🖼️ Логотип клиента")
        except Exception:
            pass

    if file_3mf and Path(file_3mf).exists():
        with open(file_3mf, "rb") as f:
            await context.bot.send_document(
                OWNER_CHAT_ID, document=f,
                filename=f"{d.get('name','keychain')}_keychain.3mf",
                caption=(f"🖨️ *{d.get('name','?')}*\n"
                         f"AMS1 = подложка ({d.get('back_color','')})\n"
                         f"AMS2 = верх ({d.get('text_color','')})"),
                parse_mode="Markdown")

    cleanup_temp(file_3mf, d.get("logo_path"))
    if d.get("svg_path") and "/tmp/logo_" in str(d.get("svg_path", "")):
        cleanup_temp(d["svg_path"])
    try:
        if work_dir.exists():
            for f in work_dir.glob("*"):
                f.unlink(missing_ok=True)
    except Exception:
        pass

    try:
        await msg.delete()
    except Exception:
        pass
    await update.message.reply_text(t(context, "order_accepted"), parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context):
    await update.message.reply_text(t(context, "cancelled"))
    context.user_data.clear()
    return ConversationHandler.END


# ═════════════════════════════════════════════════════════════════════════════
#  СЛУЖЕБНОЕ
# ═════════════════════════════════════════════════════════════════════════════

_conflict_notified = False


async def error_handler(update, context):
    global _conflict_notified
    err_text = str(context.error)

    if "Conflict" in err_text or "terminated by other" in err_text:
        if not _conflict_notified:
            _conflict_notified = True
            try:
                await context.bot.send_message(
                    OWNER_CHAT_ID,
                    "🛑 Обнаружен второй запущенный экземпляр бота!\n\n"
                    "На Railway оставьте только один ACTIVE-деплой.\n"
                    "Этот экземпляр останавливается.")
            except Exception:
                pass
        logger.error("Conflict — shutting down")
        os._exit(1)

    err = "".join(traceback.format_exception(
        type(context.error), context.error, context.error.__traceback__))[-1200:]
    logger.error(f"Unhandled: {err}")
    try:
        await context.bot.send_message(
            OWNER_CHAT_ID,
            f"⚠️ Ошибка (бот работает дальше):\n\n<code>{err[-800:]}</code>",
            parse_mode="HTML")
    except Exception:
        pass
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Произошла ошибка. Напишите /start чтобы начать заново.")
    except Exception:
        pass


async def periodic_cleanup(context):
    cleanup_old_files(max_age_sec=600)


async def post_init(app):
    try:
        await app.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=(f"🤖 Бот запущен!\n\n"
                  f"🎨 Цветов: {len(C.labels())}\n"
                  f"🚗 Марок авто: {len(AVAILABLE_CARS)}\n"
                  f"🔤 Шрифтов: {len(set(FONTS_CYRILLIC) | set(FONTS_LATIN))}"))
    except Exception as e:
        print(f"post_init error: {e}", flush=True)


def main():
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .get_updates_read_timeout(40)
        .build()
    )

    if app.job_queue:
        app.job_queue.run_repeating(periodic_cleanup, interval=300, first=300)

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:        [CallbackQueryHandler(get_lang)],
            TYPE:        [CallbackQueryHandler(get_type)],
            NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            FONT:        [CallbackQueryHandler(get_font)],
            FONT_SIZE:   [CallbackQueryHandler(get_font_size)],
            LOGO_UPLOAD: [MessageHandler(filters.PHOTO, get_logo),
                          MessageHandler(filters.TEXT & ~filters.COMMAND, get_logo)],
            CAR_BRAND:   [CallbackQueryHandler(get_car_brand)],
            LOGO_SIZE:   [CallbackQueryHandler(get_logo_size)],
            TEXT_HEIGHT: [CallbackQueryHandler(get_text_height)],
            BACK_HEIGHT: [CallbackQueryHandler(get_back_height)],
            RING_SIZE:   [CallbackQueryHandler(get_ring_size)],
            TEXT_COLOR:  [CallbackQueryHandler(get_text_color)],
            BACK_COLOR:  [CallbackQueryHandler(get_back_color)],
            CONFIRM:     [CallbackQueryHandler(confirm)],
            CONTACT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    print("=== POLLING STARTED ===", flush=True)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        msg = str(e)[:300]
        print(f"FATAL: {msg}", flush=True)
        if "Conflict" in msg or "terminated by other" in msg:
            tg_send("⚠️ Обнаружен второй запущенный бот! Оставьте один деплой на Railway.")
        else:
            tg_send(f"❌ Бот остановлен: {msg}")
        sys.exit(1)
