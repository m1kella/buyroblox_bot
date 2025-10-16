from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from database import Database
from config import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
db = Database()

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return user_id == Config.ADMIN_ID_INT

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает админ-панель"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к админ-панели")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Базовая статистика", callback_data="admin_stats"),
         InlineKeyboardButton("📈 Детальная статистика", callback_data="admin_detailed_stats")],
        [InlineKeyboardButton("🎮 Управление скинами", callback_data="admin_skins"),
         InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton("➕ Добавить скин", callback_data="admin_add_skin")],
        [InlineKeyboardButton("💰 Изменить баланс", callback_data="admin_change_balance")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚙️ Админ-панель\n\nВыберите действие:",
        reply_markup=reply_markup
    )

async def admin_panel_main(query):
    """Возвращает в главное меню админ-панели"""
    keyboard = [
        [InlineKeyboardButton("📊 Базовая статистика", callback_data="admin_stats"),
         InlineKeyboardButton("📈 Детальная статистика", callback_data="admin_detailed_stats")],
        [InlineKeyboardButton("🎮 Управление скинами", callback_data="admin_skins"),
         InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton("➕ Добавить скин", callback_data="admin_add_skin")],
        [InlineKeyboardButton("💰 Изменить баланс", callback_data="admin_change_balance")]
    ]

    await query.edit_message_text(
        "⚙️ Админ-панель\n\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок в админ-панели"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа")
        return

    callback_data = query.data

    # Обработка кнопок с timestamp
    if callback_data.startswith("admin_stats"):
        await show_admin_stats(query)
    elif callback_data.startswith("admin_detailed_stats"):
        await show_detailed_stats(query)
    elif callback_data == "admin_skins":
        await show_skin_management(query)
    elif callback_data == "admin_users":
        await show_user_management(query)
    elif callback_data == "admin_add_skin":
        await start_add_skin(query, context)
    elif callback_data == "admin_change_balance":
        await start_change_balance(query, context)
    elif callback_data == "admin_main":
        await admin_panel_main(query)
    elif callback_data == "catalog":
        from handlers import show_catalog_from_button
        await show_catalog_from_button(query, context)
    elif callback_data == "admin_delete_skin":
        await start_delete_skin(query, context)

async def show_admin_stats(query):
    """Показывает статистику бота"""
    stats = db.get_bot_stats()

    # Добавляем время обновления чтобы сообщение всегда было разным
    import time
    timestamp = int(time.time())

    stats_text = (
        f"📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🎮 Всего скинов: {stats['total_skins']}\n"
        f"🛒 Всего покупок: {stats['total_purchases']}\n"
        f"💰 Общий оборот: {stats['total_revenue']} ₽\n"
        f"\n🕐 Обновлено: {datetime.now().strftime('%H:%M:%S')}"  # Добавляем время
    )

    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data=f"admin_stats_{timestamp}")],  # Добавляем timestamp
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_main")]
    ]

    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_add_skin(query, context):
    """Начинает процесс добавления скина"""
    await query.edit_message_text(
        "➕ Добавление нового скина\n\n"
        "Введите данные скина в формате:\n"
        "`название | описание | цена | редкость | количество | roblox_id | image_url`\n\n"
        "Пример:\n"
        "`Огненный меч | Мощное оружие | 1500 | Godly | 5 | fire_sword_001 | https://example.com/fire.jpg`\n\n"
        "Редкости: Legendary, Godly, Ancient\n"
        "Для фото используйте прямые ссылки на изображения",
        parse_mode='Markdown'
    )

    context.user_data['waiting_for_skin'] = True

