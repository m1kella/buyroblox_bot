from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import Database
import asyncio
import logging
from telegram import InputMediaPhoto
from datetime import datetime

logger = logging.getLogger(__name__)
db = Database()

# Константы для пагинации
ITEMS_PER_PAGE = 5

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):

    """Показывает каталог скинов с кнопками и пагинацией"""

    skins = db.get_all_skins()

    if not skins:
        await update.message.reply_text("😔 В каталоге пока нет скинов")
        return

    # Вычисляем общее количество страниц
    total_pages = (len(skins) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    # Получаем скины для текущей страницы
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_skins = skins[start_idx:end_idx]

    # Создаем сообщение с каталогом
    catalog_text = f"🛍️ *Каталог скинов* (Страница {page + 1}/{total_pages})\n\n"

    for skin in current_skins:
        rarity_emoji = {
            'Legendary': '❤️',
            'Godly': '🩷',
            'Ancient': '💜',
        }.get(skin['rarity'], '🤍')

        catalog_text += (
            f"🆔 {skin['skin_id']} | {rarity_emoji} *{skin['name']}* | *{skin['rarity']}* | {skin['price']} ₽\n"
            #f"📝 {skin['description']}\n"
            #f"💰 Цена: {skin['price']} ₽\n"
        )

    catalog_text += f"\n`/skin ID` - информация о скине\n"
    catalog_text += f"`/photo ID` - фото скина\n"

    # Создаем клавиатуру с кнопками
    keyboard = []
    for skin in current_skins:
        keyboard.append([
            InlineKeyboardButton(
                f"➕ {skin['name']} | {skin['rarity']}",
                callback_data=f"cart_add_{skin['skin_id']}"
            )
        ])

    #Кнопки пагинации
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
        pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="current_page"))

    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))

    if pagination_buttons:
        keyboard.append(pagination_buttons)

    # Получаем количество товаров в корзине для счетчика
    cart_count = db.get_cart_count(update.effective_user.id)

    # Основные кнопки
    keyboard.append([InlineKeyboardButton(f"🛒 Корзина ({cart_count})", callback_data="view_cart")])
    keyboard.append([InlineKeyboardButton("🔍 Поиск скинов", callback_data="search_skins")])
    keyboard.append([InlineKeyboardButton("📦 Мой инвентарь", callback_data="inventory")])
    keyboard.append([InlineKeyboardButton("💰 Баланс", callback_data="balance")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                catalog_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                catalog_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Ошибка в show_catalog: {e}")
        # Альтернативный способ
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(
                "❌ Ошибка при загрузке каталога\n\nПопробуйте снова",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Попробовать снова", callback_data="catalog")]
                ])
            )

async def show_catalog_from_button(query, context):
    """Показывает каталог при нажатии на кнопку из других разделов"""
    try:
        # Создаем fake update объект для использования существующей функции show_catalog
        class FakeUpdate:
            def __init__(self, query):
                self.callback_query = query
                self.effective_user = query.from_user

        fake_update = FakeUpdate(query)
        await show_catalog(fake_update, context, page=0)
    except Exception as e:
        # Если возникла ошибка, используем альтернативный способ
        logger.error(f"Ошибка в show_catalog_from_button: {e}")
        await show_catalog_direct(query, context)

