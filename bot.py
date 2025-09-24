import logging
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Список ID админов
ADMIN_IDS = {123456789}  # Замени на свой ID

# База данных
user_db = set()

# ================== ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    user_db.add(user.id)
    
    # Создаем клавиатуру с кнопкой меню
    keyboard = [[KeyboardButton("/start")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, 
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот-помощник для партнеров.",
        reply_markup=reply_markup
    )
    
    await show_main_menu(update, user)

async def show_main_menu(update, user=None):
    """Показывает главное меню."""
    if user is None:
        user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("О платформе", callback_data="menu_about")],
        [InlineKeyboardButton("Тарифы и условия", callback_data="menu_tariffs")],
        [InlineKeyboardButton("Контакты поддержки", callback_data="menu_contacts")],
        [InlineKeyboardButton("Полезные материалы", callback_data="menu_materials")],
        [InlineKeyboardButton("FAQ", callback_data="menu_faq")],
        [
            InlineKeyboardButton("Статистика: 30 дней", callback_data="stats_30"),
            InlineKeyboardButton("Статистика: 7 дней", callback_data="stats_7")
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message'):
        await update.message.reply_text(
            "Выбери, что тебя интересует:",
            reply_markup=reply_markup
        )
    else:
        await update.edit_message_text(
            "Главное меню. Выбери, что тебя интересует:",
            reply_markup=reply_markup
        )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки меню."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await show_main_menu(query, query.from_user)
        return

    elif data == "menu_about":
        text = ("<b>О нашей платформе</b>\n\n"
                "Здесь будет краткое и ясное описание вашей платформы.")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "menu_tariffs":
        text = ("<b>Тарифы и условия</b>\n\n"
                "• <b>Тариф Старт</b> - бесплатно\n"
                "• <b>Тариф Профи</b> - 1000₽/мес\n"
                "• <b>Тариф Бизнес</b> - 3000₽/мес")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "menu_contacts":
        text = ("<b>Поддержка</b>\n\n"
                "📧 Email: support@example.com\n"
                "👥 Telegram: @support_username\n"
                "🌐 Сайт: example.com")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "menu_materials":
        text = "<b>Полезные материалы</b>\n\nВыбери нужный материал:"
        keyboard = [
            [InlineKeyboardButton("📊 Презентация", url="https://example.com/presentation.pdf")],
            [InlineKeyboardButton("📖 Инструкция", url="https://example.com/guide.pdf")],
            [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "menu_faq":
        text = ("<b>FAQ</b>\n\n"
                "❓ <b>Как начать работу?</b>\n"
                "👉 Зарегистрируйтесь на платформе\n\n"
                "❓ <b>Где найти документацию?</b>\n"
                "👉 В разделе 'Полезные материалы'")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "stats_30":
        text = ("<b>Статистика за 30 дней</b>\n\n"
                "📈 Новых пользователей: 150\n"
                "💼 Завершенных сделок: 45\n"
                "💰 Общий оборот: 500,000₽")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "stats_7":
        text = ("<b>Статистика за 7 дней</b>\n\n"
                "📈 Новых пользователей: 35\n"
                "💼 Завершенных сделок: 12\n"
                "💰 Общий оборот: 120,000₽")
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== АДМИН-ФУНКЦИОНАЛ ==================

def is_admin(user_id: int):
    return user_id in ADMIN_IDS

async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("У вас нет прав для этой команды.")
        return

    try:
        new_admin_id = int(context.args[0])
        ADMIN_IDS.add(new_admin_id)
        await update.message.reply_text(f"Пользователь {new_admin_id} добавлен в админы.")
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /add_admin <user_id>")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID or not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("ОК! Пришли мне сообщение для рассылки.")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID or not is_admin(update.effective_user.id):
        return

    message = update.message
    success = 0
    errors = 0
    
    for user_id in user_db:
        try:
            if message.text:
                await context.bot.send_message(chat_id=user_id, text=message.text, parse_mode="HTML")
            elif message.photo:
                await context.bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id, caption=message.caption)
            elif message.document:
                await context.bot.send_document(chat_id=user_id, document=message.document.file_id, caption=message.caption)
            else:
                await context.bot.copy_message(chat_id=user_id, from_chat_id=ADMIN_CHAT_ID, message_id=message.message_id)
            success += 1
        except Exception as e:
            errors += 1

    await update.message.reply_text(f"✅ Рассылка завершена.\nУспешно: {success}\nОшибок: {errors}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_menu))
    application.add_handler(CommandHandler("add_admin", admin_add))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(MessageHandler(filters.Chat(ADMIN_CHAT_ID) & filters.ALL, handle_admin_message))

    application.run_polling()

if __name__ == "__main__":
    main()