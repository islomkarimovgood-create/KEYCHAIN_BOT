import os
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
)
from preview import generate_preview
from generator import generate_keychain_3mf

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_CHAT_ID = os.environ["OWNER_CHAT_ID"]
WORK_DIR = Path("/tmp/keychains")
PREVIEW_DIR = Path("/tmp/previews")

# Conversation states
NAME, FONT, TEXT_COLOR, BACK_COLOR, CONFIRM, CONTACT = range(6)

FONTS = [
    "Pacifico", "Lobster", "Cookie", "Dancing Script",
    "Chewy", "DynaPuff", "Courgette", "Bangers",
]

COLORS = {
    "Розовый 🩷": "Pink",
    "Голубой 💙": "Turquoise",
    "Фиолетовый 💜": "Purple",
    "Красный ❤️": "Red",
    "Зелёный 💚": "Green",
    "Жёлтый 💛": "Yellow",
    "Оранжевый 🧡": "Orange",
    "Белый ⬜": "White",
}

BACK_COLORS = {
    "Чёрный ⬛": "Black",
    "Белый ⬜": "White",
    "Серый 🔘": "Gray",
}


def kb(items, cols=2):
    buttons = [InlineKeyboardButton(t, callback_data=t) for t in items]
    rows = [buttons[i : i + cols] for i in range(0, len(buttons), cols)]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Привет! Создадим именной брелок для 3D-печати.\n\n"
        "✏️ Введите имя для брелка (макс. 15 символов):"
    )
    return NAME


async def get_name(update: Update, context):
    name = update.message.text.strip()
    if not name or len(name) > 15:
        await update.message.reply_text(
            "⚠️ Имя должно быть от 1 до 15 символов. Попробуйте ещё раз:"
        )
        return NAME
    context.user_data["name"] = name
    await update.message.reply_text(
        f"✅ Имя: *{name}*\n\n🔤 Выберите шрифт:",
        parse_mode="Markdown",
        reply_markup=kb(FONTS),
    )
    return FONT


async def get_font(update: Update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["font"] = q.data
    await q.edit_message_text(
        f"✅ Шрифт: *{q.data}*\n\n🎨 Выберите цвет текста:",
        parse_mode="Markdown",
        reply_markup=kb(list(COLORS.keys())),
    )
    return TEXT_COLOR


async def get_text_color(update: Update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["text_color_ru"] = q.data
    context.user_data["text_color"] = COLORS[q.data]
    await q.edit_message_text(
        f"✅ Цвет текста: *{q.data}*\n\n🖤 Выберите цвет подложки:",
        parse_mode="Markdown",
        reply_markup=kb(list(BACK_COLORS.keys())),
    )
    return BACK_COLOR


async def get_back_color(update: Update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["back_color_ru"] = q.data
    context.user_data["back_color"] = BACK_COLORS[q.data]

    await q.edit_message_text("⏳ Генерирую превью...")

    d = context.user_data
    preview_path = generate_preview(
        d["name"], d["font"], d["text_color"], d["back_color"]
    )

    caption = (
        f"👀 *Ваш брелок:*\n\n"
        f"📛 Имя: *{d['name']}*\n"
        f"🔤 Шрифт: *{d['font']}*\n"
        f"🎨 Текст: *{d['text_color_ru']}*\n"
        f"🖤 Подложка: *{d['back_color_ru']}*"
    )
    confirm_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Заказать", callback_data="confirm")],
        [InlineKeyboardButton("🔄 Начать заново", callback_data="restart")],
    ])

    await q.message.delete()
    with open(preview_path, "rb") as f:
        await context.bot.send_photo(
            chat_id=q.message.chat_id,
            photo=f,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=confirm_kb,
        )
    return CONFIRM


async def confirm(update: Update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "restart":
        await q.message.delete()
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text="🔄 Начнём заново!\n\n✏️ Введите имя для брелка:",
        )
        context.user_data.clear()
        return NAME

    await q.edit_message_caption(
        q.message.caption + "\n\n✅ *Оформляем заказ!*",
        parse_mode="Markdown",
    )
    await context.bot.send_message(
        chat_id=q.message.chat_id,
        text="📞 Введите ваш контакт для связи\n(номер телефона или @username в Telegram):",
    )
    return CONTACT


async def get_contact(update: Update, context):
    contact = update.message.text.strip()
    d = context.user_data
    d["contact"] = contact

    msg = await update.message.reply_text(
        "⏳ Генерирую файл для Bambu Studio...\n_Это займёт ~30 секунд_",
        parse_mode="Markdown",
    )

    work_dir = WORK_DIR / str(update.effective_user.id)
    file_3mf = None
    error_note = ""

    try:
        file_3mf = generate_keychain_3mf(
            name=d["name"],
            font=d["font"],
            back_color=d["back_color"],
            text_color=d["text_color"],
            work_dir=work_dir,
        )
    except Exception as e:
        logger.error(f"3MF generation failed: {e}")
        error_note = "\n⚠️ Файл не сгенерирован — сделайте вручную по параметрам."

    # Notify owner
    order_text = (
        f"🆕 *НОВЫЙ ЗАКАЗ*{error_note}\n\n"
        f"👤 {update.effective_user.full_name}"
        + (f" (@{update.effective_user.username})" if update.effective_user.username else "")
        + f"\n📞 Контакт: {contact}\n\n"
        f"📛 Имя: *{d['name']}*\n"
        f"🔤 Шрифт: {d['font']}\n"
        f"🎨 Текст: {d['text_color_ru']}\n"
        f"🖤 Подложка: {d['back_color_ru']}"
    )
    await context.bot.send_message(OWNER_CHAT_ID, order_text, parse_mode="Markdown")

    if file_3mf:
        with open(file_3mf, "rb") as f:
            await context.bot.send_document(
                chat_id=OWNER_CHAT_ID,
                document=f,
                filename=f"{d['name']}_keychain.3mf",
                caption=(
                    f"🖨️ *{d['name']}* | {d['font']}\n"
                    f"AMS слот 1 → подложка ({d['back_color']})\n"
                    f"AMS слот 2 → текст ({d['text_color']})"
                ),
                parse_mode="Markdown",
            )

    await msg.delete()
    await update.message.reply_text(
        "✅ *Заказ принят!*\n\n"
        "Мы свяжемся с вами в ближайшее время для уточнения деталей и стоимости. 🎉\n\n"
        "Напишите /start чтобы создать ещё один брелок.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel(update: Update, context):
    await update.message.reply_text(
        "❌ Отменено. Напишите /start чтобы начать заново."
    )
    return ConversationHandler.END


def main():
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME:       [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            FONT:       [CallbackQueryHandler(get_font)],
            TEXT_COLOR: [CallbackQueryHandler(get_text_color)],
            BACK_COLOR: [CallbackQueryHandler(get_back_color)],
            CONFIRM:    [CallbackQueryHandler(confirm)],
            CONTACT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