async def show_catalog_direct(query, context):
    """Альтернативный способ показа каталога"""
    user_id = query.from_user.id
    skins = db.get_all_skins()

    if not skins:
        await query.edit_message_text("😔 В каталоге пока нет скинов")
        return

    ITEMS_PER_PAGE = 5
    total_pages = (len(skins) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    current_skins = skins[0:ITEMS_PER_PAGE]

    catalog_text = f"🛍️ *Каталог скинов* (Страница 1/{total_pages})\n\n"

    for skin in current_skins:
        rarity_emoji = {
            'Legendary': '❤️',
            'Godly': '🩷',
            'Ancient': '💜',
        }.get(skin['rarity'], '🤍')

        catalog_text += f"🆔 {skin['skin_id']} | {rarity_emoji} *{skin['name']}* | *{skin['rarity']}* | {skin['price']} ₽\n"

    keyboard = []

    for skin in current_skins:
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 [{skin['skin_id']}] {skin['name']}",
                callback_data=f"cart_add_{skin['skin_id']}"
            )
        ])

    pagination_buttons = []
    if total_pages > 1:
        pagination_buttons.append(InlineKeyboardButton("1/{}".format(total_pages), callback_data="current_page"))
        pagination_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_1"))

    if pagination_buttons:
        keyboard.append(pagination_buttons)

    cart_count = db.get_cart_count(user_id)

    keyboard.append([InlineKeyboardButton(f"🛒 Корзина ({cart_count})", callback_data="view_cart")])
    keyboard.append([InlineKeyboardButton("🔍 Поиск скинов", callback_data="search_skins")])
    keyboard.append([InlineKeyboardButton("📦 Мой инвентарь", callback_data="inventory")])
    keyboard.append([InlineKeyboardButton("💰 Баланс", callback_data="balance")])

    await query.edit_message_text(
        catalog_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    callback_data = query.data

    if callback_data.startswith('buy_'):
        skin_id = int(callback_data.split('_')[1])
        await process_purchase(query, skin_id, user_id)

    elif callback_data.startswith('page_'):
        page = int(callback_data.split('_')[1])
        await show_catalog(update, context, page)

    elif callback_data == 'inventory':
        await show_inventory(query, user_id)

    elif callback_data == 'balance':
        await show_balance(query, user_id)

    elif callback_data == 'search_skins':
        await start_search(query, context)

    elif callback_data == 'catalog':
        await return_to_catalog_final(query, user_id)

    elif callback_data.startswith('search_page_'):
        parts = callback_data.split('_')
        page = int(parts[2])
        search_term = '_'.join(parts[3:])
        found_skins = db.search_skins(search_term)
        await show_search_results(update, context, found_skins, search_term, page)

    elif callback_data.startswith('cart_add_'):
        skin_id = int(callback_data.split('_')[2])
        await add_to_cart(query, user_id, skin_id)

    elif callback_data == 'view_cart':
        await show_cart(query, user_id)

    elif callback_data.startswith('cart_remove_'):
        skin_id = int(callback_data.split('_')[2])
        await remove_from_cart(query, user_id, skin_id)

    elif callback_data == 'clear_cart':
        await clear_cart(query, user_id)

    elif callback_data == 'confirm_purchase':
        await confirm_purchase(query, context, user_id)

    elif callback_data == 'already_in_cart':
        await query.answer("✅ Этот скин уже в корзине", show_alert=True)

    elif callback_data.startswith('withdraw_'):
        skin_id = int(callback_data.split('_')[1])
        await withdraw_skin(query, user_id, skin_id)

    elif callback_data.startswith('confirm_withdraw_'):
        skin_id = int(callback_data.split('_')[2])
        await confirm_withdraw_skin(query, context, user_id, skin_id)

    elif callback_data.startswith('inv_page_'):
        page = int(callback_data.split('_')[2])
        await show_inventory(query, user_id, page)

    elif callback_data.startswith('view_photo_'):
        skin_id = int(callback_data.split('_')[2])
        await show_photo_only(query, skin_id)

    elif callback_data.startswith('skin_info_'):
        # Возврат к информации о скине из фото
        skin_id = int(callback_data.split('_')[2])
        await show_skin_info(query, skin_id, user_id)

# -----------------------ОБЫЧНЫЕ-МЕТОДЫ------------------------- #

#Обрабатывает процесс покупки скина
async def process_purchase(query, skin_id, user_id):
    """Обрабатывает процесс покупки скина"""
    skin = db.get_skin_by_id(skin_id)
    user = db.get_user(user_id)

    if not skin:
        await query.answer("❌ Скин не найден", show_alert=True)
        return

    if not user:
        await query.answer("❌ Пользователь не найден. Напиши /start", show_alert=True)
        return

    if user['balance'] < skin['price']:
        await query.edit_message_text(
            f"❌ Недостаточно средств!\n\n"
            f"💰 Твой баланс: {user['balance']} ₽\n"
            f"💵 Цена скина: {skin['price']} ₽\n"
            f"📉 Не хватает: {skin['price'] - user['balance']} ₽\n\n"
            f"Для пополнения баланса обратись к администратору @m1kellaa",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Пополнить баланс", url="https://t.me/m1kellaa")],
                [InlineKeyboardButton("🔙 Назад", callback_data="catalog")]
            ])
        )
        return

    if skin['quantity'] <= 0:
        await query.edit_message_text(
            "❌ Этот скин закончился",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="catalog")]
            ])
        )
        return

    success = db.add_to_inventory(user_id, skin_id)

    if success:
        db.update_user_balance(user_id, -skin['price'])
        db.add_transaction(
            user_id=user_id,
            amount=-skin['price'],
            transaction_type='purchase',
            description=f"Покупка скина: {skin['name']}"
        )

        await query.edit_message_text(
            f"🎉 Поздравляем с покупкой!\n\n"
            f"✅ Ты приобрел: *{skin['name']}*\n"
            f"💵 Стоимость: {skin['price']} ₽\n\n"
            f"💰 Остаток на балансе: {user['balance'] - skin['price']} ₽\n\n"
            f"Скин добавлен в твой инвентарь!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Мой инвентарь", callback_data="inventory")],
                [InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")]
            ]),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при покупке. Возможно, у тебя уже есть этот скин",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="catalog")]
            ])
        )

