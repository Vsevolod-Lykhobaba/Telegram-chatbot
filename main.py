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
    bot.reply_to(message, "Good afternoon, let's collect information about you.")
    msg = bot.send_message(message.chat.id, "Enter your PIB. Example:\nBabay Gennady Gennadiyovich")
    bot.register_next_step_handler(msg, process_name)

def process_name(message):
    chat_id = message.chat.id
    name = message.text
    if validate_name(name):
        user_data[chat_id]['name'] = name
        msg = bot.send_message(chat_id, 'Enter your phone number. Butt:\n+380000000000')
        bot.register_next_step_handler(msg, process_phone)
    else:
        msg = bot.send_message(chat_id, 'Non-Cyrillic characters were found in your name, please re-enter.')
        bot.register_next_step_handler(msg, process_name)

def process_phone(message):
    chat_id = message.chat.id
    phone = message.text
    if validate_phone(phone):
        user_data[chat_id]['phone'] = phone
        msg = bot.send_message(chat_id, 'Enter your INN. Butt:\n333033024')
        bot.register_next_step_handler(msg, process_inn)
    else:
        msg = bot.send_message(chat_id, 'Enter the incorrect phone number again:')
        bot.register_next_step_handler(msg, process_phone)

def process_inn(message):
    chat_id = message.chat.id
    inn = message.text
    if validate_inn(inn):
        user_data[chat_id]['inn'] = inn
        msg = bot.send_message(chat_id, 'Enter your date of birth (DD.MM.YYYY). Butt:\n26.09.2006')
        bot.register_next_step_handler(msg, process_dob)
    else:
        msg = bot.send_message(chat_id, 'Enter the incorrect INN again:')
        bot.register_next_step_handler(msg, process_inn)

def process_dob(message):
    chat_id = message.chat.id
    dob = message.text
    if validate_dob(dob):
        user_data[chat_id]['dob'] = dob
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Yes", callback_data="vpo_yes"),
                   types.InlineKeyboardButton("No", callback_data="vpo_no"))
        bot.send_message(chat_id, 'Are you a VPO? (Yes/No)', reply_markup=markup)
    else:
        msg = bot.send_message(chat_id, 'The date of the people is incorrect, please enter it again (DD.MM.YYYY):')
        bot.register_next_step_handler(msg, process_dob)

@bot.callback_query_handler(func=lambda call: call.data in ["vpo_yes", "vpo_no"])
def process_vpo(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return
    
    user_data[chat_id]['vpo'] = 'Да' if call.data == 'vpo_yes' else 'Ні'
    msg = bot.send_message(chat_id, 'Indicate the location where you are located. Stock:\nLyubotin, Zalupina st., 6')
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
               types.InlineKeyboardButton("Rich family", callback_data="vulnerability_large_family"),
               types.InlineKeyboardButton("Detection of disability", callback_data="vulnerability_disability"),
               types.InlineKeyboardButton("Other", callback_data="vulnerability_other"))
    bot.send_message(chat_id, 'What category do you fall into?', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("vulnerability_"))
def process_vulnerability(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    if call.data == "vulnerability_other":
        msg = bot.send_message(chat_id, 'Please indicate your option:')
        bot.register_next_step_handler(msg, process_vulnerability_other)
    else:
        vulnerability_options = {
            "vulnerability_65_plus": "65+",
            "vulnerability_large_family": "Rich family",
            "vulnerability_disability": "Detection of disability"
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
    markup.add(types.InlineKeyboardButton("Food", callback_data="assistance_food"),
               types.InlineKeyboardButton("Hygienic dialing", callback_data="assistance_hygiene_set"),
               types.InlineKeyboardButton("Medicine", callback_data="assistance_meds"),
               types.InlineKeyboardButton("Hygiene products (Diapers, pads, diapers)", callback_data="assistance_hygiene_items"),
               types.InlineKeyboardButton("Soc. accompaniment", callback_data="assistance_social"),
               types.InlineKeyboardButton("Other", callback_data="assistance_other"))
    bot.send_message(chat_id, 'What help do you need?', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("assistance_"))
def process_assistance(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    if call.data == "assistance_other":
        msg = bot.send_message(chat_id, 'Please indicate your option:')
        bot.register_next_step_handler(msg, process_assistance_other)
    else:
        assistance_options = {
            "assistance_food": "Food",
            "assistance_hygiene_set": "Hygienic dialing",
            "assistance_meds": "Medicine",
            "assistance_hygiene_items": "Hygiene products (Diapers, pads, diapers)",
            "assistance_social": "Soc. accompaniment"
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
    bot.send_message(chat_id, 'Do you agree to the processing of personal data? (Yes/No)', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["consent_yes", "consent_no"])
def process_consent(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    user_data[chat_id]['consent'] = 'Yes' if call.data == 'consent_yes' else 'No'
    
    if call.data == 'consent_no':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Yes", callback_data="previous_assistance_yes"),
                   types.InlineKeyboardButton("No", callback_data="previous_assistance_no"))
        bot.send_message(chat_id, 'Have you received help from our fund before?', reply_markup=markup)
    else:
        ask_how_heard(chat_id)

@bot.callback_query_handler(func=lambda call: call.data in ["previous_assistance_yes", "previous_assistance_no"])
def process_previous_assistance(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    user_data[chat_id]['previous_assistance'] = 'Yes' if call.data == 'previous_assistance_yes' else 'No'
    ask_how_heard(chat_id)

def ask_how_heard(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Soc. Networks", callback_data="how_heard_social_media"),
               types.InlineKeyboardButton("Acquaintances", callback_data="how_heard_friends"),
               types.InlineKeyboardButton("Other", callback_data="how_heard_other"))
    bot.send_message(chat_id, 'How did you hear about us?', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("how_heard_"))
def process_how_heard(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        start(call.message)
        return

    how_heard_options = {
        "how_heard_social_media": "Soc. Networks",
        "how_heard_friends": "Acquaintances",
        "how_heard_other": "Other"
    }
    if call.data == "how_heard_other":
        msg = bot.send_message(chat_id, 'Please indicate your option in no more than 300 characters:')
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
        msg = bot.send_message(chat_id, 'The text is too long, please enter no more than 300 characters:')
        bot.register_next_step_handler(msg, process_how_heard_other)

def confirm_data(chat_id):
    if chat_id not in user_data:
        return

    user = user_data[chat_id]
    confirmation_message = (
        f"Peeb: {user['name']}\n"
        f"Phone number: {user['phone']}\n"
        f"TIN: {user['inn']}\n"
        f"Date of birth: {user['dob']}\n"
        f"IDPs: {user['vpo']}\n"
        f"Residential address: {user['location']}\n"
        f"Help: {user['assistance']}\n"
        f"Vulnerable category: {user.get('vulnerability', 'Не указано')}\n"
        f"Consent to data processing:{user['consent']}\n"
        f"How did you find out about us: {user['how_heard']}\n"
        "Everything correct? (Yes/No)"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Yes", callback_data="confirm_yes"),
               types.InlineKeyboardButton("No", callback_data="confirm_no"))
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
        bot.send_message(chat_id, "Your data is saved!")
    else:
        bot.send_message(chat_id, "Enter the data again:")
        bot.register_next_step_handler(call.message, process_name)

@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.send_message(message.chat.id, "Please use /start to start the dialog")

bot.polling()
