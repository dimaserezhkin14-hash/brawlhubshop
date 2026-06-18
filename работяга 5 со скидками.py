import telebot
from telebot import types
import sqlite3
import time
import logging
import random
import string
import threading
from datetime import datetime, timedelta

# ==============================================================================
# 1. КОНФИГУРАЦИЯ
# ==============================================================================
API_TOKEN = '8445113525:AAH0-Blr_sptKtjFHu08GDvmSRn9uF8zpCo'
GROUP_ID = -1003588034991 
CARD_NUMBER = '2200154543708779'
START_PHOTO_ID = 'AgACAgIAAyEFAATV3RGvAAMqagJpS7FPSHBgGzIgYCszfkSrTpUAAnUaaxtr6xFIjBvpP2F5h30BAAMCAAN3AAM7BA'
REVIEWS_CHANNEL_LINK = 'https://t.me/BrawlHub_rep'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ArtiLuckBot")
bot = telebot.TeleBot(API_TOKEN)

# ==============================================================================
# 2. БАЗА ДАННЫХ
# ==============================================================================
def init_db():
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            subscription_type TEXT DEFAULT 'free',
            subscription_end TEXT,
            referrer_id INTEGER,
            referral_code TEXT UNIQUE,
            zodiac_sign TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            bonus_days INTEGER DEFAULT 3,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rituals_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ritual_name TEXT,
            performed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            question TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO users (user_id, referral_code) VALUES (?, ?)", (0, 'SYSTEM'))
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# 3. ФУНКЦИЯ ЛОГИРОВАНИЯ В ГРУППУ
# ==============================================================================
def log_to_group(text, reply_markup=None):
    try:
        bot.send_message(GROUP_ID, text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не удалось отправить лог в группу: {e}")

# ==============================================================================
# 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================================================
def get_user_subscription(user_id):
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_type, subscription_end FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return 'free', None
    sub_type = row[0]
    sub_end = row[1]
    if sub_type != 'free' and sub_end:
        try:
            end_date = datetime.fromisoformat(sub_end)
            if datetime.now() > end_date:
                conn = sqlite3.connect('artiluck.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET subscription_type = 'free', subscription_end = NULL WHERE user_id = ?", (user_id,))
                conn.commit()
                conn.close()
                return 'free', None
        except:
            pass
    return sub_type, sub_end

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def send_notification(user_id, title, message):
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notifications (user_id, title, message) VALUES (?, ?, ?)", (user_id, title, message))
    conn.commit()
    conn.close()
    try:
        bot.send_message(user_id, f"📢 <b>{title}</b>\n\n{message}", parse_mode="HTML")
    except:
        pass

def get_luck_percentage():
    return random.randint(60, 98)

def get_luck_message(percentage):
    if percentage >= 90:
        return "🌟 Сегодня звёзды на вашей стороне! День будет полон удачи и приятных сюрпризов!"
    elif percentage >= 75:
        return "✨ Отличный день для новых начинаний! Удача благосклонна к вам."
    elif percentage >= 60:
        return "🍀 Хороший день, чтобы завершить старые дела и начать новые проекты."
    else:
        return "🔮 Все в ваших руках! Небольшие усилия приведут к большим результатам."

def get_zodiac_horoscope(sign):
    horoscopes = {
        "♈ Овен": "Сегодня Овнам стоит быть осторожнее в финансовых вопросах. Звёзды говорят о возможных неожиданных расходах. Но в любви вас ждёт приятный сюрприз!",
        "♉ Телец": "Тельцам сегодня стоит прислушаться к своей интуиции. Она подскажет правильное решение в сложной ситуации. День благоприятен для творчества.",
        "♊ Близнецы": "Близнецов сегодня ждёт много общения и новых знакомств. Будьте открыты к новым возможностям. Вечером возможен романтический сюрприз.",
        "♋ Рак": "Ракам сегодня стоит уделить время семье и близким. Звёзды говорят о важном разговоре, который всё изменит. День полон эмоций.",
        "♌ Лев": "Львов сегодня ждёт успех в делах и признание окружающих. Ваша энергия и харизма привлекут удачу. Отличный день для презентаций!",
        "♍ Дева": "Девам сегодня стоит заняться здоровьем и режимом дня. Звёзды советуют отдохнуть и набраться сил перед важными событиями.",
        "♎ Весы": "Весам сегодня улыбнётся удача в финансовых вопросах. Возможно неожиданное поступление денег. В личной жизни гармония и понимание.",
        "♏ Скорпион": "Скорпионам сегодня стоит быть осторожнее в общении. Звёзды предупреждают о возможных конфликтах. Но в любви всё будет хорошо!",
        "♐ Стрелец": "Стрельцов сегодня ждёт удача в путешествиях и обучении. Новые знания откроют перед вами новые возможности. День полон приключений!",
        "♑ Козерог": "Козерогам сегодня стоит сосредоточиться на карьере. Звёзды говорят о продвижении по службе. Не бойтесь брать на себя ответственность.",
        "♒ Водолей": "Водолеев сегодня ждёт творческий подъём и вдохновение. Ваши идеи найдут поддержку у окружающих. Отличный день для реализации проектов!",
        "♓ Рыбы": "Рыбам сегодня стоит прислушаться к своей интуиции. Звёзды говорят о важных знаках судьбы. В любви вас ждёт приятное свидание."
    }
    return horoscopes.get(sign, "🔮 Сегодня звёзды благосклонны к вам! День будет удачным.")

# ==============================================================================
# 5. РИТУАЛЫ
# ==============================================================================
RITUALS = {
    "🍀 Утренний ритуал": {
        "free": True,
        "description": "Проснись с благодарностью и позитивным настроем.",
        "action": "Скажите вслух: «Сегодня меня ждёт удача!»\nПотянитесь 3 раза.\nУлыбнитесь своему отражению в зеркале."
    },
    "🌙 Вечерний ритуал": {
        "free": True,
        "description": "Заверши день с осознанностью и благодарностью.",
        "action": "Скажите вслух: «Я благодарен за сегодняшний день».\nЗапишите 3 хороших события дня.\nЗагадайте желание на завтра."
    },
    "💰 Ритуал на деньги": {
        "free": True,
        "description": "Привлечение финансового потока.",
        "action": "Возьмите купюру в руки.\nПредставьте как она превращается в большой денежный поток.\nСкажите: «Деньги приходят ко мне легко и быстро»."
    },
    "❤️ Ритуал на любовь": {
        "free": True,
        "description": "Привлечение любви и гармоничных отношений.",
        "action": "Закройте глаза.\nПредставьте тёплый свет в груди.\nСкажите: «Я открыт для любви и счастья»."
    },
    "🎯 Ритуал на удачу": {
        "free": True,
        "description": "Привлечение удачи в делах и начинаниях.",
        "action": "Скажите: «Удача идёт со мной по жизни».\nПохлопайте в ладоши 3 раза.\nПодбросьте монетку."
    },
    "🔮 Индивидуальный гороскоп (Premium)": {
        "free": False,
        "description": "Персональный гороскоп на день, неделю, месяц.",
        "action": "Ваш гороскоп уже сформирован.\nОтправьте свой знак зодиака в чат, чтобы получить прогноз."
    },
    "📿 Амулеты (Premium)": {
        "free": False,
        "description": "Энергетическая защита и усиление удачи.",
        "action": "Доступно 10+ амулетов на разные сферы жизни.\nПолучите свой личный амулет успеха."
    }
}

# ==============================================================================
# 6. КЛАВИАТУРЫ
# ==============================================================================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🌟 Ритуалы"),
        types.KeyboardButton("🔮 Мой гороскоп")
    )
    markup.add(
        types.KeyboardButton("👤 Профиль"),
        types.KeyboardButton("📋 Мои подписки")
    )
    markup.add(
        types.KeyboardButton("👥 Реферальная система"),
        types.KeyboardButton("💬 Поддержка")
    )
    markup.add(
        types.KeyboardButton("ℹ️ О проекте")
    )
    return markup

def rituals_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🍀 Утренний ритуал"),
        types.KeyboardButton("🌙 Вечерний ритуал")
    )
    markup.add(
        types.KeyboardButton("💰 Ритуал на деньги"),
        types.KeyboardButton("❤️ Ритуал на любовь")
    )
    markup.add(
        types.KeyboardButton("🎯 Ритуал на удачу"),
        types.KeyboardButton("◀️ Назад")
    )
    return markup