#Показывает инвентарь пользователя
async def show_inventory(query, user_id, page=0):
    """Показывает инвентарь пользователя"""
    inventory = db.get_inventory_with_details(user_id)

    if not inventory:
        await query.edit_message_text(
            "📦 Твой инвентарь пуст\n\n"
            "Перейди в каталог, чтобы приобрести скины",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")]
            ])
        )
        return

    ITEMS_PER_PAGE = 5
    total_pages = (len(inventory) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_items = inventory[start_idx:end_idx]

    inventory_text = f"📦 *Твой инвентарь скинов* (Страница {page + 1}/{total_pages})\n\n"

    for item in current_items:
        rarity_emoji = {
            'Legendary': '❤️',
            'Godly': '🩷',
            'Ancient': '💜',
        }.get(item['rarity'], '🤍')

        inventory_text += f"{rarity_emoji} *{item['name']}* | *{item['rarity']}* | {item['price']} ₽\n"
        #inventory_text += f"🎲 Редкость: {item['rarity']}\n"
        #inventory_text += f"💰 Стоимость: {item['price']} ₽\n"
        inventory_text += f"🕐 Куплен: {item['purchased_at'][:10]}\n\n"

    keyboard = []

    for item in current_items:
        keyboard.append([
            InlineKeyboardButton(f"🎮 Забрать {item['name']}", callback_data=f"withdraw_{item['skin_id']}")
        ])

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"inv_page_{page - 1}"))

    pagination_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="inv_current"))

    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"inv_page_{page + 1}"))

    if pagination_buttons:
        keyboard.append(pagination_buttons)

    keyboard.append([InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")])
    keyboard.append([InlineKeyboardButton("💰 Баланс", callback_data="balance")])

    await query.edit_message_text(
        inventory_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

#Показывает баланс пользователя
async def show_balance(query, user_id):
    """Показывает баланс пользователя"""
    user = db.get_user(user_id)

    if user:
        balance_text = (
            f"💰 *Твой баланс:* {user['balance']} ₽\n\n"
            f"Для пополнения баланса обратись к администратору @m1kellaa"
        )

        await query.edit_message_text(
            balance_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")],
                [InlineKeyboardButton("📦 Инвентарь", callback_data="inventory")]
            ])
        )
    else:
        await query.edit_message_text(
            "❌ Пользователь не найден",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")]
            ])
        )

