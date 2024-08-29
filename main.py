import re
import sqlite3
import telebot
from telebot import types
import os
from dotenv import load_dotenv, find_dotenv

# Загрузка токена из файла .env
load_dotenv(find_dotenv())
bot = telebot.TeleBot(os.getenv('TOKEN'))

# Подключение к базе данных SQLite
conn = sqlite3.connect('userdata.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (name TEXT, phone TEXT, inn TEXT, dob TEXT, vpo TEXT, location TEXT, assistance TEXT, vulnerability TEXT, consent TEXT, how_heard TEXT)''')
conn.commit()

def validate_name(name: str) -> bool:
    return bool(re.match(r'^[\u0400-\u04FF\s]+$', name))

def validate_phone(phone: str) -> bool:
    return bool(re.match(r'^\+380\d{9}$', phone))

def validate_inn(inn: str) -> bool:
    return bool(re.match(r'^\d{9}+$', inn))

def validate_dob(dob: str) -> bool:
    return bool(re.match(r'^\d{2}\.\d{2}\.\d{4}$', dob))

user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_data[message.chat.id] = {}
    bot.reply_to(message, 'Доброго дня, давайте зберемо дані про вас.')
    msg = bot.send_message(message.chat.id, "Введіть ваш ПІБ. Приклад:\nБабай Генадій Генадійович")
    bot.register_next_step_handler(msg, process_name)

def process_name(message):
    chat_id = message.chat.id
    name = message.text
    if validate_name(name):
        user_data[chat_id]['name'] = name
        msg = bot.send_message(chat_id, 'Введіть ваш номер телефону. Приклад:\n+380000000000')
        bot.register_next_step_handler(msg, process_phone)
    else:
        msg = bot.send_message(chat_id, 'В вашому імені знайдено не кириличні символи введіть заново.')
        bot.register_next_step_handler(msg, process_name)

def process_phone(message):
    chat_id = message.chat.id
    phone = message.text
    if validate_phone(phone):
        user_data[chat_id]['phone'] = phone
        msg = bot.send_message(chat_id, 'Введіть ваш ІНН. Приклад:\n333033024')
        bot.register_next_step_handler(msg, process_inn)
    else:
        msg = bot.send_message(chat_id, 'Некоректний номер телефону введіть ще раз:')
        bot.register_next_step_handler(msg, process_phone)

def process_inn(message):
    chat_id = message.chat.id
    inn = message.text
    if validate_inn(inn):
        user_data[chat_id]['inn'] = inn
        msg = bot.send_message(chat_id, 'Введіть вашу дату народження (ДД.ММ.ГГГГ). Приклад:\n26.09.2006')
        bot.register_next_step_handler(msg, process_dob)
    else:
        msg = bot.send_message(chat_id, 'Некоректний ІНН введіть ще раз:')
        bot.register_next_step_handler(msg, process_inn)

def process_dob(message):
    chat_id = message.chat.id
    dob = message.text
    if validate_dob(dob):
        user_data[chat_id]['dob'] = dob
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Так", callback_data="vpo_yes"),
                   types.InlineKeyboardButton("Ні", callback_data="vpo_no"))
        bot.send_message(chat_id, 'Ви ВПО? (Так/Ні)', reply_markup=markup)
    else:
        msg = bot.send_message(chat_id, 'Некоректна дата народження введіть ще раз (ДД.ММ.ГГГГ):')
        bot.register_next_step_handler(msg, process_dob)

