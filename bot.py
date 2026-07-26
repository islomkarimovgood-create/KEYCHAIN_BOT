import os, sys, logging, asyncio, functools, traceback, urllib.request, urllib.parse

# ── Диагностика при старте (без библиотек) ───────────────────────────────────
TOKEN   = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("OWNER_CHAT_ID", "")

def tg_send(text):
    if not TOKEN or not CHAT_ID:
        print(f"ENV MISSING", flush=True); return
    try:
        url  = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
        urllib.request.urlopen(url, data, timeout=10)
    except Exception as e:
        print(f"TG error: {e}", flush=True)

print("=== BOT STARTING ===", flush=True)
if not TOKEN: print("NO BOT_TOKEN", flush=True); sys.exit(1)
if not CHAT_ID: print("NO OWNER_CHAT_ID", flush=True); sys.exit(1)
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
    from generator import generate_keychain_3mf
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

# ── Состояния диалога ─────────────────────────────────────────────────────────
(LANG, TYPE,
 NAME, FONT, FONT_SIZE, TEXT_HEIGHT, BACK_HEIGHT, RING_SIZE,
 TEXT_COLOR, BACK_COLOR,
 LOGO_UPLOAD, CAR_BRAND,
 CONFIRM, CONTACT) = range(14)

# ── Переводы ──────────────────────────────────────────────────────────────────
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

# ── Параметры ─────────────────────────────────────────────────────────────────
FONTS = [
    "Pacifico", "Lobster", "Cookie", "Dancing Script",
    "Satisfy", "Righteous", "Courgette", "Bangers",
]

FONT_SIZES   = ["10", "12", "14", "16", "18", "20"]   # мм
TEXT_HEIGHTS = ["1", "2", "3"]                          # мм
BACK_HEIGHTS = ["2", "3", "4", "5"]                     # мм
RING_SIZES   = ["3", "4", "5", "6"]                     # мм диаметр

COLORS = {
    "Розовый 🩷 / Pink":      "Pink",
    "Голубой 💙 / Blue":      "Turquoise",
    "Фиолетовый 💜 / Purple": "Purple",
    "Красный ❤️ / Red":       "Red",
    "Зелёный 💚 / Green":     "Green",
    "Жёлтый 💛 / Yellow":     "Yellow",
    "Оранжевый 🧡 / Orange":  "Orange",
    "Белый ⬜ / White":        "White",
}
BACK_COLORS = {
    "Чёрный ⬛ / Black": "Black",
    "Белый ⬜ / White":   "White",
    "Серый 🔘 / Gray":    "Gray",
}

CAR_BRANDS = [
    "BMW 🔵", "Mercedes-Benz ⭐", "Toyota 🔴", "Honda 🔴",
    "Audi 🔵", "Volkswagen 🔵", "Ford 🔵", "Nissan 🔴",
    "Hyundai 🔵", "Kia 🔴", "Lexus 🔷", "Porsche 🟡",
    "Ferrari 🐎", "Lamborghini 🐂", "Chevrolet 🟡", "Subaru ⭐",
    "Mazda 🔴", "Mitsubishi ♦️",
]

# ── Вспомогательные функции ───────────────────────────────────────────────────
def kb(items, cols=2):
    buttons = [InlineKeyboardButton(txt, callback_data=txt) for txt in items]
    rows = [buttons[i:i+cols] for i in range(0, len(buttons), cols)]
    return InlineKeyboardMarkup(rows)

def kb_data(pairs, cols=2):
    """pairs = [(label, callback_data), ...]"""
    buttons = [InlineKeyboardButton(lbl, callback_data=dat) for lbl, dat in pairs]
    rows = [buttons[i:i+cols] for i in range(0, len(buttons), cols)]
    return InlineKeyboardMarkup(rows)

# ── /start → выбор языка ──────────────────────────────────────────────────────
async def start(update: Update, context):
    context.user_data.clear()
    lang_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🇷🇺 Русский",  callback_data="ru"),
        InlineKeyboardButton("🇹🇯 Тоҷикӣ",  callback_data="tj"),
        InlineKeyboardButton("🇬🇧 English",  callback_data="en"),
    ]])
    await update.message.reply_text(
        "🌍 Выберите язык / Забонро интихоб кунед / Choose language:",
        reply_markup=lang_kb,
    )
    return LANG