async def start_search(query, context):
    """Начинает процесс поиска скинов"""
    await query.edit_message_text(
        "🔍 *Поиск скинов*\n\n"
        "Введите название скина или часть названия для поиска:\n\n"
        "*Примеры:*\n"
        "• `нож` - найдет все ножи\n"
        "• `ice` - найдет Iceflake, Icebeam и т.д.\n"
        "• `legendary` - найдет все легендарные предметы",
        parse_mode='Markdown'
    )

    context.user_data['waiting_for_search'] = True

async def show_search_results(update, context, skins, search_term, page=0):
    """Показывает результаты поиска"""
    ITEMS_PER_PAGE = 5
    total_pages = (len(skins) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_skins = skins[start_idx:end_idx]

    search_text = f"🔍 *Результаты поиска: \"{search_term}\"*\n"
    search_text += f"📊 Найдено скинов: {len(skins)} (Страница {page + 1}/{total_pages})\n\n"

    for skin in current_skins:
        rarity_emoji = {
            'Legendary': '❤️',
            'Godly': '🩷',
            'Ancient': '💜',
        }.get(skin['rarity'], '🤍')

        search_text += (
            f"🆔 '{skin['skin_id']}' | {rarity_emoji} *{skin['name']}* | *{skin['rarity']}* | {skin['price']} ₽\n"
        )

    keyboard = []

    for skin in current_skins:
        keyboard.append([
            InlineKeyboardButton(
                f"🛒 В корзину - {skin['name']}",
                callback_data=f"cart_add_{skin['skin_id']}"
            )
        ])

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"search_page_{page - 1}_{search_term}"))

    pagination_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="current_page"))

    if page < total_pages - 1:
        pagination_buttons.append(
            InlineKeyboardButton("Вперед ➡️", callback_data=f"search_page_{page + 1}_{search_term}"))

    if pagination_buttons:
        keyboard.append(pagination_buttons)

    keyboard.append([InlineKeyboardButton("🛍️ Весь каталог", callback_data="catalog")])
    keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="search_skins")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            search_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            search_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def return_to_catalog_final(query, user_id):
    """Универсальный возврат в каталог"""
    try:
        # Просто отправляем новый каталог
        await show_catalog_direct(query, None)
    except Exception as e:
        logger.error(f"Ошибка возврата в каталог: {e}")
        # Если не получилось, отправляем простой каталог
        await query.message.reply_text(
            "🛍️ *Каталог скинов*\n\n"
            "Используйте кнопки ниже для навигации:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Мой инвентарь", callback_data="inventory")],
                [InlineKeyboardButton("💰 Баланс", callback_data="balance")],
                [InlineKeyboardButton("🛒 Корзина", callback_data="view_cart")]
            ]),
            parse_mode='Markdown'
        )

async def show_photo_only(query, skin_id):
    """Показывает только фото скина"""
    skin = db.get_skin_by_id(skin_id)

    if not skin or not skin.get('image_url'):
        await query.answer("❌ Фото недоступно", show_alert=True)
        return

    try:
        # Если текущее сообщение текстовое - отправляем новое с фото
        if not query.message.photo:
            await query.message.reply_photo(
                photo=skin['image_url'],
                caption=f"🎮 {skin['name']} - {skin['rarity']}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад к информации", callback_data=f"skin_info_{skin_id}")]
                ])
            )
        else:
            # Если уже показывается фото - редактируем его
            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=skin['image_url'],
                    caption=f"🎮 {skin['name']} - {skin['rarity']}"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад к информации", callback_data=f"skin_info_{skin_id}")]
                ])
            )
    except Exception as e:
        logger.error(f"Ошибка при показе фото: {e}")
        await query.answer("❌ Ошибка при загрузке фото", show_alert=True)

