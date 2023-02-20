import logging
import os
import re
from datetime import datetime
from http import HTTPStatus

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.errors import OperationalError
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pytz import timezone
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      InputMediaPhoto, Update)
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, MessageHandler, ContextTypes,
                          filters)

import database as db
from bot_logger import logger_config
from utils import ExtDate

load_dotenv()

bot_logger = logging.getLogger(__name__)

ENDPOINT = 'https://api.nasa.gov/planetary/apod?api_key={}&date={}'
NASA_TOKEN = os.getenv('NASA_TOKEN')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
NASA_API_TZ = timezone('US/Eastern')

DB_DIALECT  = os.getenv('DB_DIALECT')
DB_HOSTNAME = os.getenv('DB_HOSTNAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DATABASE = os.getenv('DB_DATABASE')
DB_URL = "%s://%s:%s@%s/%s" % (
    DB_DIALECT,
    DB_USERNAME,
    DB_PASSWORD,
    DB_HOSTNAME,
    DB_DATABASE
)

def get_start_keyboard(date: str):
    """Стартовое меню."""
    keyboard = [
        [InlineKeyboardButton("🌌 Картинка дня", callback_data=date)],
        [InlineKeyboardButton("❤ Избранное", callback_data="favs")],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_fav_keyboard(prev: str, next: str):
    # TODO favorite listing
    pass

def build_listing_keyboard(date: str):
    """Создание клавиатуры-листалки фото."""
    prev_date = ExtDate.strptime(date, '%Y-%m-%d').get_prev_day()
    next_date = ExtDate.strptime(date, '%Y-%m-%d').get_next_day()

    keyboard = [
        [InlineKeyboardButton("add to favorite", callback_data=f'favs_add: {date}'), ],
        [InlineKeyboardButton("⬅️", callback_data=prev_date), InlineKeyboardButton("➡️", callback_data=next_date), ],
        [InlineKeyboardButton("return to menu", callback_data='menu'), ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_prev_keyboard(date: str):
    """Создание клавиатуры-листалки (без кнопки 'Далее')."""
    prev_date = ExtDate.strptime(date, '%Y-%m-%d').get_prev_day()
    keyboard = [
        [InlineKeyboardButton("add to favorite", callback_data=f'favs_add: {date}'), ],
        [InlineKeyboardButton("⬅️", callback_data=prev_date), ],
        [InlineKeyboardButton("return to menu", callback_data='menu'), ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало чата, регистрация новых пользователей."""
    user = db.User(update.effective_user)
    if user.exists():
        bot_logger.info(f'Вошёл существующий пользователь (id = {user.user_id})')
    else:
        user.commit()
        bot_logger.info(f'Новый пользователь (id = {user.user_id})')

    date = datetime.now(tz=NASA_API_TZ).strftime('%Y-%m-%d')
    message = (
        f'Привет, {update.effective_user.first_name}!'
        '\nПосмотрим на звёзды сегодня?'
    )    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=get_start_keyboard(date)
    )

async def button_dispatcher(update: Update, context):
    """Перенаправление на нужный обработчик исходя из текста запроса."""
    query_data = update.callback_query.data
    bot_logger.debug('Запрос: {query_data}')
    if query_data == 'favs':
        await favs(update, context)
    if query_data.startswith('favs_add'):
        await favs_add(update, context)
    elif query_data == 'menu':
        await update.callback_query.delete_message()
        await start(update, context)
    else:  # date in query 
        await get_img(update, context)

async def get_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение картинок и возвращение клавиатуры-листалки."""
    query = update.callback_query
    await query.answer()
    date_str = query.data
    bot_logger.info(f'Получение фото от {date_str}')
    endpoint = ENDPOINT.format(NASA_TOKEN, date_str)
    response = requests.get(endpoint)
    if response.status_code != HTTPStatus.OK:
        bot_logger.error('Не удалось получить данные с APOD API!')
        image_url = 'http://lamcdn.net/lookatme.ru/post_image-image/sIaRmaFSMfrw8QJIBAa8mA-small.png'
        caption = 'Что-то пошло не так :( Уже чиним...'
    else:
        response = response.json()
        image_url = response.get('url')
        caption = f'Картинка от {date_str[-2:]}.{date_str[-5:-3]}\n' + response.get('explanation') 
        if len(caption) > 1024:
            caption_ext = caption[1024:2048]  # TODO with additional message or extend caption capacity
            caption = caption[:1021] + '...'

    if date_str == datetime.now(tz=NASA_API_TZ).strftime('%Y-%m-%d'):
        reply_markup = build_prev_keyboard(date_str)
    else:
        reply_markup = build_listing_keyboard(date_str)

    chat = update.effective_chat
    if not query.message.photo:
        await query.delete_message()
        await context.bot.send_photo(chat.id, image_url, caption, reply_markup=reply_markup)
        return

    await query.edit_message_media(media=InputMediaPhoto(image_url, caption), reply_markup=reply_markup)

async def favs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возвращает дату последнего избранного фото."""
    query = update.callback_query
    await query.answer()
    user = db.User(update.effective_user)
    last_fav = user.get_fav()[0]
    pic_date = last_fav.pic_date
    
    keyboard = [
        [InlineKeyboardButton("⬅️", callback_data=f'fav: {pic_date}'), ],
        [InlineKeyboardButton("return to menu", callback_data='menu'), ],
    ]

    message = pic_date
    await query.edit_message_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard))

async def favs_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление в БД данных о избранных фото пользователей."""
    query = update.callback_query
    parsed_date = re.match('^.*(\d\d\d\d-\d\d-\d\d)$', query.data).group(1)
    fav = db.Favorite(update.effective_user.id, parsed_date)
    if fav.exists():
        await context.bot.answer_callback_query(callback_query_id=query.id, text='Уже в избранном!', show_alert=True)
        bot_logger.info('Пользователь пытался добавить фото, которое уже в избранном.')
    else:
        fav.commit()
        await context.bot.answer_callback_query(callback_query_id=query.id, text='Добавлено!', show_alert=True)
        bot_logger.info(
            f'Пользователь ({update.effective_user.id}) добавил фото от {parsed_date} в избранное.'
        )
    await query.answer()

def user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_logger.info(f'Сообщение от пользователя ({update.effective_user.id}): {update.effective_message.text}')

if __name__ == '__main__':
    logger_config(bot_logger)
    bot_logger.debug('Preparing bot...')
    try:
        conn = psycopg2.connect(
            dbname=DB_DATABASE, 
            user=DB_USERNAME, 
            password=DB_PASSWORD, 
            host=DB_HOSTNAME)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        bot_logger.info('Succees connect to DB!')
    except OperationalError as err:
        bot_logger.error(f'Connect to DB error! {err}')

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_dispatcher))
    application.add_handler(MessageHandler(filters=filters.TEXT, callback=user_messages))
    application.run_polling()
