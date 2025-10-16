import telegram
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from config import Config
from database import Database
from handlers import show_catalog, button_handler, show_inventory
from admin_handlers import admin_panel, admin_button_handler
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is running!"

@app.route('/health')
def health():
    return "OK"

def run_web_server():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_errors.log')  # Логи в файл
    ]
)

# Создаем логгер
logger = logging.getLogger(__name__)

# Отключаем логи для некоторых noisy модулей
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ошибки бота"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    
    # Можно отправить сообщение админу
    try:
        from config import Config
        if Config.ADMIN_ID_INT:
            error_text = f"❌ Ошибка бота:\n{context.error}"
            await context.bot.send_message(
                chat_id=Config.ADMIN_ID_INT,
                text=error_text
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления админу: {e}")

db = Database()

# ---------------------КОМАНДЫ----------------------- #

async def start(update, context):

    """Обработчик команды /start"""

    user = update.effective_user

    db.add_user(user_id=user.id, username=user.username, first_name=user.first_name, last_name=user.last_name)

    await update.message.reply_html(
f"Привет {user.mention_html()}! 👋\n"
f"Добро пожаловать в магазин скинов MM2!\n\n"
f"💰 Твой стартовый баланс: 0 ₽\n"
f"🎮 Теперь ты можешь покупать крутые скины!\n\n"
f"Напиши /catalog, чтобы посмотреть каталог:\n"
f"Чтобы ознакомиться со всеми командами, напиши /help или воспользуйтесь меню\n\n"
f"🕘 Рабочее время обработки заказов: 09:00 - 21:00 МСК"
    )

async def help_command(update, context):

    """Обработчик команды /help"""

    help_text = """
🤖 Помощь по боту

Основные команды:
/start - начать работу
/catalog - каталог скинов
/balance - ваш баланс
/inventory - купить скин

В каталоге ты можешь:

• Просматривать все доступные скины
• Видеть цены и редкость
• Покупать скины одним нажатием

Как пополнить баланс:

• Напрямую переводом по номеру карты -> получить реквизиты @m1kellaa
• Пишите администратору на какую сумму хотите пополнить
• После успешной оплаты скриншот чека или перевода в ЛС
• В течении 5-10 минут ваш баланс пополняется
• Проверить /balance

Как забрать купленные товары:

• Заказы обрабатываются с 09:00 до 21:00 МСК
• Пишите администратору, какие товары нужно вывести -> @m1kellaa
• Все товары выдаются путем трейда внутри MM2
• Условия для успешного трейда: 10 LVL в MM2, аккаунт Roblox 13+

Поддержка:
Если возникли проблемы, напишите @m1kellaa"""

    await update.message.reply_html(help_text)

async def balance_command(update, context):

    """Обработчик команды /balance"""

    user = update.effective_user
    user_data = db.get_user(user.id)

    if user_data:
        balance = user_data['balance']
        await update.message.reply_text(
            f"💰 Твой баланс: {balance} ₽\n\n"
            f"Для пополнения баланса обратись к администратору @m1kellaa"
        )
    else:
        await update.message.reply_text("❌ Пользователь не найден. Напиши /start")

async def inventory_command(update, context):

    """Обработчик команды /inventory"""

    from handlers import show_inventory
    user = update.effective_user

    # Создаем fake query объект для использования существующей функции
    class FakeQuery:
        def __init__(self, message):
            self.message = message

        async def edit_message_text(self, *args, **kwargs):
            await self.message.reply_text(*args, **kwargs)

    fake_query = FakeQuery(update.message)
    await show_inventory(fake_query, user.id)

async def photo_command(update, context):
    """Показывает фото скина по ID"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "📸 *Просмотр фото скина*\n\n"
            "Использование:\n"
            "`/photo ID_скина`\n\n"
            "Пример:\n"
            "`/photo 1`\n\n"
            "ID скина можно найти в каталоге",
            parse_mode='Markdown'
        )
        return

    try:
        skin_id = int(context.args[0])
        skin = db.get_skin_by_id(skin_id)

        if not skin:
            await update.message.reply_text("❌ Скин с таким ID не найден")
            return

        if not skin.get('image_url') or not skin['image_url'].startswith(('http://', 'https://')):
            await update.message.reply_text(
                f"🎮 *{skin['name']}*\n\n"
                f"❌ Фото для этого скина недоступно\n\n"
                f"💎 Редкость: {skin['rarity']}\n"
                f"💰 Цена: {skin['price']} ₽",
                parse_mode='Markdown'
            )
            return

        # Отправляем фото
        await update.message.reply_photo(
            photo=skin['image_url'],
            caption=(
                f"🎮 *{skin['name']}*\n\n"
                f"💎 Редкость: {skin['rarity']}\n"
                f"💰 Цена: {skin['price']} ₽\n"
                f"📦 В наличии: {skin['quantity']} шт.\n\n"
                f"📝 {skin['description']}"
            ),
            parse_mode='Markdown'
        )

    except ValueError:
        await update.message.reply_text("❌ ID скина должен быть числом")
    except Exception as e:
        logger.error(f"Ошибка при показе фото: {e}")
        await update.message.reply_text("❌ Ошибка при загрузке фото")

async def skin_info_command(update, context):
    """Показывает подробную информацию о скине"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "🎮 *Информация о скине*\n\n"
            "Использование:\n"
            "`/skin ID_скина`\n\n"
            "Пример:\n"
            "`/skin 1`\n\n"
            "ID скина можно найти в каталоге",
            parse_mode='Markdown'
        )
        return

    try:
        skin_id = int(context.args[0])
        skin = db.get_skin_by_id(skin_id)

        if not skin:
            await update.message.reply_text("❌ Скин с таким ID не найден")
            return

        rarity_emoji = {
            'Legendary': '❤️',
            'Godly': '🩷',
            'Ancient': '💜',
        }.get(skin['rarity'], '🤍')

        skin_text = (
            f"{rarity_emoji} *{skin['name']}*\n\n"
            f"💎 *Редкость:* {skin['rarity']}\n"
            f"💰 *Цена:* {skin['price']} ₽\n"
            f"📦 *В наличии:* {skin['quantity']} шт.\n"
        )

        #if skin['description']:
            #skin_text += f"\n📝 *Описание:* {skin['description']}\n"

        if skin.get('image_url'):
            skin_text += f"\n📸 *Фото:* Доступно"

        keyboard = [
            [
                InlineKeyboardButton("🛒 В корзину", callback_data=f"cart_add_{skin_id}"),
                InlineKeyboardButton("💰 Купить сейчас", callback_data=f"buy_{skin_id}")
            ]
        ]

        if skin.get('image_url'):
            keyboard.append([InlineKeyboardButton("📸 Посмотреть фото", callback_data=f"view_photo_{skin_id}")])

        keyboard.append([InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")])

        await update.message.reply_text(
            skin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    except ValueError:
        await update.message.reply_text("❌ ID скина должен быть числом")
    except Exception as e:
        logger.error(f"Ошибка при показе информации о скине: {e}")
        await update.message.reply_text("❌ Ошибка при загрузке информации")

# -----------------------АДМИН-ОБРАБОТЧИКИ------------------------- #

async def handle_message(update, context):

    """Обрабатывает текстовые сообщения"""

    user_id = update.effective_user.id
    text = update.message.text

    # Проверяем, ожидаем ли мы ввод скина от админа
    if context.user_data.get('waiting_for_skin'):
        await process_skin_input(update, context, text)
        return

    # ⭐⭐ ДОБАВЛЯЕМ обработку поисковых запросов ⭐⭐
    if context.user_data.get('waiting_for_search'):
        await process_search_query(update, context, text)
        return

    # ⭐⭐ ДОБАВЛЯЕМ обработку изменения баланса ⭐⭐
    if context.user_data.get('waiting_for_balance'):
        await process_balance_change(update, context, text)
        return

    if context.user_data.get('waiting_for_delete_skin'):
        await process_delete_skin(update, context, text)
        return

    # Обычные сообщения
    await update.message.reply_text(
        "Используйте команды для взаимодействия с ботом:\n"
        "/start - начать работу\n"
        "/catalog - каталог скинов\n"
        "/help - помощь"
    )

async def process_balance_change(update, context, text):
    """Обрабатывает изменение баланса пользователя"""
    from admin_handlers import is_admin
    from database import Database

    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Нет доступа")
        return

    try:
        # Парсим введенные данные
        parts = text.split('|')
        if len(parts) != 2:
            await update.message.reply_text(
                "❌ Неверный формат. Нужно 2 части разделенных |\n"
                "Формат: user_id | новый_баланс"
            )
            return

        target_user_id = int(parts[0].strip())
        new_balance = float(parts[1].strip())

        # Изменяем баланс
        db = Database()
        success = db.update_user_balance_directly(target_user_id, new_balance)

        if success:
            # Записываем транзакцию
            db.add_transaction(
                user_id=target_user_id,
                amount=new_balance,
                transaction_type='admin_adjustment',
                description=f"Корректировка баланса администратором"
            )

            await update.message.reply_text(
                f"✅ Баланс пользователя {target_user_id} установлен на {new_balance} ₽"
            )
        else:
            await update.message.reply_text("❌ Ошибка при изменении баланса")

    except ValueError:
        await update.message.reply_text("❌ Ошибка: user_id должен быть числом, баланс - числом")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    # Сбрасываем состояние ожидания
    context.user_data['waiting_for_balance'] = False

async def process_search_query(update, context, text):
    """Обрабатывает поисковый запрос"""
    from database import Database
    from handlers import show_search_results

    search_term = text.strip()

    if not search_term:
        await update.message.reply_text("❌ Введите поисковый запрос")
        return

    # Ищем скины
    db = Database()
    found_skins = db.search_skins(search_term)

    if not found_skins:
        await update.message.reply_text(
            f"😔 По запросу \"{search_term}\" ничего не найдено\n\n"
            f"Попробуйте:\n"
            f"• Другие ключевые слова\n"
            f"• Более общий запрос\n"
            f"• Проверить правильность написания"
        )
    else:
        # Показываем результаты поиска
        await show_search_results(update, context, found_skins, search_term)

    # Сбрасываем состояние ожидания
    context.user_data['waiting_for_search'] = False

async def process_skin_input(update, context, text):
    """Обрабатывает ввод данных скина от админа"""
    from admin_handlers import is_admin
    from database import Database

    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Нет доступа")
        return

    try:
        # Парсим введенные данные (теперь 7 частей)
        parts = text.split('|')
        if len(parts) != 7:
            await update.message.reply_text(
                "❌ Неверный формат. Нужно 7 частей разделенных |\n"
                "Формат: название | описание | цена | редкость | количество | roblox_id | image_url"
            )
            return

        name = parts[0].strip()
        description = parts[1].strip()
        price = float(parts[2].strip())
        rarity = parts[3].strip()
        quantity = int(parts[4].strip())
        roblox_id = parts[5].strip()
        image_url = parts[6].strip()

        # Проверяем редкость
        valid_rarities = ['Legendary', 'Godly', 'Ancient']
        if rarity not in valid_rarities:
            await update.message.reply_text(
                f"❌ Неверная редкость. Допустимые: {', '.join(valid_rarities)}"
            )
            return

        # Добавляем скин в базу
        db = Database()
        success = db.add_skin(name, description, price, rarity, roblox_id, image_url, quantity)

        if success:
            await update.message.reply_text(
                f"✅ Скин успешно добавлен!\n\n"
                f"Название: {name}\n"
                f"Описание: {description}\n"
                f"Цена: {price} ₽\n"
                f"Редкость: {rarity}\n"
                f"Количество: {quantity} шт.\n"
                f"Roblox ID: {roblox_id}\n"
                f"Фото: {'✅' if image_url else '❌'}"
            )
        else:
            await update.message.reply_text("❌ Ошибка при добавлении скина")

    except ValueError as e:
        await update.message.reply_text(f"❌ Ошибка в данных: {e}\nПроверьте что цена и количество - числа")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    context.user_data['waiting_for_skin'] = False

async def process_delete_skin(update, context, text):
    """Обрабатывает удаление скина"""
    from admin_handlers import is_admin
    from database import Database

    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Нет доступа")
        return

    try:
        skin_id = int(text.strip())
        db = Database()

        # Проверяем существует ли скин
        skin = db.get_skin_by_id(skin_id)
        if not skin:
            await update.message.reply_text("❌ Скин с таким ID не найден")
            return

        # Удаляем скин
        with db.get_connection() as conn:
            conn.execute('DELETE FROM skins WHERE skin_id = ?', (skin_id,))
            conn.commit()

        await update.message.reply_text(
            f"✅ Скин '{skin['name']}' (ID: {skin_id}) успешно удален!"
        )

    except ValueError:
        await update.message.reply_text("❌ ID скина должен быть числом")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при удалении: {str(e)}")

    context.user_data['waiting_for_delete_skin'] = False

async def my_id(update, context):
    """Показывает ID пользователя"""
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 Твой ID: `{user.id}`\n"
        f"👤 Username: @{user.username}\n"
        f"📛 Имя: {user.first_name}",
        parse_mode='Markdown'
    )

# -----------------------ЗАПУСК-БОТА------------------------- #

def main():
    """Основная функция запуска бота"""
    try:
        # Создаем приложение
        application = (
            Application.builder()
            .token(Config.BOT_TOKEN)
            .concurrent_updates(True)
            .build()
        )
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("catalog", show_catalog))
        application.add_handler(CommandHandler("inventory", inventory_command))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("myid", my_id))
        application.add_handler(CommandHandler("photo", photo_command))
        application.add_handler(CommandHandler("skin", skin_info_command))
        application.add_handler(CommandHandler("delete_skin", delete_skin_command))

        # ⭐⭐ Важно: сначала админ хендлеры, потом обычные ⭐⭐
        application.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^admin_"))
        application.add_handler(CallbackQueryHandler(button_handler))

        # Добавляем обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        print("🤖 Starting bot with conflict protection...")
        
        # Запускаем с защитой от конфликтов
        application.run_polling(
            drop_pending_updates=True,  # Игнорируем старые сообщения
            allowed_updates=['message', 'callback_query'],
            close_loop=False
        )
        
    except telegram.error.Conflict:
        print("❌ Conflict detected! Another bot instance is running.")
        print("🔄 Waiting 30 seconds and restarting...")
        import time
        time.sleep(30)
        main()  # Перезапускаем
        
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        print("🔄 Restarting in 10 seconds...")
        import time
        time.sleep(10)
        main()  # Перезапускаем

if __name__ == "__main__":
    main()