async def show_skin_info(query, skin_id, user_id):
    """Показывает информацию о скине из callback (для возврата из фото)"""
    skin = db.get_skin_by_id(skin_id)

    if not skin:
        await query.answer("❌ Скин не найден", show_alert=True)
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
        skin_text += f"\n📸 *Фото:* `/photo {skin_id}`"

    keyboard = [
        [
            InlineKeyboardButton("🛒 В корзину", callback_data=f"cart_add_{skin_id}"),
            InlineKeyboardButton("💰 Купить сейчас", callback_data=f"buy_{skin_id}")
        ]
    ]

    if skin.get('image_url'):
        keyboard.append([InlineKeyboardButton("📸 Посмотреть фото", callback_data=f"view_photo_{skin_id}")])

    keyboard.append([InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")])

    await query.edit_message_caption(
        caption=skin_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# -----------------------МЕТОДЫ-КОРЗИНЫ------------------------- #

#Добавление товара в корзину
async def add_to_cart(query, user_id, skin_id):
    """Добавляет скин в корзину"""
    skin = db.get_skin_by_id(skin_id)

    if not skin:
        await query.answer("❌ Скин не найден", show_alert=True)
        return

    if skin['quantity'] <= 0:
        await query.answer("❌ Этот скин закончился", show_alert=True)
        return

    success = db.add_to_cart(user_id, skin_id)

    if success:
        cart_count = db.get_cart_count(user_id)

        await query.answer(
            f"✅ {skin['name']} добавлен в корзину!\n"
            f"📦 В корзине: {cart_count} товаров",
            show_alert=True
        )

        # Обновляем счетчик корзины в сообщении
        try:
            original_markup = query.message.reply_markup
            new_keyboard = []
            for row in original_markup.inline_keyboard:
                new_row = []
                for button in row:
                    if button.callback_data == "view_cart":
                        new_row.append(InlineKeyboardButton(
                            f"🛒 Корзина ({cart_count})",
                            callback_data="view_cart"
                        ))
                    else:
                        new_row.append(button)
                new_keyboard.append(new_row)

            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(new_keyboard)
            )
        except:
            pass  # Игнорируем ошибки обновления

    else:
        await query.answer("❌ Этот скин уже в корзине", show_alert=True)

#Показывает корзину пользователя
async def show_cart(query, user_id):
    """Показывает корзину пользователя"""
    cart_items = db.get_user_cart(user_id)
    user = db.get_user(user_id)

    if not cart_items:
        await query.edit_message_text(
            "🛒 Ваша корзина пуста\n\n"
            "Перейдите в каталог чтобы добавить скины!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")]
            ])
        )
        return

    total_price = sum(item['price'] for item in cart_items)

    cart_text = f"🛒 Ваша корзина\n\n"

    for item in cart_items:
        rarity_emoji = {
            'Legendary': '❤️',
            'Godly': '🩷',
            'Ancient': '💜',
        }.get(item['rarity'], '🤍')

        cart_text += f"{rarity_emoji} {item['name']} | {item['rarity']} | {item['price']} ₽\n\n"
        #cart_text += f"💰 {item['price']} ₽\n"
        #cart_text += f"🎲 {item['rarity']}\n\n"

    cart_text += f"💵 Общая сумма: {total_price} ₽\n"
    cart_text += f"💰 Ваш баланс: {user['balance']} ₽\n\n"

    if user['balance'] < total_price:
        cart_text += "❌ Недостаточно средств для покупки\n"

    keyboard = []

    for item in cart_items:
        keyboard.append([
            InlineKeyboardButton(f"❌ Удалить {item['name']}", callback_data=f"cart_remove_{item['skin_id']}")
        ])

    if cart_items:
        if user['balance'] >= total_price:
            keyboard.append([InlineKeyboardButton("✅ Подтвердить покупку", callback_data="confirm_purchase")])
        keyboard.append([InlineKeyboardButton("🗑️ Очистить корзину", callback_data="clear_cart")])

    keyboard.append([InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")])
    keyboard.append([InlineKeyboardButton("💰 Баланс", callback_data="balance")])

    await query.edit_message_text(
        cart_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def remove_from_cart(query, user_id, skin_id):
    """Удаляет скин из корзины"""
    success = db.remove_from_cart(user_id, skin_id)

    if success:
        await query.answer("✅ Удалено из корзины")
        await show_cart(query, user_id)
    else:
        await query.answer("❌ Ошибка при удалении")

async def clear_cart(query, user_id):
    """Очищает корзину"""
    success = db.clear_user_cart(user_id)

    if success:
        await query.message.reply_text(
            "🗑️ Корзина очищена",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")]
            ])
        )
    else:
        await query.answer("❌ Ошибка при очистке корзины")

async def confirm_purchase(query, context, user_id):
    """Подтверждает покупку всей корзины"""
    cart_items = db.get_user_cart(user_id)
    user = db.get_user(user_id)

    if not cart_items:
        await query.answer("❌ Корзина пуста")
        return

    total_price = sum(item['price'] for item in cart_items)

    if user['balance'] < total_price:
        await query.answer("❌ Недостаточно средств")
        return

    for item in cart_items:
        if item['quantity'] <= 0:
            await query.message.reply_text(
                f"❌ Скин \"{item['name']}\" закончился\n\n"
                f"Пожалуйста, обновите корзину",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Обновить корзину", callback_data="view_cart")]
                ])
            )
            return

    purchased_skins = []
    for item in cart_items:
        success = db.add_to_inventory(user_id, item['skin_id'])
        if success:
            purchased_skins.append(item['name'])
            db.update_user_balance(user_id, -item['price'])
            db.add_transaction(
                user_id=user_id,
                amount=-item['price'],
                transaction_type='purchase',
                description=f"Покупка скина: {item['name']}"
            )

    db.clear_user_cart(user_id)

    purchase_text = "🎉 Покупка успешно завершена!\n\n"
    purchase_text += f"✅ Купленные скины:\n\n"
    for skin_name in purchased_skins:
        purchase_text += f"• {skin_name}\n"

    purchase_text += f"\n💵 Общая стоимость: {total_price} ₽\n"
    purchase_text += f"💰 Остаток на балансе: {user['balance'] - total_price} ₽\n\n"
    purchase_text += "Скины добавлены в ваш инвентарь!"

    await query.message.reply_text(
        purchase_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Мой инвентарь", callback_data="inventory")],
            [InlineKeyboardButton("🛍️ В каталог", callback_data="catalog")]
        ]),
        parse_mode='Markdown'
    )

    # 🔔 УВЕДОМЛЕНИЕ ДЛЯ АДМИНА О ПОКУПКЕ
    current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
    await send_purchase_admin_notification(
        bot=context.bot,  # Передаем bot из context
        user_name=query.from_user.first_name,
        user_username=f"@{query.from_user.username}" if query.from_user.username else "не указан",
        user_id=user_id,
        skins=purchased_skins,
        total_price=total_price,
        time=current_time
    )

