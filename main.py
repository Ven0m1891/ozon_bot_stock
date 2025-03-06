import telebot
from telebot import types
import json
from func import gsheet_output, get_product_remains, get_fbo_stock
from datetime import datetime, date, timedelta
import time
import requests

# Загрузка конфигурации
with open('config.json', 'r') as file:
    config = json.load(file)
    TOKEN = config.get('token')
    ADMIN_CHAT_ID = config.get('admin_chat_id')
    projects = config.get('projects')

bot = telebot.TeleBot(TOKEN)


def inline_main_menu():
    '''Универсальная функция для меню выбора магазина'''
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(projects['project1']['name'], callback_data='project1')
    btn2 = types.InlineKeyboardButton(projects['project2']['name'], callback_data='project2')
    btn3 = types.InlineKeyboardButton(projects['project3']['name'], callback_data='project3')
    btn4 = types.InlineKeyboardButton(projects['project4']['name'], callback_data='project4')
    markup.add(btn1, btn3)
    markup.add(btn2, btn4)
    return markup


def generate_project_menu_markup(project):
    '''Универсальная функция для создания меню'''
    markup = types.InlineKeyboardMarkup()
    btn_remains = types.InlineKeyboardButton('Получить остатки', callback_data=f'remains_{project}')
    btn_update_stock = types.InlineKeyboardButton('Обновить сток', callback_data=f'stock_{project}')
    btn_delete = types.InlineKeyboardButton('Удалить остатки', callback_data=f'delete_{project}')
    btn_back = types.InlineKeyboardButton('Назад в меню выбора магазина', callback_data='main_menu')
    markup.row(btn_remains)
    markup.row(btn_update_stock)
    markup.row(btn_delete)
    markup.row(btn_back)
    return markup

# Универсальная функция для создания меню проектов
def generate_project_menu(callback, project, project_name):
    markup = types.InlineKeyboardMarkup()
    btn_remains = types.InlineKeyboardButton('Получить остатки', callback_data=f'remains_{project}')
    btn_update_stock = types.InlineKeyboardButton('Обновить сток', callback_data=f'stock_{project}')
    btn_delete = types.InlineKeyboardButton('Удалить остатки', callback_data=f'delete_{project}')
    btn_back = types.InlineKeyboardButton('Назад в меню выбора магазина', callback_data='main_menu')
    markup.row(btn_remains)
    markup.row(btn_update_stock)
    markup.row(btn_delete)
    markup.row(btn_back)
    bot.send_message(callback.message.chat.id, f'Выбери действие для {project_name}', reply_markup=markup)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Выберите магазин:", reply_markup=inline_main_menu())

# Обработчик команды Назад
@bot.callback_query_handler(func=lambda callback: callback.data == 'main_menu')
def main_menu_handler(callback):
    bot.send_message(callback.message.chat.id, 'Вы в главном меню. Выберите магазин:', reply_markup=inline_main_menu())

# Обработчик выбора действия для Project 1
@bot.callback_query_handler(func=lambda callback: callback.data == 'project1')
def menu_project1(callback):
    generate_project_menu(callback, 'project1', projects['project1']['name'])

# Обработчик выбора действия для Project 2
@bot.callback_query_handler(func=lambda callback: callback.data == 'project2')
def menu_project2(callback):
    generate_project_menu(callback, 'project2', projects['project2']['name'])

# Обработчик выбора действия для Project 3
@bot.callback_query_handler(func=lambda callback: callback.data == 'project3')
def menu_project3(callback):
    generate_project_menu(callback, 'project3', projects['project3']['name'])

# Обработчик выбора действия для Project 4
@bot.callback_query_handler(func=lambda callback: callback.data == 'project4')
def menu_project4(callback):
    generate_project_menu(callback, 'project4', projects['project4']['name'])



def send_telegram_notification_error(message):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            'chat_id': ADMIN_CHAT_ID,
            'text': str(message)
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("Админу отправлено успешно!")
        else:
            print(f"Ошибка отправки сообщения: {response.status_code}")
    except Exception as e:
        print(f"Ошибка отправки сообщения в Telegram: {e}")



if __name__ == "__main__":
    while True:
        try:
            bot.polling(non_stop=True)
        except Exception as e:
            print(f"Error occurred: {e}")
            send_telegram_notification_error(f'Возникла ошибка связи с сервером в боте OZON STOCK {e}')
            time.sleep(15)  # Wait for 15 seconds before trying again