def zodiac_menu():
    markup = types.InlineKeyboardMarkup(row_width=3)
    signs = [
        "♈ Овен", "♉ Телец", "♊ Близнецы",
        "♋ Рак", "♌ Лев", "♍ Дева",
        "♎ Весы", "♏ Скорпион", "♐ Стрелец",
        "♑ Козерог", "♒ Водолей", "♓ Рыбы"
    ]
    for sign in signs:
        markup.add(types.InlineKeyboardButton(sign, callback_data=f"zodiac_{sign}"))
    return markup

def subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🌟 Базовая подписка (Бесплатно)", callback_data="sub_base"),
        types.InlineKeyboardButton("👑 Премиум подписка (Скоро)", callback_data="sub_premium_soon"),
        types.InlineKeyboardButton("🎁 Активировать промокод", callback_data="promo_activate")
    )
    return markup

def back_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("◀️ Назад"))
    return markup

def get_group_admin_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Сделать рассылку", callback_data="adm_panel_broadcast"),
        types.InlineKeyboardButton("✉️ Написать юзеру", callback_data="adm_panel_write_user")
    )
    markup.add(
        types.InlineKeyboardButton("🔍 Узнать ID по юзеру", callback_data="adm_panel_find_id"),
        types.InlineKeyboardButton("📊 Статистика", callback_data="adm_panel_stats")
    )
    markup.add(
        types.InlineKeyboardButton("❌ Закрыть панель", callback_data="adm_panel_close")
    )
    return markup

def get_broadcast_confirm_inline():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🟢 ДА, ЗАПУСТИТЬ", callback_data="confirm_broadcast_yes"),
        types.InlineKeyboardButton("🔴 ОТМЕНА", callback_data="confirm_broadcast_no")
    )
    return markup

# ==============================================================================
# 7. ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ АДМИНКИ
# ==============================================================================
pending_broadcast_text = {}