# ── Язык выбран ───────────────────────────────────────────────────────────────
async def get_lang(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["lang"] = q.data

    type_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "type_named"), callback_data="named")],
        [InlineKeyboardButton(t(context, "type_logo"),  callback_data="logo")],
        [InlineKeyboardButton(t(context, "type_car"),   callback_data="car")],
    ])
    await q.edit_message_text(t(context, "welcome"), reply_markup=type_kb, parse_mode="Markdown")
    return TYPE

# ── Тип брелока выбран ────────────────────────────────────────────────────────
async def get_type(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["type"] = q.data

    if q.data == "named":
        await q.edit_message_text(t(context, "enter_name"), parse_mode="Markdown")
        return NAME
    elif q.data == "logo":
        await q.edit_message_text(t(context, "upload_logo"))
        return LOGO_UPLOAD
    else:  # car
        await q.edit_message_text(t(context, "choose_car"), reply_markup=kb(CAR_BRANDS, cols=2))
        return CAR_BRAND

# ═══════════════════════════════════════════════════════════════════════════════
#  ВЕТКА 1: ИМЕННОЙ БРЕЛОК
# ═══════════════════════════════════════════════════════════════════════════════

async def get_name(update: Update, context):
    name = update.message.text.strip()
    if not name or len(name) > 15:
        await update.message.reply_text(t(context, "name_too_long"))
        return NAME
    context.user_data["name"] = name
    await update.message.reply_text(
        t(context, "choose_font"),
        reply_markup=kb(FONTS, cols=2),
    )
    return FONT

async def get_font(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["font"] = q.data
    await q.edit_message_text(
        t(context, "choose_font_size"),
        reply_markup=kb_data([(f"{s} мм", s) for s in FONT_SIZES], cols=3),
    )
    return FONT_SIZE

async def get_font_size(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["font_size"] = int(q.data)
    await q.edit_message_text(
        t(context, "choose_text_height"),
        parse_mode="Markdown",
        reply_markup=kb_data([(f"{h} мм", h) for h in TEXT_HEIGHTS], cols=3),
    )
    return TEXT_HEIGHT

async def get_text_height(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["text_height"] = float(q.data)
    await q.edit_message_text(
        t(context, "choose_back_height"),
        parse_mode="Markdown",
        reply_markup=kb_data([(f"{h} мм", h) for h in BACK_HEIGHTS], cols=4),
    )
    return BACK_HEIGHT

async def get_back_height(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["back_height"] = float(q.data)
    await q.edit_message_text(
        t(context, "choose_ring"),
        reply_markup=kb_data([(f"⌀ {r} мм", r) for r in RING_SIZES], cols=4),
    )
    return RING_SIZE

async def get_ring_size(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["ring_size"] = float(q.data)
    await q.edit_message_text(
        t(context, "choose_text_color"),
        reply_markup=kb(list(COLORS.keys()), cols=2),
    )
    return TEXT_COLOR

async def get_text_color(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["text_color_label"] = q.data
    context.user_data["text_color"] = COLORS[q.data]
    await q.edit_message_text(
        t(context, "choose_back_color"),
        reply_markup=kb(list(BACK_COLORS.keys()), cols=2),
    )
    return BACK_COLOR

async def get_back_color(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["back_color_label"] = q.data
    context.user_data["back_color"] = BACK_COLORS[q.data]

    await q.edit_message_text(t(context, "generating_preview"))

    d = context.user_data
    preview_path = generate_preview(
        d["name"], d["font"], d["text_color"], d["back_color"]
    )

    lang = d.get("lang", "ru")
    caption = (
        f"{T[lang]['your_keychain']}\n\n"
        f"{T[lang]['name_lbl']}: *{d['name']}*\n"
        f"{T[lang]['font_lbl']}: *{d['font']}*\n"
        f"{T[lang]['size_lbl']}: *{d['font_size']} мм*\n"
        f"{T[lang]['text_h_lbl']}: *{d['text_height']} мм*\n"
        f"{T[lang]['back_h_lbl']}: *{d['back_height']} мм*\n"
        f"{T[lang]['ring_lbl']}: *⌀{d['ring_size']} мм*\n"
        f"{T[lang]['text_c_lbl']}: *{d['text_color_label']}*\n"
        f"{T[lang]['back_c_lbl']}: *{d['back_color_label']}*"
    )
    confirm_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(context, "order_btn"),   callback_data="confirm")],
        [InlineKeyboardButton(t(context, "restart_btn"), callback_data="restart")],
    ])
    await q.message.delete()
    with open(preview_path, "rb") as f:
        await context.bot.send_photo(
            chat_id=q.message.chat_id, photo=f,
            caption=caption, parse_mode="Markdown",
            reply_markup=confirm_kb,
        )
    return CONFIRM

# ═══════════════════════════════════════════════════════════════════════════════
#  ВЕТКА 2: БРЕЛОК С ЛОГОТИПОМ
# ═══════════════════════════════════════════════════════════════════════════════

async def get_logo(update: Update, context):
    if not update.message.photo:
        await update.message.reply_text(t(context, "upload_logo"))
        return LOGO_UPLOAD
    photo = update.message.photo[-1]
    file  = await context.bot.get_file(photo.file_id)
    logo_path = f"/tmp/logo_{update.effective_user.id}.jpg"
    await file.download_to_drive(logo_path)
    context.user_data["logo_path"] = logo_path
    context.user_data["name"] = "Логотип"
    await update.message.reply_text(
        t(context, "choose_back_color"),
        reply_markup=kb(list(BACK_COLORS.keys()), cols=2),
    )
    return BACK_COLOR

# ═══════════════════════════════════════════════════════════════════════════════
#  ВЕТКА 3: БРЕЛОК С ЛОГОТИПОМ АВТО
# ═══════════════════════════════════════════════════════════════════════════════

async def get_car_brand(update: Update, context):
    q = update.callback_query; await q.answer()
    context.user_data["car_brand"] = q.data
    context.user_data["name"] = q.data
    context.user_data["font"] = "Pacifico"
    context.user_data["font_size"] = 16
    context.user_data["text_height"] = 2.0
    context.user_data["back_height"] = 3.0
    context.user_data["ring_size"] = 4.0
    await q.edit_message_text(
        t(context, "choose_back_color"),
        reply_markup=kb(list(BACK_COLORS.keys()), cols=2),
    )
    return BACK_COLOR

# ═══════════════════════════════════════════════════════════════════════════════
#  ПОДТВЕРЖДЕНИЕ И КОНТАКТ
# ═══════════════════════════════════════════════════════════════════════════════

async def confirm(update: Update, context):
    q = update.callback_query; await q.answer()
    if q.data == "restart":
        await q.message.delete()
        context.user_data.clear()
        lang_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🇷🇺 Русский", callback_data="ru"),
            InlineKeyboardButton("🇹🇯 Тоҷикӣ",  callback_data="tj"),
            InlineKeyboardButton("🇬🇧 English",  callback_data="en"),
        ]])
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text="🌍 Выберите язык / Забонро интихоб кунед / Choose language:",
            reply_markup=lang_kb,
        )
        return LANG
    await q.edit_message_caption(
        (q.message.caption or "") + "\n\n✅ Оформляем заказ!",
        parse_mode="Markdown",
    )
    await context.bot.send_message(
        chat_id=q.message.chat_id,
        text=t(context, "enter_contact"),
    )
    return CONTACT