async def show_detailed_stats(query):
    """Показывает детальную статистику"""
    stats = db.get_detailed_stats()

    import time
    timestamp = int(time.time())

    stats_text = f"📊 Детальная статистика\n\n"

    # Основная статистика
    stats_text += f"👥 Всего пользователей: {stats['total_users']}\n"
    stats_text += f"🎮 Всего скинов: {stats['total_skins']}\n"
    stats_text += f"🛒 Всего покупок: {stats['total_purchases']}\n"
    stats_text += f"💰 Общий оборот: {stats['total_revenue']} ₽\n\n"

    # Статистика по редкостям
    stats_text += "📈 По редкостям:\n"
    for rarity_stat in stats['rarity_stats']:
        stats_text += f"• {rarity_stat['rarity']}: {rarity_stat['count']} скинов\n"

    stats_text += "\n🏆 Топ пользователей:\n"
    for i, user in enumerate(stats['top_users'][:5], 1):
        username = f"@{user['username']}" if user['username'] else user['first_name']
        stats_text += f"{i}. {username}: {user['balance']} ₽\n"

    stats_text += "\n🔥 Популярные скины:\n"
    for i, skin in enumerate(stats['popular_skins'][:5], 1):
        stats_text += f"{i}. {skin['name']}: {skin['sales_count']} продаж\n"

    stats_text += f"\n🕐 Обновлено: {datetime.now().strftime('%H:%M:%S')}"

    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data=f"admin_detailed_stats_{timestamp}")],
        [InlineKeyboardButton("📈 Базовая статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_main")]
    ]

    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_user_management(query):
    """Показывает управление пользователями с действиями"""
    users = db.get_all_users()

    user_text = "👥 Управление пользователями\n\n"

    for user in users[:5]:
        user_text += f"🆔 {user['user_id']} | {user['first_name']}"
        if user['username']:
            user_text += f" (@{user['username']})"
        user_text += f"\n💰 Баланс: {user['balance']} ₽\n\n"

    if len(users) > 5:
        user_text += f"... и еще {len(users) - 5} пользователей\n"

    keyboard = [
        [InlineKeyboardButton("💰 Изменить баланс", callback_data="admin_change_balance")],
        [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_detailed_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_main")]
    ]

    await query.edit_message_text(
        user_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_change_balance(query, context):
    """Начинает процесс изменения баланса"""
    await query.edit_message_text(
        "💰 Изменение баланса пользователя\n\n"
        "Введите данные в формате:\n"
        "user_id | новый_баланс\n\n"
        "Пример:\n"
        "123456789 | 1000\n\n"
        "Чтобы найти user_id пользователя, попросите его написать /myid"
    )

    # Устанавливаем состояние для ожидания ввода баланса
    context.user_data['waiting_for_balance'] = True

async def show_skin_management(query):
    """Показывает управление скинами с действиями"""
    skins = db.get_all_skins()

    skin_text = "🎮 Управление скинами\n\n"

    for skin in skins[:5]:  # Показываем первые 5
        skin_text += f"🆔 {skin['skin_id']} | {skin['name']}\n"
        skin_text += f"💰 {skin['price']} ₽ | 🎲 {skin['rarity']}\n"
        skin_text += f"📦 В наличии: {skin['quantity']}\n"
        skin_text += f"❌ /delete_skin_{skin['skin_id']}\n\n"

    if len(skins) > 5:
        skin_text += f"... и еще {len(skins) - 5} скинов\n"

    keyboard = [
        [InlineKeyboardButton("➕ Добавить скин", callback_data="admin_add_skin")],
        [InlineKeyboardButton("🗑️ Удалить скин", callback_data="admin_delete_skin")],
        [InlineKeyboardButton("📊 Статистика скинов", callback_data="admin_detailed_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_main")]
    ]

    await query.edit_message_text(
        skin_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_delete_skin(query, context):
    """Начинает процесс удаления скина"""
    await query.edit_message_text(
        "🗑️ Удаление скина\n\n"
        "Введите ID скина для удаления:\n\n"
        "Чтобы узнать ID скина, зайдите в 'Управление скинами'"
    )
    context.user_data['waiting_for_delete_skin'] = True