@bot.callback_query_handler(func=lambda call: call.data in ["vpo_yes", "vpo_no"])
def process_vpo(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return
    
    user_data[chat_id]['vpo'] = 'Да' if call.data == 'vpo_yes' else 'Ні'
    msg = bot.send_message(chat_id, 'Вкажіть локацію в якій знаходитесь. Приклад:\nЛюботин, вул.Залупіна, 6')
    if call.data == 'vpo_no':
        bot.register_next_step_handler(msg, process_location_and_vulnerability)
    else:
        bot.register_next_step_handler(msg, process_location)

def process_location_and_vulnerability(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        start(message)
        return

    user_data[chat_id]['location'] = message.text
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("65+", callback_data="vulnerability_65_plus"),
               types.InlineKeyboardButton("Багатодітна сім'я", callback_data="vulnerability_large_family"),
               types.InlineKeyboardButton("Наявність інвалідності", callback_data="vulnerability_disability"),
               types.InlineKeyboardButton("Інше", callback_data="vulnerability_other"))
    bot.send_message(chat_id, 'До якої вразливої категорії ви відноситесь?', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("vulnerability_"))
def process_vulnerability(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    if call.data == "vulnerability_other":
        msg = bot.send_message(chat_id, 'Будь ласка вкажіть ваш варіант:')
        bot.register_next_step_handler(msg, process_vulnerability_other)
    else:
        vulnerability_options = {
            "vulnerability_65_plus": "65+",
            "vulnerability_large_family": "Багатодітна сім'я",
            "vulnerability_disability": "Наявність інвалідності"
        }
        user_data[chat_id]['vulnerability'] = vulnerability_options[call.data]
        ask_assistance(chat_id)

def process_vulnerability_other(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        start(message)
        return

    vulnerability_other = message.text
    user_data[chat_id]['vulnerability'] = vulnerability_other
    ask_assistance(chat_id)

def process_location(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        start(message)
        return

    user_data[chat_id]['location'] = message.text
    ask_assistance(chat_id)

def ask_assistance(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Харчування", callback_data="assistance_food"),
               types.InlineKeyboardButton("Гігієнічний набір", callback_data="assistance_hygiene_set"),
               types.InlineKeyboardButton("Ліки", callback_data="assistance_meds"),
               types.InlineKeyboardButton("Засоби гігієни(Памперси, прокладки, пелюшки)", callback_data="assistance_hygiene_items"),
               types.InlineKeyboardButton("Соц. супровід", callback_data="assistance_social"),
               types.InlineKeyboardButton("Інше", callback_data="assistance_other"))
    bot.send_message(chat_id, 'Яку домопогу ви потребуєте?', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("assistance_"))
def process_assistance(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    if call.data == "assistance_other":
        msg = bot.send_message(chat_id, 'Будь ласка вкажіть ваш варіант:')
        bot.register_next_step_handler(msg, process_assistance_other)
    else:
        assistance_options = {
            "assistance_food": "Харчування",
            "assistance_hygiene_set": "Гігієнічний набір",
            "assistance_meds": "Ліки",
            "assistance_hygiene_items": "Засоби гігієни(Памперси, прокладки, пелюшки)",
            "assistance_social": "Соц. Супровід"
        }
        user_data[chat_id]['assistance'] = assistance_options[call.data]
        ask_consent(chat_id)

def process_assistance_other(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        start(message)
        return

    assistance_other = message.text
    user_data[chat_id]['assistance'] = assistance_other
    ask_consent(chat_id)

def ask_consent(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Так", callback_data="consent_yes"),
               types.InlineKeyboardButton("Ні", callback_data="consent_no"))
    bot.send_message(chat_id, 'Чи згодні ви на обробку персональних даних? (Так/Ні)', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["consent_yes", "consent_no"])
def process_consent(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    user_data[chat_id]['consent'] = 'Так' if call.data == 'consent_yes' else 'Ні'
    
    if call.data == 'consent_no':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Так", callback_data="previous_assistance_yes"),
                   types.InlineKeyboardButton("Ні", callback_data="previous_assistance_no"))
        bot.send_message(chat_id, 'Чи отримували ви раніше допомогу від нашого фонду?', reply_markup=markup)
    else:
        ask_how_heard(chat_id)

@bot.callback_query_handler(func=lambda call: call.data in ["previous_assistance_yes", "previous_assistance_no"])
def process_previous_assistance(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    user_data[chat_id]['previous_assistance'] = 'Так' if call.data == 'previous_assistance_yes' else 'Ні'
    ask_how_heard(chat_id)

def ask_how_heard(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Соц. Мережі", callback_data="how_heard_social_media"),
               types.InlineKeyboardButton("Знайомі", callback_data="how_heard_friends"),
               types.InlineKeyboardButton("Інше", callback_data="how_heard_other"))
    bot.send_message(chat_id, 'Звідки ви дізнались про нас?', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("how_heard_"))
def process_how_heard(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    how_heard_options = {
        "how_heard_social_media": "Соц. Мережі",
        "how_heard_friends": "Знайомі",
        "how_heard_other": "Інше"
    }
    if call.data == "how_heard_other":
        msg = bot.send_message(chat_id, 'Будь ласка вкажіть ваш варіант не більше 300 символів:')
        bot.register_next_step_handler(msg, process_how_heard_other)
    else:
        user_data[chat_id]['how_heard'] = how_heard_options[call.data]
        confirm_data(chat_id)

def process_how_heard_other(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        start(message)
        return

    how_heard_other = message.text
    if len(how_heard_other) <= 300:
        user_data[chat_id]['how_heard'] = how_heard_other
        confirm_data(chat_id)
    else:
        msg = bot.send_message(chat_id, 'Занадто великий текст введіть будь ласка не більше 300 символів:')
        bot.register_next_step_handler(msg, process_how_heard_other)

def confirm_data(chat_id):
    if chat_id not in user_data:
        return

    user = user_data[chat_id]
    confirmation_message = (
        f"Піб: {user['name']}\n"
        f"Номер телефону: {user['phone']}\n"
        f"ІНН: {user['inn']}\n"
        f"Дата народження: {user['dob']}\n"
        f"ВПО: {user['vpo']}\n"
        f"Адреса проживання: {user['location']}\n"
        f"Допомога: {user['assistance']}\n"
        f"Вразлива категорія: {user.get('vulnerability', 'Не указано')}\n"
        f"Згода на обробку данних: {user['consent']}\n"
        f"Звідки ви дізнались про нас: {user['how_heard']}\n"
        "Все вірно? (Так/Ні)"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Так", callback_data="confirm_yes"),
               types.InlineKeyboardButton("Ні", callback_data="confirm_no"))
    bot.send_message(chat_id, confirmation_message, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_yes", "confirm_no"])
def process_confirmation(call):
    chat_id = call.message.chat.id
    if call.data == 'confirm_yes':
        if chat_id not in user_data:
            start(call.message)
            return

        user = user_data[chat_id]
        c.execute("INSERT INTO users (name, phone, inn, dob, vpo, location, assistance, vulnerability, consent, how_heard) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (user['name'], user['phone'], user['inn'], user['dob'], user['vpo'], user['location'], user['assistance'], user.get('vulnerability', ''), user['consent'], user['how_heard']))
        conn.commit()
        bot.send_message(chat_id, "Ваші дані збережено!")
    else:
        bot.send_message(chat_id, "Введіть дані заново:")
        bot.register_next_step_handler(call.message, process_name)

@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.send_message(message.chat.id, "Будь ласка використовуйте /start для початку діалогу")

bot.polling()