async def get_contact(update: Update, context):
    contact = update.message.text.strip()
    d = context.user_data
    d["contact"] = contact

    msg = await update.message.reply_text(t(context, "generating_file"))

    # Определяем тип заказа
    order_type = d.get("type", "named")
    keychain_type_label = {
        "named": "🏷️ Именной",
        "logo":  "🎨 Логотип",
        "car":   "🚗 Авто",
    }.get(order_type, "Именной")

    file_3mf = None
    error_note = ""

    if order_type == "named":
        try:
            work_dir = WORK_DIR / str(update.effective_user.id)
            loop = asyncio.get_running_loop()
            file_3mf = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    functools.partial(
                        generate_keychain_3mf,
                        name=d["name"], font=d["font"],
                        back_color=d.get("back_color", "Black"),
                        text_color=d.get("text_color", "Pink"),
                        work_dir=work_dir,
                        font_size=d.get("font_size", 16),
                        text_height=d.get("text_height", 2.0),
                        back_height=d.get("back_height", 3.0),
                        ring_radius=d.get("ring_size", 4.0) / 2,
                    ),
                ),
                timeout=110,
            )
        except asyncio.TimeoutError:
            logger.error("3MF generation timed out")
            error_note = "\n⚠️ Генерация заняла слишком долго — сделайте файл вручную."
        except Exception as e:
            logger.error(f"3MF error: {e}")
            error_note = "\n⚠️ Файл не сгенерирован — детали в заказе."

    lang = d.get("lang", "ru")
    order_lines = [
        f"🆕 *НОВЫЙ ЗАКАЗ* — {keychain_type_label}{error_note}",
        f"",
        f"👤 {update.effective_user.full_name}"
        + (f" (@{update.effective_user.username})" if update.effective_user.username else ""),
        f"📞 {contact}",
        f"🌍 Язык: {lang.upper()}",
        f"",
    ]
    if order_type == "named":
        order_lines += [
            f"📛 Имя: *{d.get('name','?')}*",
            f"🔤 Шрифт: {d.get('font','?')}",
            f"📏 Размер: {d.get('font_size','?')} мм",
            f"📐 Высота текста: {d.get('text_height','?')} мм",
            f"🧱 Подложка: {d.get('back_height','?')} мм",
            f"🔘 Отверстие: ⌀{d.get('ring_size','?')} мм",
            f"🎨 Цвет текста: {d.get('text_color_label','?')}",
            f"🖤 Цвет подложки: {d.get('back_color_label','?')}",
        ]
    elif order_type == "logo":
        order_lines.append("🖼️ Клиент прислал логотип — см. фото выше")
    elif order_type == "car":
        order_lines.append(f"🚗 Марка авто: {d.get('car_brand','?')}")
        order_lines.append(f"🖤 Подложка: {d.get('back_color_label','?')}")

    order_text = "\n".join(order_lines)
    await context.bot.send_message(OWNER_CHAT_ID, order_text, parse_mode="Markdown")

    # Если есть логотип — пересылаем владельцу
    if order_type == "logo" and d.get("logo_path"):
        try:
            with open(d["logo_path"], "rb") as f:
                await context.bot.send_photo(OWNER_CHAT_ID, photo=f, caption="🖼️ Логотип клиента")
        except Exception: pass

    # Если есть 3MF — отправляем файл
    if file_3mf:
        with open(file_3mf, "rb") as f:
            await context.bot.send_document(
                OWNER_CHAT_ID, document=f,
                filename=f"{d['name']}_keychain.3mf",
                caption=(f"🖨️ *{d['name']}* | {d.get('font','')}\n"
                         f"AMS1=подложка ({d.get('back_color','')}) | "
                         f"AMS2=текст ({d.get('text_color','')})"),
                parse_mode="Markdown",
            )

    await msg.delete()
    await update.message.reply_text(t(context, "order_accepted"), parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context):
    await update.message.reply_text(t(context, "cancelled"))
    return ConversationHandler.END