# ==============================================================================
# 8. ОСНОВНЫЕ ОБРАБОТЧИКИ
# ==============================================================================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    username = message.from_user.username or ''
    full_name = message.from_user.full_name or ''
    text = message.text
    
    log_to_group(f"🟢 Пользователь @{username} (ID: {uid}) запустил бота Артимейка")
    
    referrer_id = None
    if len(text.split()) > 1:
        ref_code = text.split()[1]
        conn = sqlite3.connect('artiluck.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
        row = cursor.fetchone()
        conn.close()
        if row:
            referrer_id = row[0]
            log_to_group(f"🔄 Реферальный переход: @{username} (ID: {uid}) по коду {ref_code} от реферера ID: {referrer_id}")
    
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (uid, username, full_name))
    cursor.execute("UPDATE users SET username = ?, full_name = ? WHERE user_id = ?", (username, full_name, uid))
    
    cursor.execute("SELECT subscription_type FROM users WHERE user_id = ?", (uid,))
    sub_row = cursor.fetchone()
    if sub_row and sub_row[0] == 'free':
        new_end = (datetime.now() + timedelta(days=7)).isoformat()
        cursor.execute("UPDATE users SET subscription_type = 'base', subscription_end = ? WHERE user_id = ?", (new_end, uid))
        log_to_group(f"🎁 Пользователю @{username} (ID: {uid}) выдана базовая подписка на 7 дней")
    
    if referrer_id and referrer_id != uid:
        cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (uid,))
        existing_ref = cursor.fetchone()
        if not existing_ref or not existing_ref[0]:
            cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, uid))
            cursor.execute("INSERT INTO referrals (referrer_id, referred_id, bonus_days) VALUES (?, ?, 7)", (referrer_id, uid))
            
            cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (uid,))
            current_end_row = cursor.fetchone()
            if current_end_row and current_end_row[0]:
                try:
                    current_end = datetime.fromisoformat(current_end_row[0])
                    new_end = (current_end + timedelta(days=7)).isoformat()
                except:
                    new_end = (datetime.now() + timedelta(days=14)).isoformat()
            else:
                new_end = (datetime.now() + timedelta(days=14)).isoformat()
            cursor.execute("UPDATE users SET subscription_type = 'base', subscription_end = ? WHERE user_id = ?", (new_end, uid))
            
            cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (referrer_id,))
            ref_row = cursor.fetchone()
            if ref_row and ref_row[0]:
                try:
                    current_end = datetime.fromisoformat(ref_row[0])
                    new_ref_end = (current_end + timedelta(days=3)).isoformat()
                except:
                    new_ref_end = (datetime.now() + timedelta(days=3)).isoformat()
            else:
                new_ref_end = (datetime.now() + timedelta(days=3)).isoformat()
            cursor.execute("UPDATE users SET subscription_type = 'base', subscription_end = ? WHERE user_id = ?", (new_ref_end, referrer_id))
            
            send_notification(uid, "🎉 Вам подарок!", "Вы получили +7 дней базовой подписки за переход по реферальной ссылке!")
            send_notification(referrer_id, "🎉 Новый реферал!", "Ваш друг перешёл по ссылке! Вы получили +3 дня подписки.")
            log_to_group(f"✅ Реферал активирован: @{username} (ID: {uid}) получил +7 дней, реферер ID: {referrer_id} получил +3 дня")
    
    conn.commit()
    conn.close()
    
    luck_percent = get_luck_percentage()
    luck_msg = get_luck_message(luck_percent)
    
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("SELECT zodiac_sign FROM users WHERE user_id = ?", (uid,))
    zodiac_row = cursor.fetchone()
    conn.close()
    
    zodiac_text = ""
    if zodiac_row and zodiac_row[0]:
        zodiac_text = f"\n♈ <b>Ваш знак зодиака: {zodiac_row[0]}</b>\n"
    
    welcome = (
        f"🎨 <b>Добро пожаловать в бот удачи от Артимейка!</b>\n\n"
        f"🔮 <b>Ваша удача сегодня: {luck_percent}%</b>\n"
        f"{luck_msg}\n"
        f"{zodiac_text}\n"
        "🌟 Здесь вы найдёте ритуалы, гороскопы и амулеты для привлечения удачи.\n\n"
        "🎁 <b>Вам подарок!</b> Базовая подписка на 7 дней уже активна!\n"
        "🔮 <b>Ваш статус: БАЗОВАЯ ПОДПИСКА</b>\n"
        "💎 <b>Подписка даёт:</b>\n"
        "• Доступ ко всем ритуалам\n"
        "• Индивидуальный гороскоп\n"
        "• Персональные амулеты\n"
        "• Приоритетная поддержка\n\n"
        "📢 <b>Акция!</b> Пригласи друга — получи 3 дня подписки, а друг 7 дней! 🎁"
    )
    
    try:
        bot.send_photo(uid, PHOTO_ID, caption=welcome, reply_markup=main_menu(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не удалось отправить фото: {e}")
        bot.send_message(uid, welcome, reply_markup=main_menu(), parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "◀️ Назад")
def back_to_main(message):
    uid = message.chat.id
    bot.send_message(uid, "◀️ Главное меню:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔮 Мой гороскоп")
def my_horoscope(message):
    uid = message.chat.id
    
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("SELECT zodiac_sign FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0]:
        sign = row[0]
        horoscope_text = get_zodiac_horoscope(sign)
        luck_percent = get_luck_percentage()
        
        text = (
            f"♈ <b>Ваш знак зодиака: {sign}</b>\n\n"
            f"🔮 {horoscope_text}\n\n"
            f"🔮 <b>Удача сегодня: {luck_percent}%</b>\n"
            f"{get_luck_message(luck_percent)}\n\n"
            f"🔄 <i>Чтобы изменить знак, нажмите кнопку «Выбрать знак зодиака» ниже.</i>"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("♈ Выбрать знак зодиака", callback_data="choose_zodiac"))
        bot.send_message(uid, text, reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(uid, "♈ <b>Выберите ваш знак зодиака:</b>", reply_markup=zodiac_menu(), parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🌟 Ритуалы")
def show_rituals(message):
    uid = message.chat.id
    sub_type, _ = get_user_subscription(uid)
    text = "🌟 <b>Доступные ритуалы:</b>\n\n"
    for name, info in RITUALS.items():
        if info["free"] or sub_type != 'free':
            status = "✅" if info["free"] or sub_type != 'free' else "🔒"
            text += f"{status} {name}\n"
    bot.send_message(uid, text, reply_markup=rituals_menu(), parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text in RITUALS)
def perform_ritual(message):
    uid = message.chat.id
    ritual_name = message.text
    ritual = RITUALS[ritual_name]
    sub_type, _ = get_user_subscription(uid)
    
    username = message.from_user.username or 'нет'
    log_to_group(f"🧘 Пользователь @{username} (ID: {uid}) выполняет ритуал: {ritual_name}")
    
    if not ritual["free"] and sub_type == 'free':
        bot.send_message(uid, 
            "🔒 <b>Этот ритуал доступен только по подписке!</b>\n\n"
            "Оформите подписку, чтобы получить доступ к:\n"
            "• Индивидуальному гороскопу\n"
            "• Персональным амулетам\n"
            "• 10+ эксклюзивным ритуалам\n"
            "• Приоритетной поддержке\n\n"
            "💎 Базовая подписка — БЕСПЛАТНО",
            reply_markup=subscription_menu(),
            parse_mode="HTML"
        )
        return
    
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rituals_log (user_id, ritual_name) VALUES (?, ?)", (uid, ritual_name))
    conn.commit()
    conn.close()
    
    luck_percent = get_luck_percentage()
    luck_msg = get_luck_message(luck_percent)
    
    text = (
        f"🧘 <b>{ritual_name}</b>\n\n"
        f"📖 {ritual['description']}\n\n"
        f"✨ <b>Как выполнить:</b>\n{ritual['action']}\n\n"
        f"🔮 <b>Ваша удача после ритуала: {luck_percent}%</b>\n"
        f"{luck_msg}\n\n"
        f"🙏 Удачи! Вы на правильном пути."
    )
    bot.send_message(uid, text, parse_mode="HTML")
    luck_score = random.randint(1, 10)
    send_notification(uid, "⭐ Удача растёт!", f"Вы получили +{luck_score} очков удачи за выполнение ритуала!")
    log_to_group(f"⭐ Пользователь @{username} (ID: {uid}) получил +{luck_score} очков удачи за ритуал {ritual_name}")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    uid = message.chat.id
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, full_name, subscription_type, subscription_end, referral_code, zodiac_sign FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        start(message)
        return
    
    username, full_name, sub_type, sub_end, ref_code, zodiac_sign = row
    sub_type_names = {'free': 'Бесплатный', 'base': 'Базовая', 'premium': 'Премиум'}
    sub_type_display = sub_type_names.get(sub_type, 'Бесплатный')
    status_emoji = "💎" if sub_type != 'free' else "🆓"
    
    cursor.execute("SELECT COUNT(*) FROM rituals_log WHERE user_id = ?", (uid,))
    rituals_count = cursor.fetchone()[0]
    conn.close()
    
    luck_percent = get_luck_percentage()
    
    text = (
        f"👤 <b>Ваш профиль в боте Артимейка</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"👤 Имя: {full_name or 'Не указано'}\n"
        f"📛 Юзернейм: @{username or 'Не указан'}\n"
        f"♈ Знак зодиака: {zodiac_sign or 'Не выбран'}\n"
        f"{status_emoji} Статус: <b>{sub_type_display}</b>\n"
        f"🔮 Удача сегодня: <b>{luck_percent}%</b>\n"
        f"{get_luck_message(luck_percent)}\n"
    )
    if sub_end:
        try:
            end_date = datetime.fromisoformat(sub_end)
            days_left = (end_date - datetime.now()).days
            text += f"⏳ Осталось дней подписки: <b>{days_left}</b>\n"
        except:
            pass
    
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={ref_code}" if ref_code else "Нет ссылки"
    text += f"\n🔗 Реферальная ссылка:\n<code>{ref_link}</code>\n"
    text += f"\n📊 Выполнено ритуалов: <b>{rituals_count}</b>"
    
    bot.send_message(uid, text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📋 Мои подписки")
def my_subscriptions(message):
    uid = message.chat.id
    sub_type, sub_end = get_user_subscription(uid)
    sub_names = {'free': '🆓 Бесплатная', 'base': '🌟 Базовая', 'premium': '👑 Премиум'}
    text = f"📋 <b>Ваша подписка</b>\n\n"
    text += f"Тип: {sub_names.get(sub_type, 'Бесплатная')}\n"
    if sub_end:
        try:
            end_date = datetime.fromisoformat(sub_end)
            days_left = (end_date - datetime.now()).days
            text += f"Действует до: {end_date.strftime('%d.%m.%Y')}\n"
            text += f"Осталось дней: <b>{days_left}</b>\n"
        except:
            text += f"Действует до: {sub_end}\n"
    else:
        if sub_type == 'free':
            text += "\n💎 <b>Преимущества подписки:</b>\n"
            text += "• Индивидуальный гороскоп\n"
            text += "• Персональные амулеты\n"
            text += "• Доступ к 10+ ритуалам\n"
            text += "• Приоритетная поддержка\n"
    
    luck_percent = get_luck_percentage()
    text += f"\n\n🔮 <b>Ваша удача сегодня: {luck_percent}%</b>"
    text += f"\n{get_luck_message(luck_percent)}"
    
    text += "\n\n👇 Оформите подписку:"
    bot.send_message(uid, text, reply_markup=subscription_menu(), parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "👥 Реферальная система")
def referral_system(message):
    uid = message.chat.id
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("SELECT referral_code FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    ref_code = row[0] if row else None
    if not ref_code:
        ref_code = generate_referral_code()
        cursor.execute("UPDATE users SET referral_code = ? WHERE user_id = ?", (ref_code, uid))
        conn.commit()
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (uid,))
    count = cursor.fetchone()[0]
    conn.close()
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={ref_code}"
    
    luck_percent = get_luck_percentage()
    
    text = (
        "👥 <b>Реферальная система Артимейка</b>\n\n"
        "💰 <b>Зарабатывай подписку!</b>\n\n"
        "🔗 <b>Твоя реферальная ссылка:</b>\n"
        f"<code>{link}</code>\n\n"
        "📊 <b>Статистика:</b>\n"
        f"👤 Приглашено друзей: <b>{count}</b>\n\n"
        "🎁 <b>Бонусы:</b>\n"
        "• Ты получаешь <b>3 дня подписки</b> за каждого друга\n"
        "• Друг получает <b>7 дней подписки</b> БЕСПЛАТНО!\n"
        "• Новые пользователи получают <b>7 дней подписки</b> сразу при старте!\n\n"
        f"🔮 <b>Ваша удача сегодня: {luck_percent}%</b>\n"
        f"{get_luck_message(luck_percent)}\n\n"
        "📤 Отправь ссылку другу и получай бонусы!"
    )
    bot.send_message(uid, text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💬 Поддержка")
def support(message):
    uid = message.chat.id
    msg = bot.send_message(uid, "💬 <b>Напишите ваш вопрос или проблему:</b>\n\nМы ответим вам в ближайшее время.", reply_markup=back_button(), parse_mode="HTML")
    bot.register_next_step_handler(msg, process_support_request)

def process_support_request(message):
    uid = message.chat.id
    if message.text == "◀️ Назад":
        bot.send_message(uid, "Вы вернулись в главное меню.", reply_markup=main_menu())
        return
    question = message.text
    username = message.from_user.username or 'нет'
    full_name = message.from_user.full_name or 'нет'
    
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO support_requests (user_id, username, question) VALUES (?, ?, ?)", (uid, username, question))
    conn.commit()
    conn.close()
    
    bot.send_message(uid, "✅ <b>Ваш вопрос отправлен!</b>\n\nМы ответим вам в ближайшее время.", reply_markup=main_menu(), parse_mode="HTML")
    
    text = (
        f"💬 <b>НОВЫЙ ЗАПРОС В ПОДДЕРЖКУ АРТИМЕЙКА</b>\n\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"👤 Имя: {full_name}\n"
        f"📛 Юзернейм: @{username}\n\n"
        f"📝 <b>Вопрос:</b>\n{question}"
    )
    log_to_group(text)

@bot.message_handler(func=lambda m: m.text == "ℹ️ О проекте")
def about_project(message):
    uid = message.chat.id
    luck_percent = get_luck_percentage()
    
    text = (
        "🎨 <b>О проекте «Бот Удачи от Артимейка»</b>\n\n"
        "🔮 Это бот для привлечения удачи, гармонии и успеха в вашу жизнь.\n\n"
        "🌟 <b>Что мы предлагаем:</b>\n"
        "• Эффективные ритуалы на все случаи жизни\n"
        "• Индивидуальный гороскоп\n"
        "• Персональные амулеты\n"
        "• Поддержку 24/7\n\n"
        "💎 <b>Подписки:</b>\n"
        "• Базовая — БЕСПЛАТНО (7 дней новым пользователям!)\n"
        "• Премиум — СКОРО\n\n"
        "📢 <b>Акция!</b> Пригласи друга и получи 3 дня подписки!\n"
        "Друг получает 7 дней бесплатно! 🎁\n\n"
        f"🔮 <b>Ваша удача сегодня: {luck_percent}%</b>\n"
        f"{get_luck_message(luck_percent)}\n\n"
        "🙏 Удачи вам на всех путях, друзья Артимейка!"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# ==============================================================================
# 9. CALLBACK-ОБРАБОТЧИКИ
# ==============================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("zodiac_"))
def set_zodiac_sign(call):
    uid = call.message.chat.id
    sign = call.data.replace("zodiac_", "")
    
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET zodiac_sign = ? WHERE user_id = ?", (sign, uid))
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id, f"✅ Знак {sign} сохранён!")
    
    horoscope_text = get_zodiac_horoscope(sign)
    luck_percent = get_luck_percentage()
    
    text = (
        f"♈ <b>Ваш знак зодиака: {sign}</b>\n\n"
        f"🔮 {horoscope_text}\n\n"
        f"🔮 <b>Удача сегодня: {luck_percent}%</b>\n"
        f"{get_luck_message(luck_percent)}\n\n"
        f"🔄 <i>Чтобы изменить знак, нажмите кнопку «Выбрать знак зодиака» ниже.</i>"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("♈ Выбрать знак зодиака", callback_data="choose_zodiac"))
    
    bot.edit_message_text(text, chat_id=uid, message_id=call.message.message_id, reply_markup=markup, parse_mode="HTML")
    
    log_to_group(f"♈ Пользователь @{call.from_user.username or 'нет'} (ID: {uid}) выбрал знак зодиака: {sign}")

@bot.callback_query_handler(func=lambda call: call.data == "choose_zodiac")
def choose_zodiac(call):
    uid = call.message.chat.id
    bot.edit_message_text("♈ <b>Выберите ваш знак зодиака:</b>", chat_id=uid, message_id=call.message.message_id, reply_markup=zodiac_menu(), parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "sub_base")
def process_base_subscription(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id, "⏳ Базовая подписка пока не доступна для продления. Вы уже получили 7 дней при запуске!", show_alert=True)
    bot.edit_message_text(
        f"⏳ <b>Базовая подписка</b>\n\n"
        f"🌟 Вы уже получили <b>7 дней</b> базовой подписки при запуске бота!\n\n"
        f"Если подписка закончится, вы сможете продлить её здесь.\n\n"
        f"👑 <b>Премиум подписка скоро появится!</b>",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "sub_premium_soon")
def premium_soon(call):
    bot.answer_callback_query(call.id, "⏳ Премиум подписка скоро появится! Ожидайте обновления.", show_alert=True)
    bot.edit_message_text(
        f"⏳ <b>Премиум подписка скоро!</b>\n\n"
        f"👑 Артимейк готовит для вас нечто особенное!\n"
        f"В ближайшее время появятся:\n"
        f"• Индивидуальный гороскоп\n"
        f"• Персональные амулеты\n"
        f"• 10+ эксклюзивных ритуалов\n"
        f"• Приоритетная поддержка\n\n"
        f"📢 <b>Следите за обновлениями!</b>",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "promo_activate")
def promo_activate_prompt(call):
    uid = call.message.chat.id
    bot.answer_callback_query(call.id)
    msg = bot.send_message(uid, "✏️ Введите промокод:")
    bot.register_next_step_handler(msg, process_promo)

def process_promo(message):
    uid = message.chat.id
    promo = message.text.strip().upper()
    promos = {
        "ARTI2026": {"days": 30, "type": "base"},
        "LUCKARTI": {"days": 14, "type": "base"},
        "HELLOARTI": {"days": 7, "type": "base"}
    }
    
    username = message.from_user.username or 'нет'
    log_to_group(f"🎟 Пользователь @{username} (ID: {uid}) активирует промокод: {promo}")
    
    if promo in promos:
        days = promos[promo]["days"]
        sub_type = promos[promo]["type"]
        new_end = (datetime.now() + timedelta(days=days)).isoformat()
        conn = sqlite3.connect('artiluck.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET subscription_type = ?, subscription_end = ? WHERE user_id = ?", (sub_type, new_end, uid))
        conn.commit()
        conn.close()
        
        luck_percent = get_luck_percentage()
        
        bot.send_message(uid, 
            f"✅ <b>Промокод активирован!</b>\n\n"
            f"🎁 Вы получили {days} дней {sub_type} подписки!\n\n"
            f"🔮 <b>Ваша удача сегодня: {luck_percent}%</b>\n"
            f"{get_luck_message(luck_percent)}", 
            parse_mode="HTML"
        )
        send_notification(uid, "🎁 Промокод активирован!", f"Вы активировали промокод {promo} и получили {days} дней подписки!")
        log_to_group(f"✅ Промокод {promo} активирован пользователем @{username} (ID: {uid})")
    else:
        bot.send_message(uid, "❌ Промокод не найден. Попробуйте другой.")
        log_to_group(f"❌ Неверный промокод {promo} от пользователя @{username} (ID: {uid})")

# ==============================================================================
# 10. АДМИН-ПАНЕЛЬ (ДЛЯ ГРУППЫ)
# ==============================================================================
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID)
def admin_group_handler(message):
    if message.text in ["/panel", "/admin", "панель", "Панель"]:
        log_to_group("⚙️ <b>Панель управления ботом Артимейка:</b>", reply_markup=get_group_admin_inline_menu())
    elif message.reply_to_message:
        rep_msg = message.reply_to_message.text or message.reply_to_message.caption
        if rep_msg and "ID:" in rep_msg:
            try:
                lines = rep_msg.split("\n")
                t_id = None
                for line in lines:
                    if "ID:" in line:
                        parts = line.split("ID:")
                        if len(parts) > 1:
                            t_id = int(parts[1].strip().replace("<code>", "").replace("</code>", "").split()[0])
                            break
                if t_id:
                    if message.content_type == 'photo':
                        bot.send_photo(t_id, message.photo[-1].file_id, caption=message.caption)
                    else:
                        bot.send_message(t_id, f"✉️ <b>Ответ поддержки Артимейка:</b>\n\n{message.text}", parse_mode="HTML")
                    bot.reply_to(message, f"✅ Ответ отправлен пользователю <code>{t_id}</code>", parse_mode="HTML")
                    log_to_group(f"✅ Ответ отправлен пользователю ID: {t_id}")
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка: {e}", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.message.chat.id == GROUP_ID)
def admin_callback(call):
    bot.answer_callback_query(call.id)
    
    if call.data == "adm_panel_broadcast":
        msg = bot.send_message(GROUP_ID, "📢 Введите текст для рассылки:")
        bot.register_next_step_handler(msg, admin_broadcast_step1)
    elif call.data == "adm_panel_write_user":
        msg = bot.send_message(GROUP_ID, "✉️ Введите: <code>ID_или_username текст</code>", parse_mode="HTML")
        bot.register_next_step_handler(msg, admin_send_to_user)
    elif call.data == "adm_panel_find_id":
        msg = bot.send_message(GROUP_ID, "🔍 Введите юзернейм без @:")
        bot.register_next_step_handler(msg, admin_find_id)
    elif call.data == "adm_panel_stats":
        admin_stats(call.message)
    elif call.data == "adm_panel_close":
        bot.edit_message_text("🏁 Панель закрыта.", GROUP_ID, call.message.message_id)

def admin_broadcast_step1(message):
    text = message.text.strip()
    pending_broadcast_text[GROUP_ID] = text
    bot.send_message(GROUP_ID, f"⚠️ <b>Подтвердите рассылку:</b>\n\n{text}", reply_markup=get_broadcast_confirm_inline(), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_broadcast_yes", "confirm_broadcast_no"] and call.message.chat.id == GROUP_ID)
def admin_broadcast_confirm(call):
    if call.data == "confirm_broadcast_yes":
        text = pending_broadcast_text.get(GROUP_ID, "")
        if not text:
            bot.edit_message_text("❌ Ошибка: текст не найден.", GROUP_ID, call.message.message_id)
            return
        bot.edit_message_text("⏳ Рассылка запущена...", GROUP_ID, call.message.message_id)
        count = 0
        conn = sqlite3.connect('artiluck.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()
        for row in users:
            try:
                bot.send_message(row[0], f"📢 <b>Сообщение от Артимейка</b>\n\n{text}", parse_mode="HTML")
                count += 1
                time.sleep(0.05)
            except:
                pass
        bot.send_message(GROUP_ID, f"✅ Рассылка завершена. Доставлено <code>{count}</code> пользователям.", reply_markup=get_group_admin_inline_menu(), parse_mode="HTML")
        log_to_group(f"📢 Выполнена рассылка для {count} пользователей Артимейка")
        if GROUP_ID in pending_broadcast_text:
            del pending_broadcast_text[GROUP_ID]
    else:
        bot.edit_message_text("❌ Рассылка отменена.", GROUP_ID, call.message.message_id)
        bot.send_message(GROUP_ID, "Панель управления:", reply_markup=get_group_admin_inline_menu())
        if GROUP_ID in pending_broadcast_text:
            del pending_broadcast_text[GROUP_ID]

def admin_send_to_user(message):
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.send_message(GROUP_ID, "❌ Формат: <code>ID_или_username текст</code>", parse_mode="HTML")
            return
        target = parts[0].strip()
        msg_text = parts[1].strip()
        target_id = None
        if target.isdigit():
            target_id = int(target)
        else:
            username_to_find = target.replace("@", "").lower()
            conn = sqlite3.connect('artiluck.db')
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (username_to_find,))
            row = cursor.fetchone()
            conn.close()
            if row:
                target_id = row[0]
        if target_id:
            bot.send_message(target_id, f"✉️ <b>Сообщение от Артимейка:</b>\n\n{msg_text}", parse_mode="HTML")
            bot.send_message(GROUP_ID, f"✅ Отправлено пользователю <code>{target_id}</code>", reply_markup=get_group_admin_inline_menu(), parse_mode="HTML")
            log_to_group(f"✉️ Отправлено сообщение пользователю ID: {target_id}")
        else:
            bot.send_message(GROUP_ID, f"❌ Пользователь {target} не найден.", reply_markup=get_group_admin_inline_menu(), parse_mode="HTML")
    except Exception as e:
        bot.send_message(GROUP_ID, f"❌ Ошибка: {e}", reply_markup=get_group_admin_inline_menu(), parse_mode="HTML")

def admin_find_id(message):
    try:
        username = message.text.strip().replace("@", "").lower()
        conn = sqlite3.connect('artiluck.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            bot.send_message(GROUP_ID, f"🔍 @{username} → ID: <code>{row[0]}</code>", reply_markup=get_group_admin_inline_menu(), parse_mode="HTML")
            log_to_group(f"🔍 Поиск пользователя @{username} — ID: {row[0]}")
        else:
            bot.send_message(GROUP_ID, f"❌ @{username} не найден.", reply_markup=get_group_admin_inline_menu(), parse_mode="HTML")
    except Exception as e:
        bot.send_message(GROUP_ID, f"❌ Ошибка: {e}", reply_markup=get_group_admin_inline_menu(), parse_mode="HTML")

def admin_stats(message):
    conn = sqlite3.connect('artiluck.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_type != 'free'")
    premium_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM rituals_log")
    total_rituals = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM referrals")
    total_refs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM support_requests WHERE status = 'pending'")
    pending_support = cursor.fetchone()[0]
    conn.close()
    
    text = (
        f"📊 <b>СТАТИСТИКА БОТА АРТИМЕЙКА</b>\n\n"
        f"👤 Всего пользователей: <b>{total_users}</b>\n"
        f"💎 Пользователей с подпиской: <b>{premium_users}</b>\n"
        f"🧘 Выполнено ритуалов: <b>{total_rituals}</b>\n"
        f"👥 Реферальных переходов: <b>{total_refs}</b>\n"
        f"💬 Ожидают ответа в поддержке: <b>{pending_support}</b>"
    )
    bot.send_message(GROUP_ID, text, parse_mode="HTML", reply_markup=get_group_admin_inline_menu())
    log_to_group("📊 Запрошена статистика бота")

# ==============================================================================
# 11. CATCH ALL - ВСЕ ОСТАЛЬНЫЕ СООБЩЕНИЯ (В САМОМ КОНЦЕ)
# ==============================================================================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def catch_all(message):
    uid = message.chat.id
    text = message.text
    
    if message.chat.id == GROUP_ID:
        return
    
    menu_texts = ["🌟 Ритуалы", "🔮 Мой гороскоп", "👤 Профиль", "📋 Мои подписки", 
                  "👥 Реферальная система", "💬 Поддержка", "ℹ️ О проекте", "◀️ Назад",
                  "🍀 Утренний ритуал", "🌙 Вечерний ритуал", "💰 Ритуал на деньги", 
                  "❤️ Ритуал на любовь", "🎯 Ритуал на удачу"]
    if text in menu_texts:
        return
    
    zodiac_signs = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
    if any(sign in text for sign in zodiac_signs):
        sub_type, _ = get_user_subscription(uid)
        if sub_type != 'free':
            fortunes = [
                "Звёзды говорят, что сегодня удача на вашей стороне!",
                "Ваш день будет полон приятных сюрпризов.",
                "Сегодня — отличный день для новых начинаний.",
                "Прислушайтесь к своей интуиции сегодня.",
                "Звёзды предвещают прибыль и успех."
            ]
            luck_percent = get_luck_percentage()
            bot.send_message(uid, 
                f"🔮 <b>Ваш гороскоп от Артимейка для {text}</b>\n\n"
                f"{random.choice(fortunes)}\n\n"
                f"🔮 <b>Удача сегодня: {luck_percent}%</b>\n"
                f"{get_luck_message(luck_percent)}", 
                parse_mode="HTML"
            )
            return
    
    bot.send_message(uid, "❓ Используйте кнопки меню для навигации.", reply_markup=main_menu())
    log_to_group(f"❓ Пользователь @{message.from_user.username or 'нет'} (ID: {uid}) ввел неизвестную команду: {text}")

# ==============================================================================
# 12. ФОНОВЫЙ ПРОЦЕСС ДЛЯ УВЕДОМЛЕНИЙ
# ==============================================================================
def daily_notifications():
    while True:
        try:
            conn = sqlite3.connect('artiluck.db')
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, subscription_end FROM users WHERE subscription_type != 'free'")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                user_id, sub_end = row
                if sub_end:
                    try:
                        end_date = datetime.fromisoformat(sub_end)
                        days_left = (end_date - datetime.now()).days
                        if days_left == 3:
                            send_notification(user_id, "⏳ Подписка истекает!", "Ваша подписка в боте Артимейка истекает через 3 дня. Продлите её, чтобы не потерять доступ к ритуалам!")
                            log_to_group(f"⏳ Уведомление об истечении подписки отправлено пользователю ID: {user_id}")
                        elif days_left == 1:
                            send_notification(user_id, "⚠️ Подписка истекает завтра!", "Завтра ваша подписка в боте Артимейка истекает. Продлите её сейчас!")
                            log_to_group(f"⚠️ Уведомление об истечении подписки отправлено пользователю ID: {user_id}")
                    except:
                        pass
            time.sleep(86400)
        except:
            time.sleep(60)

# ==============================================================================
# 13. ЗАПУСК
# ==============================================================================
if __name__ == '__main__':
    print("🎨 Бот Удачи от Артимейка запущен!")
    print(f"🤖 Бот: @{bot.get_me().username}")
    print(f"📋 Группа логов: {GROUP_ID}")
    print("🎁 Новые пользователи получают 7 дней подписки!")
    print("♈ Добавлен выбор знака зодиака!")
    print("❌ Для остановки нажми Ctrl+C")
    
    threading.Thread(target=daily_notifications, daemon=True).start()
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            time.sleep(5)
