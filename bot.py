import logging
import os
import sqlite3
from datetime import datetime
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

# ⚠️ ЗАМЕНИТЕ ЭТОТ ID НА СВОЙ!
INITIAL_ADMIN_ID = 7727813191

# Глобальный набор админов (загружается из БД)
ADMIN_IDS = set()

# ================== БАЗА ДАННЫХ ==================

def init_db():
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS command_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            command TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date DATE,
            actions_count INTEGER DEFAULT 1,
            UNIQUE(user_id, date)
        )
    ''')
    
    # Добавляем первоначального админа
    cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (INITIAL_ADMIN_ID,))
    
    conn.commit()
    conn.close()

def load_admins_from_db():
    global ADMIN_IDS
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM admins')
    ADMIN_IDS = {row[0] for row in cursor.fetchall()}
    conn.close()
    logger.info(f"Загружено админов: {len(ADMIN_IDS)}")

def add_user_to_db(user_id: int):
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def add_group_to_db(chat_id: int, title: str = ""):
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO groups (chat_id, title) VALUES (?, ?)', (chat_id, title))
    conn.commit()
    conn.close()

def add_admin_to_db(user_id: int):
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def log_command_usage(user_id: int, command: str):
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO command_stats (user_id, command) VALUES (?, ?)', (user_id, command))
    conn.commit()
    conn.close()

def log_user_activity(user_id: int):
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute('''
        INSERT OR REPLACE INTO user_activity (user_id, date, actions_count)
        VALUES (?, ?, COALESCE((SELECT actions_count FROM user_activity WHERE user_id = ? AND date = ?), 0) + 1)
    ''', (user_id, today, user_id, today))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_all_groups():
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM groups')
    groups = [row[0] for row in cursor.fetchall()]
    conn.close()
    return groups

def is_admin(user_id: int):
    return user_id in ADMIN_IDS

# ================== ОСНОВНЫЕ ФУНКЦИИ ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user_to_db(user.id)
    log_command_usage(user.id, 'start')
    log_user_activity(user.id)
    
    keyboard = [[KeyboardButton("/start")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}! Я бот-помощник для партнеров.",
        reply_markup=reply_markup
    )
    await show_main_menu(update, user)

async def show_main_menu(update, user=None):
    if user is None:
        user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📋 О платформе", callback_data="menu_about")],
        [InlineKeyboardButton("💼 Условия работы", callback_data="menu_conditions")],
        [InlineKeyboardButton("📞 Контакты поддержки", callback_data="menu_contacts")],
        [InlineKeyboardButton("📚 Полезные материалы", callback_data="menu_materials")],
        [InlineKeyboardButton("❓ FAQ", callback_data="menu_faq")],
        [
            InlineKeyboardButton("📊 Статистика: 30 дней", callback_data="stats_30"),
            InlineKeyboardButton("📈 Статистика: 7 дней", callback_data="stats_7")
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update, 'message'):
        await update.message.reply_text("🎯 Выбери, что тебя интересует:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("🏠 Главное меню. Выбери, что тебя интересует:", reply_markup=reply_markup)

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    log_command_usage(user.id, data)
    log_user_activity(user.id)

    try:
        if data == "main_menu":
            await show_main_menu(query, user)
            return

        elif data == "menu_about":
            text = (
                "<b>🚀 О нашей платформе</b>\n\n"
                "🔥 <a href='https://wincraft.casino/'>Wincraft Casino</a> — это динамично развивающийся бренд, "
                "который за короткий срок стал узнаваемым и востребованным среди партнёров и игроков по всему миру.\n\n"
                "💎 Мы не просто следуем трендам — мы создаём их. Наша команда оперативно адаптирует продукт под "
                "современные ожидания аудитории, внедряя инновации и сохраняя высочайший уровень сервиса.\n\n"
                "🤝 Каждому партнёру — индивидуальный подход. Мы верим, что успех строится на доверии, "
                "прозрачности и гибкости. Готовы расти вместе с вами!\n\n"
                "🔗 <b>Наша платформа:</b> https://wincraft.casino/\n"
                "🔗 <b>Партнёрская программа:</b> https://affwin.partners/"
            )
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
            await query.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )

        elif data == "menu_conditions":
            text = "<b>💼 Условия работы</b>\n\nВыберите модель сотрудничества:"
            keyboard = [
                [InlineKeyboardButton("💰 CPA", callback_data="conditions_cpa")],
                [InlineKeyboardButton("📊 RS", callback_data="conditions_rs")],
                [InlineKeyboardButton("🔄 Hybrid", callback_data="conditions_hybrid")],
                [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "conditions_cpa":
            text = ("<b>💰 Модель CPA (Cost Per Action)</b>\n\n"
                    "✅ <b>Преимущества:</b>\n"
                    "• Оплата за целевое действие\n"
                    "• Минимальные риски для партнера\n"
                    "• Подходит для начинающих\n"
                    "• Стабильный доход\n\n"
                    "💵 <b>Ставки по FB нашим основным гео:</b>\n"
                    "┌────────────┬──────────────────┬───────┐\n"
                    "│   Тир      │     Страна       │ Ставка│\n"
                    "├────────────┼──────────────────┼───────┤\n"
                    "│    T1      │ FI (Finland)     │  170  │\n"
                    "│    T1      │ CH (Switzerland) │  295  │\n"
                    "│    T3      │ KG (Kyrgyzstan)  │  60   │\n"
                    "│    T3      │ AM (Armenia)     │  60   │\n"
                    "│    T2      │ HU (Hungary)     │  160  │\n"
                    "│    T3      │ GE (Georgia)     │  80   │\n"
                    "│    T2      │ PL (Poland)      │  150  │\n"
                    "│    T2      │ RS (Serbia)      │  75   │\n"
                    "│    T1      │ CA (Canada)      │  220  │\n"
                    "│    T1      │ IE (Ireland)     │  255  │\n"
                    "│    T1      │ DE (Germany)     │  220  │\n"
                    "│    T1      │ SE (Sweden)      │  215  │\n"
                    "│    T2      │ SI (Slovenia)    │  130  │\n"
                    "│    T2      │ SK (Slovakia)    │  130  │\n"
                    "│    T3      │ TJ (Tajikistan)  │  65   │\n"
                    "│    T3      │ MD (Moldova)     │  60   │\n"
                    "│    T2      │ GR (Greece)      │  150  │\n"
                    "│    T1      │ GB (UK)          │  225  │\n"
                    "│    T1      │ FR (France)      │  185  │\n"
                    "└────────────┴──────────────────┴───────┘\n\n"
                    "📊 <b>Полная таблица ставок:</b>\n"
                    "https://docs.google.com/spreadsheets/d/1ObMQlGiY7PbxA0ZdQkZRjXvpbp5clpM4wA2X5CUvl5A/edit?usp=sharing\n\n"
                    "💬 <b>Другие варианты сотрудничества можем обсудить индивидуально</b>")
            keyboard = [[InlineKeyboardButton("◀️ Назад к условиям", callback_data="menu_conditions")]]
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "conditions_rs":
            text = ("<b>📊 Модель RS (Revenue Share)</b>\n\n"
                    "✨ <b>Премиум условия для опытных партнеров</b>\n\n"
                    "✅ <b>Преимущества:</b>\n"
                    "• Процент от оборота клиента\n"
                    "• Высокий потенциал дохода\n"
                    "• Долгосрочное сотрудничество\n"
                    "• Персональный подход\n\n"
                    "🌟 <b>Индивидуальные условия:</b>\n"
                    "• Гибкие процентные ставки\n"
                    "• Эксклюзивные предложения\n"
                    "• Приоритетная поддержка\n\n"
                    "👥 <b>Обсудить индивидуальные условия:</b>\n"
                    "• @makswincraft 🚀\n"
                    "• @dosiTG 💼\n"
                    "• @hugewinaffs 🌟\n\n"
                    "<i>Пример: процент от депозитов, повторных покупок, LTV клиента</i>")
            keyboard = [
                [InlineKeyboardButton("💬 Написать @makswincraft", url="tg://resolve?domain=makswincraft")],
                [InlineKeyboardButton("💬 Написать @dosiTG", url="tg://resolve?domain=dosiTG")],
                [InlineKeyboardButton("💬 Написать @hugewinaffs", url="tg://resolve?domain=hugewinaffs")],
                [InlineKeyboardButton("◀️ Назад к условиям", callback_data="menu_conditions")]
            ]
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "conditions_hybrid":
            text = ("<b>🔄 Гибридная модель (CPA + RS)</b>\n\n"
                    "🎯 <b>Идеальный баланс для максимальной эффективности</b>\n\n"
                    "✅ <b>Преимущества:</b>\n"
                    "• Сочетание стабильности CPA и потенциала RS\n"
                    "• Гибкие условия под ваши задачи\n"
                    "• Индивидуальный подход\n"
                    "• Оптимальный риск/доход\n\n"
                    "💫 <b>Варианты сотрудничества:</b>\n"
                    "• CPA + процент от оборота\n"
                    "• Фиксированный бонус за качество\n"
                    "• Многоуровневая система вознаграждений\n\n"
                    "👥 <b>Обсудить индивидуальные условия:</b>\n"
                    "• @makswincraft 🚀\n"
                    "• @dosiTG 💼\n"
                    "• @hugewinaffs 🌟\n\n"
                    "<i>Пример: фикс за регистрацию + % от оборота, ступенчатая система</i>")
            keyboard = [
                [InlineKeyboardButton("💬 Написать @makswincraft", url="tg://resolve?domain=makswincraft")],
                [InlineKeyboardButton("💬 Написать @dosiTG", url="tg://resolve?domain=dosiTG")],
                [InlineKeyboardButton("💬 Написать @hugewinaffs", url="tg://resolve?domain=hugewinaffs")],
                [InlineKeyboardButton("◀️ Назад к условиям", callback_data="menu_conditions")]
            ]
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "menu_contacts":
            text = (
                "📞 Контакты поддержки\n\n"
                "Мы всегда на связи и готовы помочь — в любой ситуации и в любое время!\n\n"
                "🕒 Работаем 24/7\n"
                "Ваш запрос будет обработан максимально оперативно.\n\n"
                "👨‍💼 Ваши персональные менеджеры:\n"
                "• @makswincraft🚀\n"
                "• @dosiTG 💼\n"
                "• @hugewinaffs🌟\n\n"
                "Пишите смело — мы настроены на долгое и взаимовыгодное сотрудничество!"
            )
            keyboard = [
                [InlineKeyboardButton("🚀 Написать @makswincraft", url="https://t.me/makswincraft")],
                [InlineKeyboardButton("💼 Написать @dosiTG", url="https://t.me/dosiTG")],
                [InlineKeyboardButton("🌟 Написать @hugewinaffs", url="https://t.me/hugewinaffs")],
                [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "menu_materials":
            text = "📚 Полезные материалы\n\nВыберите раздел:"
            keyboard = [
                [InlineKeyboardButton("🔗 Лендинги", callback_data="materials_landings")],
                [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
            ]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "materials_landings":
            text = "🔗 Доступные лендинги и демо-игры"
            keyboard = [
                [InlineKeyboardButton("🏠 Главная (EN)", url="https://wincraft.casino/")],
                [InlineKeyboardButton("🇫🇷 Главная (FR)", url="https://www.wincraft.casino/fr")],
                [InlineKeyboardButton("🎯 Регистрация", url="https://wincraft.casino/?modal=signup")],
                [InlineKeyboardButton("🎰 Популярные слоты", url="https://wincraft.casino/categories/games/popular")],
                [InlineKeyboardButton("🎁 Промо / Бонусы", url="https://wincraft.casino/promotions")],
                [InlineKeyboardButton("🎡 Wheel of Fortune", url="https://wincraft.casino/wheel-of-fortune")],
                [InlineKeyboardButton("👧 Wheel of Fortune (Girl)", url="https://wincraft.casino/wheel-of-fortune-girl")],
                [InlineKeyboardButton("🎮 Демо-игры", callback_data="landings_demos")],
                [InlineKeyboardButton("◀️ Назад к материалам", callback_data="menu_materials")]
            ]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "landings_demos":
            text = "🎮 Демо-версии популярных слотов"
            keyboard = [
                [InlineKeyboardButton("📖 Book of Dead", url="https://wincraft.casino/casino/games/12406?demo=true")],
                [InlineKeyboardButton("⛰️ Gates of Olympus", url="https://wincraft.casino/casino/games/20502?demo=true")],
                [InlineKeyboardButton("⚔️ Zeus vs Hades", url="https://wincraft.casino/casino/games/14475?demo=true")],
                [InlineKeyboardButton("🏡 The Dog House", url="https://wincraft.casino/casino/games/9535?demo=true")],
                [InlineKeyboardButton("🍬 Sweet Bonanza", url="https://wincraft.casino/casino/games/20504?demo=true")],
                [InlineKeyboardButton("✋ Hand of Midas", url="https://wincraft.casino/casino/games/20709?demo=true")],
                [InlineKeyboardButton("◀️ Назад к лендингам", callback_data="materials_landings")]
            ]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "menu_faq":
            text = (
                "❓ Часто задаваемые вопросы\n\n"
                "01. За какие лиды вы платите?\n"
                "— Motivated-трафик\n"
                "— Мультиаккаунты (один ID/IP/устройство → несколько регистраций)\n"
                "— Лиды с подозрительной воронкой (высокая рега, но нет депозитов)\n\n"
                "02. Оценка трафика — в потоке или по игрокам?\n"
                "— Оцениваем каждого игрока индивидуально. Если из 20 — 12 сделали FTD, оплатим за 12.\n\n"
                "03. Есть ли холд на игроков?\n"
                "— Нет. Все FTD, совершённые до конца отчётного периода, оплачиваются.\n\n"
                "04. Сколько дней с клика до депозита?\n"
                "— Максимум 30 дней. Если депозит в этот срок — лид валидный.\n\n"
                "05. Сроки сверки и выплат?\n"
                "— Сверка до конца месяца, выплата — до 10-го числа следующего месяца.\n"
                "— На больших объёмах — возможны выплаты 2–3 раза в месяц.\n\n"
                "06. Тестовые капы?\n"
                "— 10–20 FTD на тест. Далее — до 100 FTD. При хорошем качестве — без ограничений.\n\n"
                "07. Минимальная сумма выплаты?\n"
                "— 500 USD.\n\n"
                "08. Способы оплаты?\n"
                "— USDT / USDC. Инвойс, KYC, AML — не требуются.\n\n"
                "09. Задержка postback?\n"
                "— Минимальная. Данные обновляются 24/7 в реальном времени.\n\n"
                "10. Критерии оценки трафика?\n"
                "— CR клик → регистрация / FTD\n"
                "— Доля активных игроков и ретеншн\n"
                "— Коэффициент возвратов\n"
                "— Источники, гео, устройства, стабильность заливов\n\n"
                "11. Регистрация в одном периоде, депозит — в следующем?\n"
                "— FTD засчитывается в период депозита (в рамках 30 дней) и оплачивается.\n\n"
                "12. Как оплачивается перелив?\n"
                "— Только по согласованию. Качественный перелив — оплачиваем.\n\n"
                "13. Показатели через 30 дней?\n"
                "— RetDep ≥30% от FTD\n"
                "— Средний чек — x2–x2.5 от мин. депозита\n\n"
                "16. KPI на тесте?\n"
                "— На тесте KPI не блокирующие. Ориентиры:\n"
                "  • CR клик → регистрация: 20–30%\n"
                "  • CR регистрация → депозит: 5–10%\n"
                "  • Retention Day 7: от 25%\n"
                "— Оплата по валидным FTD — в любом случае.\n\n"
                "17. Принимаете ли инфлюенсеров и PPS-бренд?\n"
                "— PPC, SEO, Facebook — да. Инфлюенсеры и PPS-бренд — по согласованию.\n\n"
                "18. Hard и Soft KPI?\n"
                "— Soft: CR рега 20–30%, CR FTD 5–10%, Ret7 >25%\n"
                "— Hard: RetDep >30%, ARPU ≥x2 от мин. депа, ROI на D7/D14\n\n"
                "Контакты для уточнений:\n"
                "@makswincraft | @dosiTG | @hugewinaffs"
            )
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "stats_30":
            text = ("<b>📊 Статистика за 30 дней</b>\n\n"
                    "📆 Данные обновляются 1-го и 15-го числа каждого месяца.\n\n"
                    "🖼️ Скоро: графики Click2Reg и Reg2Dep!")
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "stats_7":
            text = ("<b>📈 Статистика за 7 дней</b>\n\n"
                    "📆 Данные обновляются каждое утро по понедельникам.\n\n"
                    "🖼️ Скоро: недельные графики конверсий!")
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logger.error(f"Ошибка в меню: {e}")
        await query.message.reply_text("⚠️ Ошибка. Попробуйте позже.")

# ================== АДМИН-МЕНЮ ==================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа.")
        return
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка по пользователям", callback_data="admin_broadcast_users")],
        [InlineKeyboardButton("📤 Рассылка по группам", callback_data="admin_broadcast_groups")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👤 Добавить админа", callback_data="admin_add_admin")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")]
    ]
    await update.message.reply_text("🔐 Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён.", show_alert=True)
        return

    if data == "admin_close":
        await query.edit_message_text("Админ-панель закрыта.")
    elif data == "admin_broadcast_users":
        context.user_data['admin_action'] = 'broadcast_users'
        await query.edit_message_text("Пришлите сообщение для рассылки по пользователям.")
    elif data == "admin_broadcast_groups":
        context.user_data['admin_action'] = 'broadcast_groups'
        await query.edit_message_text("Пришлите сообщение для рассылки по группам.")
    elif data == "admin_stats":
        await query.edit_message_text("📊 Аналитика доступна в веб-панели.")
    elif data == "admin_add_admin":
        context.user_data['admin_action'] = 'add_admin'
        await query.edit_message_text("Введите Telegram ID нового админа:")
    else:
        await query.edit_message_text("Неизвестная команда.")

async def handle_admin_action_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    action = context.user_data.get('admin_action')
    message = update.message

    if action == 'broadcast_users':
        users = get_all_users()
        success = errors = 0
        for uid in users:
            try:
                if message.text:
                    await context.bot.send_message(chat_id=uid, text=message.text, parse_mode="HTML")
                elif message.photo:
                    await context.bot.send_photo(chat_id=uid, photo=message.photo[-1].file_id, caption=message.caption)
                elif message.document:
                    await context.bot.send_document(chat_id=uid, document=message.document.file_id, caption=message.caption)
                else:
                    await context.bot.copy_message(chat_id=uid, from_chat_id=message.chat_id, message_id=message.message_id)
                success += 1
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {uid}: {e}")
                errors += 1
        await message.reply_text(f"✅ Рассылка завершена.\nУспешно: {success}\nОшибок: {errors}")
        context.user_data.pop('admin_action', None)

    elif action == 'broadcast_groups':
        groups = get_all_groups()
        if not groups:
            await message.reply_text("Нет сохранённых групп.")
            return
        success = errors = 0
        for gid in groups:
            try:
                await context.bot.copy_message(chat_id=gid, from_chat_id=message.chat_id, message_id=message.message_id)
                success += 1
            except Exception as e:
                logger.error(f"Ошибка отправки в группу {gid}: {e}")
                errors += 1
        await message.reply_text(f"📤 Рассылка в группы завершена.\nУспешно: {success}\nОшибок: {errors}")
        context.user_data.pop('admin_action', None)

    elif action == 'add_admin':
        try:
            new_admin_id = int(message.text.strip())
            add_admin_to_db(new_admin_id)
            ADMIN_IDS.add(new_admin_id)
            await message.reply_text(f"✅ Пользователь {new_admin_id} добавлен в админы!")
        except ValueError:
            await message.reply_text("❌ Неверный ID. Отправьте число.")
        context.user_data.pop('admin_action', None)

# ================== ГРУППЫ ==================

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                chat = update.effective_chat
                add_group_to_db(chat.id, chat.title or f"Group {chat.id}")
                await update.message.reply_text("🤖 Спасибо за добавление! Я готов к работе.")

# ================== ЗАПУСК ==================

def main():
    init_db()
    load_admins_from_db()

    application = Application.builder().token(BOT_TOKEN).build()

    # 1. Сначала — команды (они имеют высший приоритет)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))

    # 2. Потом — callback-обработчики
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_menu, pattern="^(?!admin_).*$"))

    # 3. И только потом — обработчики "остальных сообщений"
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.User(user_id=list(ADMIN_IDS) if ADMIN_IDS else [INITIAL_ADMIN_ID]),
        handle_admin_action_message
    ))

    # Группы
    application.add_handler(MessageHandler(
        filters.ChatType.GROUP | filters.ChatType.SUPERGROUP,
        handle_group_message
    ))

    application.run_polling()

if __name__ == "__main__":
    main()