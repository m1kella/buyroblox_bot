import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:

    def __init__(self, db_name='skins_bot.db'):
        self.db_name = db_name
        self.create_tables()

    def get_connection(self):
        """Создает соединение с базой данных"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Чтобы получать данные как словарь
        return conn

    def create_tables(self):

        """Создает необходимые таблицы в базе данных"""

        try:
            with self.get_connection() as conn:
                # Таблица пользователей
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        balance REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Таблица скинов
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS skins (
                        skin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price REAL NOT NULL,
                        rarity TEXT DEFAULT 'Common',
                        roblox_id TEXT,
                        image_url TEXT,
                        quantity INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Таблица инвентаря пользователей
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS user_inventory (
                        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        skin_id INTEGER,
                        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (skin_id) REFERENCES skins (skin_id)
                    )
                ''')

                # Таблица транзакций
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount REAL,
                        type TEXT, -- 'deposit', 'purchase', 'sale'
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')

                # Таблица корзины пользователей
                conn.execute('''
                        CREATE TABLE IF NOT EXISTS user_cart (
                            cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            skin_id INTEGER,
                            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users (user_id),
                            FOREIGN KEY (skin_id) REFERENCES skins (skin_id)
                        )
                    ''')

                logger.info("Таблицы базы данных успешно созданы")

        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")

    def add_user(self, user_id, username, first_name, last_name=None):

        """Добавляет нового пользователя в базу данных"""

        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
                logger.info(f"Пользователь {user_id} добавлен в базу")
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")

    def get_user(self, user_id):

        """Получает информацию о пользователе"""

        try:
            with self.get_connection() as conn:
                user = conn.execute(
                    'SELECT * FROM users WHERE user_id = ?',
                    (user_id,)
                ).fetchone()
                return dict(user) if user else None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None

    def update_user_balance(self, user_id, amount):

        """Обновляет баланс пользователя"""

        try:
            with self.get_connection() as conn:
                conn.execute(
                    'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                    (amount, user_id)
                )
                conn.commit()
                logger.info(f"Баланс пользователя {user_id} обновлен на {amount}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении баланса: {e}")

    def get_all_skins(self):

        """Получает все скины из базы данных"""

        try:
            with self.get_connection() as conn:
                skins = conn.execute('''
                    SELECT * FROM skins WHERE quantity > 0 ORDER BY 
                    CASE rarity
                        WHEN 'Legendary' THEN 1
                        WHEN 'Godly' THEN 2
                        WHEN 'Ancient' THEN 3
                        ELSE 4
                    END,
                    price ASC
                ''').fetchall()
                return [dict(skin) for skin in skins]

        except Exception as e:
            logger.error(f"Ошибка при получении скинов: {e}")
            return []

    def get_skin_by_id(self, skin_id):

        """Получает скин по ID"""

        try:
            with self.get_connection() as conn:
                skin = conn.execute(
                    'SELECT * FROM skins WHERE skin_id = ?',
                    (skin_id,)
                ).fetchone()
                return dict(skin) if skin else None
        except Exception as e:
            logger.error(f"Ошибка при получении скина: {e}")
            return None

    def add_to_inventory(self, user_id, skin_id):

        """Добавляет скин в инвентарь пользователя"""

        try:
            with self.get_connection() as conn:
                # Проверяем, есть ли уже такой скин у пользователя
                existing = conn.execute(
                    'SELECT * FROM user_inventory WHERE user_id = ? AND skin_id = ?',
                    (user_id, skin_id)
                ).fetchone()

                if not existing:
                    conn.execute(
                        'INSERT INTO user_inventory (user_id, skin_id) VALUES (?, ?)',
                        (user_id, skin_id)
                    )
                    # Уменьшаем количество скина
                    conn.execute(
                        'UPDATE skins SET quantity = quantity - 1 WHERE skin_id = ?',
                        (skin_id,)
                    )
                    conn.commit()
                    logger.info(f"Скин {skin_id} добавлен в инвентарь пользователя {user_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при добавлении в инвентарь: {e}")
            return False

    def get_user_inventory(self, user_id):

        """Получает инвентарь пользователя"""

        try:
            with self.get_connection() as conn:
                inventory = conn.execute('''
                    SELECT ui.*, s.name, s.description, s.rarity, s.image_url
                    FROM user_inventory ui
                    JOIN skins s ON ui.skin_id = s.skin_id
                    WHERE ui.user_id = ?
                    ORDER BY ui.purchased_at DESC
                ''', (user_id,)).fetchall()
                return [dict(item) for item in inventory]
        except Exception as e:
            logger.error(f"Ошибка при получении инвентаря: {e}")
            return []

    def add_transaction(self, user_id, amount, transaction_type, description):

        """Добавляет запись о транзакции"""

        try:
            with self.get_connection() as conn:
                conn.execute(
                    'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                    (user_id, amount, transaction_type, description)
                )
                conn.commit()
                logger.info(f"Транзакция добавлена для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении транзакции: {e}")

    def add_skin(self, name, description, price, rarity, roblox_id, image_url, quantity=1):
        """Добавляет новый скин в базу данных"""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO skins (name, description, price, rarity, roblox_id, image_url, quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name, description, price, rarity, roblox_id, image_url, quantity))
                conn.commit()
                logger.info(f"Скин '{name}' добавлен в базу (количество: {quantity})")
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении скина: {e}")
            return False

    def get_all_users(self):

        """Получает всех пользователей"""

        try:
            with self.get_connection() as conn:
                users = conn.execute('''
                    SELECT * FROM users ORDER BY created_at DESC
                ''').fetchall()
                return [dict(user) for user in users]
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            return []

    def get_bot_stats(self):

        """Получает статистику бота"""

        try:
            with self.get_connection() as conn:
                stats = {}

                # Общее количество пользователей
                stats['total_users'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]

                # Общее количество скинов
                stats['total_skins'] = conn.execute('SELECT COUNT(*) FROM skins').fetchone()[0]

                # Общее количество покупок
                stats['total_purchases'] = conn.execute('SELECT COUNT(*) FROM user_inventory').fetchone()[0]

                # Общий оборот
                result = conn.execute('SELECT SUM(amount) FROM transactions WHERE amount < 0').fetchone()[0]
                stats['total_revenue'] = abs(result) if result else 0

                return stats
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}

    def search_skins(self, search_term):

        """Ищет скины по названию или описанию"""

        try:
            with self.get_connection() as conn:
                skins = conn.execute('''
                    SELECT * FROM skins 
                    WHERE quantity > 0 
                    AND (name LIKE ? OR description LIKE ?)
                    ORDER BY 
                        CASE rarity 
                            WHEN 'Legendary' THEN 1
                            WHEN 'Godly' THEN 2 
                            WHEN 'Ancient' THEN 3
                            ELSE 4
                        END,
                        price ASC
                ''', (f'%{search_term}%', f'%{search_term}%')).fetchall()
                return [dict(skin) for skin in skins]
        except Exception as e:
            logger.error(f"Ошибка при поиске скинов: {e}")
            return []

    # -----------------------МЕТОДЫ-КОРЗИНЫ------------------------- #

    def add_to_cart(self, user_id, skin_id):
        """Добавляет скин в корзину пользователя"""
        try:
            with self.get_connection() as conn:
                # Проверяем, есть ли уже в корзине
                existing = conn.execute(
                    'SELECT * FROM user_cart WHERE user_id = ? AND skin_id = ?',
                    (user_id, skin_id)
                ).fetchone()

                if not existing:
                    conn.execute(
                        'INSERT INTO user_cart (user_id, skin_id) VALUES (?, ?)',
                        (user_id, skin_id)
                    )
                    conn.commit()
                    logger.info(f"Скин {skin_id} добавлен в корзину пользователя {user_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при добавлении в корзину: {e}")
            return False

    def get_user_cart(self, user_id):
        """Получает корзину пользователя"""
        try:
            with self.get_connection() as conn:
                cart = conn.execute('''
                    SELECT uc.*, s.name, s.description, s.price, s.rarity, s.quantity, s.image_url
                    FROM user_cart uc
                    JOIN skins s ON uc.skin_id = s.skin_id
                    WHERE uc.user_id = ?
                ''', (user_id,)).fetchall()
                return [dict(item) for item in cart]
        except Exception as e:
            logger.error(f"Ошибка при получении корзины: {e}")
            return []

    def clear_user_cart(self, user_id):
        """Очищает корзину пользователя"""
        try:
            with self.get_connection() as conn:
                conn.execute('DELETE FROM user_cart WHERE user_id = ?', (user_id,))
                conn.commit()
                logger.info(f"Корзина пользователя {user_id} очищена")
                return True
        except Exception as e:
            logger.error(f"Ошибка при очистке корзины: {e}")
            return False

    def remove_from_cart(self, user_id, skin_id):
        """Удаляет скин из корзины"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    'DELETE FROM user_cart WHERE user_id = ? AND skin_id = ?',
                    (user_id, skin_id)
                )
                conn.commit()
                logger.info(f"Скин {skin_id} удален из корзины пользователя {user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении из корзины: {e}")
            return False

    def get_cart_count(self, user_id):
        """Получает количество товаров в корзине"""
        try:
            with self.get_connection() as conn:
                count = conn.execute(
                    'SELECT COUNT(*) FROM user_cart WHERE user_id = ?',
                    (user_id,)
                ).fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"Ошибка при получении количества корзины: {e}")
            return 0

    # -----------------------МЕТОДЫ-ИНВЕНТОРЯ------------------------- #

    def remove_from_inventory_mm2(self, user_id, skin_id):
        """Удаляет скин из инвентаря после вывода в MM2 (без возврата в каталог)"""
        try:
            with self.get_connection() as conn:
                # Проверяем, есть ли скин у пользователя
                inventory_item = conn.execute(
                    'SELECT * FROM user_inventory WHERE user_id = ? AND skin_id = ?',
                    (user_id, skin_id)
                ).fetchone()

                if inventory_item:
                    conn.execute(
                        'DELETE FROM user_inventory WHERE user_id = ? AND skin_id = ?',
                        (user_id, skin_id)
                    )
                    # ⚠️ НЕ возвращаем в каталог - скин продан навсегда
                    conn.commit()
                    logger.info(f"Скин {skin_id} удален из инвентаря пользователя {user_id} (вывод в MM2)")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при удалении из инвентаря: {e}")
            return False

    def get_inventory_with_details(self, user_id):
        """Получает инвентарь с полной информацией о скинах"""
        try:
            with self.get_connection() as conn:
                inventory = conn.execute('''
                    SELECT ui.*, s.skin_id, s.name, s.description, s.rarity, s.image_url, s.price
                    FROM user_inventory ui
                    JOIN skins s ON ui.skin_id = s.skin_id
                    WHERE ui.user_id = ?
                    ORDER BY ui.purchased_at DESC
                ''', (user_id,)).fetchall()
                return [dict(item) for item in inventory]
        except Exception as e:
            logger.error(f"Ошибка при получении детального инвентаря: {e}")
            return []

    # -----------------------АДМИН-ФУНКЦИИ------------------------- #

    def update_user_balance_directly(self, user_id, new_balance):
        """Устанавливает точный баланс пользователя"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    'UPDATE users SET balance = ? WHERE user_id = ?',
                    (new_balance, user_id)
                )
                conn.commit()
                logger.info(f"Баланс пользователя {user_id} установлен на {new_balance}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при установке баланса: {e}")
            return False

    def get_user_purchases(self, user_id):
        """Получает историю покупок пользователя"""
        try:
            with self.get_connection() as conn:
                purchases = conn.execute('''
                    SELECT t.*, s.name as skin_name 
                    FROM transactions t
                    LEFT JOIN user_inventory ui ON t.description LIKE '%' || s.name || '%'
                    LEFT JOIN skins s ON ui.skin_id = s.skin_id
                    WHERE t.user_id = ? AND t.type = 'purchase'
                    ORDER BY t.created_at DESC
                ''', (user_id,)).fetchall()
                return [dict(purchase) for purchase in purchases]
        except Exception as e:
            logger.error(f"Ошибка при получении покупок пользователя: {e}")
            return []

    def get_detailed_stats(self):
        """Получает детальную статистику"""
        try:
            with self.get_connection() as conn:
                stats = {}

                # Базовая статистика
                stats['total_users'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
                stats['total_skins'] = conn.execute('SELECT COUNT(*) FROM skins').fetchone()[0]
                stats['total_purchases'] = conn.execute('SELECT COUNT(*) FROM user_inventory').fetchone()[0]

                # Оборот
                result = conn.execute('SELECT SUM(amount) FROM transactions WHERE amount < 0').fetchone()[0]
                stats['total_revenue'] = abs(result) if result else 0

                # Статистика по редкостям
                rarity_stats = conn.execute('''
                    SELECT rarity, COUNT(*) as count, SUM(price) as total_value 
                    FROM skins GROUP BY rarity
                ''').fetchall()
                stats['rarity_stats'] = [dict(row) for row in rarity_stats]

                # Топ пользователей по балансу
                top_users = conn.execute('''
                    SELECT user_id, username, first_name, balance 
                    FROM users 
                    ORDER BY balance DESC 
                    LIMIT 10
                ''').fetchall()
                stats['top_users'] = [dict(row) for row in top_users]

                # Популярные скины
                popular_skins = conn.execute('''
                    SELECT s.skin_id, s.name, s.rarity, s.price, COUNT(ui.inventory_id) as sales_count
                    FROM skins s
                    LEFT JOIN user_inventory ui ON s.skin_id = ui.skin_id
                    GROUP BY s.skin_id
                    ORDER BY sales_count DESC
                    LIMIT 10
                ''').fetchall()
                stats['popular_skins'] = [dict(row) for row in popular_skins]

                return stats
        except Exception as e:
            logger.error(f"Ошибка при получении детальной статистики: {e}")
            return {}