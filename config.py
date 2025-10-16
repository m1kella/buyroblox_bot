import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = os.getenv('ADMIN_ID')

    # Отладочная информация
    print(f"🛠️ DEBUG: BOT_TOKEN loaded: {'Yes' if BOT_TOKEN else 'No'}")
    print(f"🛠️ DEBUG: ADMIN_ID loaded: {ADMIN_ID} (тип: {type(ADMIN_ID)})")

    # Проверяем, что токен загружен
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в .env файле")

    # Преобразуем ADMIN_ID в int
    try:
        if ADMIN_ID:
            # СОЗДАЕМ НОВУЮ ПЕРЕМЕННУЮ, а не изменяем существующую
            ADMIN_ID_INT = int(ADMIN_ID)
            print(f"🛠️ DEBUG: ADMIN_ID converted to int: {ADMIN_ID_INT}")
        else:
            ADMIN_ID_INT = None
            print("❌ ADMIN_ID не найден в .env файле")
    except ValueError as e:
        print(f"❌ Ошибка преобразования ADMIN_ID: {e}")
        raise ValueError("ADMIN_ID должен быть числом")