# -----------------------ВЫВОД-ПРЕДМЕТОВ------------------------- #

async def withdraw_skin(query, user_id, skin_id):
    """Процесс вывода скина в Mystery Murder 2"""
    skin = db.get_skin_by_id(skin_id)
    user = db.get_user(user_id)

    if not skin:
        await query.answer("❌ Скин не найден", show_alert=True)
        return

    await query.message.reply_text(
        f"🎮 *Вывод скина в Mystery Murder 2*\n\n"
        f"📋 *Информация о скине:*\n\n"
        f"🔪 {skin['name']} | {skin['rarity']} | {skin['price']}\n\n"
        #f"💎 Редкость: {skin['rarity']}\n"
        #f"💰 Стоимость: {skin['price']} ₽\n\n"

        f"📞 *Как получить скин:*\n"
        f"1. Напишите @m1kellaa в ЛС\n"
        f"2. Укажите ваш @username в Roblox\n"
        f"3. Название скина: *{skin['name']}*\n"
        f"4. Ваш User ID: `{user_id}`\n\n"

        f"🎯 *Условия трейда в MM2:*\n"
        f"• Уровень 10+ в Mystery Murder 2\n"
        f"• Аккаунт Roblox 13+\n\n"

        f"⏱ *Время выдачи:* 5-15 минут после оплаты.\n"
        f"*Обработка заказов:* _09:00 - 21:00 МСК_",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📞 Написать для трейда", url="https://t.me/m1kellaa"),
                InlineKeyboardButton("✅ Я получил скин", callback_data=f"confirm_withdraw_{skin_id}")
            ],
            [
                InlineKeyboardButton("📦 Назад в инвентарь", callback_data="inventory")
            ]
        ])
    )