async def error_handler(update, context):
    """Catches every unhandled error so the bot never crashes."""
    err = "".join(traceback.format_exception(
        type(context.error), context.error, context.error.__traceback__))[-1500:]
    logger.error(f"Unhandled error: {err}")
    try:
        await context.bot.send_message(
            OWNER_CHAT_ID,
            f"⚠️ Ошибка в боте (бот продолжает работать):\n\n<code>{err[-800:]}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass
    # Tell the user something went wrong, but keep the bot alive
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Произошла ошибка. Напишите /start чтобы начать заново."
            )
    except Exception:
        pass


async def post_init(app):
    try:
        await app.bot.send_message(chat_id=OWNER_CHAT_ID, text="🤖 Бот запущен и готов к работе!")
    except Exception as e:
        print(f"post_init error: {e}", flush=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:        [CallbackQueryHandler(get_lang)],
            TYPE:        [CallbackQueryHandler(get_type)],
            # Именной
            NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            FONT:        [CallbackQueryHandler(get_font)],
            FONT_SIZE:   [CallbackQueryHandler(get_font_size)],
            TEXT_HEIGHT: [CallbackQueryHandler(get_text_height)],
            BACK_HEIGHT: [CallbackQueryHandler(get_back_height)],
            RING_SIZE:   [CallbackQueryHandler(get_ring_size)],
            TEXT_COLOR:  [CallbackQueryHandler(get_text_color)],
            BACK_COLOR:  [CallbackQueryHandler(get_back_color)],
            # Логотип
            LOGO_UPLOAD: [MessageHandler(filters.PHOTO, get_logo),
                          MessageHandler(filters.TEXT & ~filters.COMMAND, get_logo)],
            # Авто
            CAR_BRAND:   [CallbackQueryHandler(get_car_brand)],
            # Финал
            CONFIRM:     [CallbackQueryHandler(confirm)],
            CONTACT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_error_handler(error_handler)
    print("=== POLLING STARTED ===", flush=True)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"FATAL, restarting in 10s: {e}", flush=True)
            tg_send(f"🔄 Бот перезапускается после ошибки: {str(e)[:200]}")
            import time; time.sleep(10)