async def confirm_withdraw_skin(query, context, user_id, skin_id):
    """Подтверждение получения скина в MM2"""
    skin = db.get_skin_by_id(skin_id)

    success = db.remove_from_inventory_mm2(user_id, skin_id)

    if success:
        # Получаем текущее время
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M')

        # Сообщение для пользователя
        await query.message.reply_text(
            f"🎉 *Скин успешно передан!*\n\n"
            f"✅ *{skin['name']}* выведен в ваш аккаунт MM2\n\n"
            f"📋 *Детали операции:*\n\n"
            f"🔪 Скин: {skin['name']}\n"
            f"💎 Редкость: {skin['rarity']}\n"
            #f"👤 Игрок: {query.from_user.first_name}\n"
            f"🕐 Время: {current_time}\n\n"
            f"Спасибо за покупку! Удачной игры в Mystery Murder 2! 🎮🔪",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ Купить еще", callback_data="catalog")],
                [InlineKeyboardButton("📦 Остальные скины", callback_data="inventory")]
            ])
        )

        # 🔔 УВЕДОМЛЕНИЕ ДЛЯ АДМИНА О ВЫВОДЕ
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
        await send_admin_notification(
            bot=context.bot,  # Передаем bot из context
            user_name=query.from_user.first_name,
            user_username=f"@{query.from_user.username}" if query.from_user.username else "не указан",
            user_id=user_id,
            skin_name=skin['name'],
            skin_rarity=skin['rarity'],
            skin_price=skin['price'],
            time=current_time
        )

    else:
        await query.message.edit_text(
            "❌ Ошибка при подтверждении вывода\n\n"
            "Если вы уже получили скин, но видите эту ошибку,\n"
            "пожалуйста, свяжитесь с администратором",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Написать админу", url="https://t.me/m1kellaa")],
                [InlineKeyboardButton("📦 Назад в инвентарь", callback_data="inventory")]
            ])
        )

async def send_admin_notification(bot, user_name, user_username, user_id, skin_name, skin_rarity, skin_price, time):
    """Отправляет уведомление администратору о выводе скина"""
    try:
        from config import Config

        admin_message = (
            "🔔 *УВЕДОМЛЕНИЕ: Вывод скина в MM2*\n\n"
            f"👤 *Пользователь:* {user_name} ({user_username})\n"
            f"🆔 User ID: `{user_id}`\n\n"
            f"🎮 *Скин:* {skin_name}\n"
            f"💎 *Редкость:* {skin_rarity}\n"
            f"💰 *Цена:* {skin_price} ₽\n\n"
            f"🕐 *Время подтверждения:* {time}\n"
            f"✅ *Статус:* Скин выведен из инвентаря"
        )

        # Отправляем сообщение админу
        await bot.send_message(
            chat_id=Config.ADMIN_ID_INT,
            text=admin_message,
            parse_mode='Markdown'
        )

        logger.info(f"Уведомление отправлено админу о выводе скина {skin_name} пользователем {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления админу: {e}")

async def send_purchase_admin_notification(bot, user_name, user_username, user_id, skins, total_price, time):
    """Отправляет уведомление администратору о покупке"""
    try:
        from config import Config

        skins_list = "\n".join([f"• {skin}" for skin in skins])

        admin_message = (
            "🛒 *УВЕДОМЛЕНИЕ: Новая покупка*\n\n"
            f"👤 *Пользователь:* {user_name} ({user_username})\n"
            f"🆔 User ID: `{user_id}`\n\n"
            f"🎮 *Купленные скины:*\n{skins_list}\n\n"
            f"💰 *Общая сумма:* {total_price} ₽\n"
            f"🕐 *Время покупки:* {time}"
        )

        # Отправляем сообщение админу
        await bot.send_message(
            chat_id=Config.ADMIN_ID_INT,
            text=admin_message,
            parse_mode='Markdown'
        )

        logger.info(f"Уведомление отправлено админу о покупке пользователем {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о покупке админу: {e}")
