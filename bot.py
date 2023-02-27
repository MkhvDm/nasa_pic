import logging
import os
import re
from datetime import datetime
from http import HTTPStatus
from typing import List, Tuple

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.errors import OperationalError
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pytz import timezone
from telegram import InputMediaPhoto, Update
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ContextTypes, MessageHandler,
                          filters)

import database as db
import keyboards as kb
from bot_logger import logger_config
from utils import binary_search

load_dotenv()

bot_logger = logging.getLogger(__name__)

ENDPOINT = 'https://api.nasa.gov/planetary/apod?api_key={}&date={}'
NASA_TOKEN = os.getenv('NASA_TOKEN')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_PROD')
NASA_API_TZ = timezone('US/Eastern')
MAX_CAPTION_SIZE = 1024
APOD_FIRST_DATE = '1995-06-16'

DB_DIALECT  = os.getenv('DB_DIALECT')
DB_HOSTNAME = os.getenv('DB_HOSTNAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DATABASE = os.getenv('DB_DATABASE')
DB_PORT = os.getenv('DB_PORT')
DB_URL = "%s://%s:%s@%s/%s" % (
    DB_DIALECT,
    DB_USERNAME,
    DB_PASSWORD,
    DB_HOSTNAME,
    DB_DATABASE
)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.User(user).user_id == 214733890:
        bot_logger.info(f'Админ {user.username} в здании!')
    else:
        await context.bot.send_message(
            update.effective_chat.id, 'Нет прав!', reply_markup=kb.build_return_to_menu_kb()
        )
        return
    users = db.User.get_all(limit=10)
    favs = db.Favorite.get_all(limit=10)
    resp = '\n'.join(
        [f'{user[0].first_name} {user[0].last_name} - {user[0].username}' for user in users]
    )
    resp_favs = '\n'.join(
        [f'{str(fav[0].id)}: {fav[0].user_id} - {fav[0].pic_date}' for fav in favs]
    )
    await context.bot.send_message(
        update.effective_chat.id, resp
    )
    await context.bot.send_message(
        update.effective_chat.id, resp_favs, reply_markup=kb.build_return_to_menu_kb()
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало чата, регистрация новых пользователей."""
    user = db.User(update.effective_user)
    if user.exists():
        bot_logger.info(f'Вошёл существующий пользователь (id = {user.user_id})')
    else:
        user.commit()
        bot_logger.info(f'Новый пользователь (id = {user.user_id})')

    date = datetime.now(tz=NASA_API_TZ).strftime('%Y-%m-%d')
    user_fav = user.get_last_fav()
    if user_fav:
        bot_logger.debug(f'У пользователя есть Избранное.')
        fav_date = f'fav: {user_fav[0].pic_date}'
    else:
        fav_date = None

    message = (
        f'Привет, {update.effective_user.first_name}!'
        '\nПосмотрим на звёзды сегодня?'
    )    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=kb.get_start_keyboard(date, fav_date)
    )

async def button_dispatcher(update: Update, context):
    """Перенаправление на нужный обработчик исходя из текста запроса."""
    query_data = update.callback_query.data
    bot_logger.debug(f'Запрос: {query_data}')
    if query_data.startswith('fav: '):
        await favs(update, context)
    if query_data.startswith('favs_add'):
        await favs_add(update, context)
    elif query_data == 'menu':
        await update.callback_query.delete_message()
        await start(update, context)
    elif re.match('^(\d\d\d\d-\d\d-\d\d)$', query_data): # parse date exist
        await get_img(update, context)
    else:
        bot_logger.debug('Необознанный запрос!')
        return

def get_api_response(date: str) -> Tuple[str, List[str]]:
    """Получение ответа от APOD API."""
    endpoint = ENDPOINT.format(NASA_TOKEN, date)
    response = requests.get(endpoint)
    if response.status_code != HTTPStatus.OK:
        bot_logger.error('Не удалось получить данные с APOD API!')
        image_url = 'http://lamcdn.net/lookatme.ru/post_image-image/sIaRmaFSMfrw8QJIBAa8mA-small.png'
        captions = ['Что-то пошло не так :( Уже чиним...']
    else:
        response = response.json()
        image_url = response.get('url')
        caption = f'Картинка от {date[-2:]}.{date[-5:-3]}\n' + response.get('explanation')
        captions = [caption[i:i+MAX_CAPTION_SIZE] for i in range(0, len(caption), MAX_CAPTION_SIZE)]
        bot_logger.info('Успешно получен ответ от APOD API!')
    return (image_url, captions)


async def get_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение картинок и возвращение клавиатуры-листалки."""
    query = update.callback_query
    await query.answer()
    date_str = query.data
    bot_logger.info(f'Получение фото от {date_str}...')
    # API requests may be upgraded with aiohttp: 
    image_url, captions = get_api_response(date_str)
    is_next, is_prev = False, False

    if not date_str == datetime.now(tz=NASA_API_TZ).strftime('%Y-%m-%d'):
        is_next = True
    if not date_str == datetime.strptime(APOD_FIRST_DATE, '%Y-%m-%d'):
        is_prev = True

    reply_markup = kb.build_listing_keyboard(date_str, is_prev, is_next)

    chat = update.effective_chat
    if not query.message.photo:
        await query.delete_message()
        await context.bot.send_photo(chat.id, image_url, captions[0], reply_markup=reply_markup)
        return
    await query.edit_message_media(media=InputMediaPhoto(image_url, captions[0]), reply_markup=reply_markup)

async def favs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение избранных фото."""
    user = db.User(update.effective_user)
    query = update.callback_query
    query_fav_date = query.data
    await query.answer()
    bot_logger.info(
        f'Запрос избранного от даты {query_fav_date} (+1/-1). User: {user}.'
        )
    parsed_date = re.match('fav: (\d\d\d\d-\d\d-\d\d)', query_fav_date).group(1)
    # API requests may be upgraded with aiohttp: 
    image_url, captions = get_api_response(parsed_date)
    # Generate query with favs pic_date for keyboard:
    parsed_date = datetime.strptime(parsed_date, '%Y-%m-%d').date()
    favs = user.get_all_favs()
    favs_num = len(favs)
    fav_index = binary_search(
        favs,
        user.get_fav_by_pic_date(parsed_date),
        lambda x: x[0].added_date
    )
    next, prev = None, None
    if fav_index == 0:
        if fav_index + 1 < favs_num:
            prev = favs[fav_index + 1]
    elif fav_index == favs_num - 1:
        next = favs[fav_index - 1]
    else:
        if fav_index + 1 < favs_num:
            prev = favs[fav_index + 1]
        next = favs[fav_index - 1]
    prev_date = datetime.strftime(prev[0].pic_date, '%Y-%m-%d') if prev else None
    next_date = datetime.strftime(next[0].pic_date, '%Y-%m-%d') if next else None
    reply_markup = kb.build_fav_keyboard(prev_date, next_date)

    if not query.message.photo:
        await query.delete_message()
        await context.bot.send_photo(
            update.effective_chat.id, 
            image_url, 
            captions[0], 
            reply_markup=reply_markup
        )
        return
    await query.edit_message_media(
        media=InputMediaPhoto(image_url, captions[0]), reply_markup=reply_markup
    )
    bot_logger.info(f'Запрос избранного обработан! User: {user}.')

async def favs_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление в БД данных о избранных фото пользователей."""
    query = update.callback_query
    parsed_date = re.match('^.*(\d\d\d\d-\d\d-\d\d)$', query.data).group(1)
    fav = db.Favorite(
        update.effective_user.id, 
        datetime.strptime(parsed_date, '%Y-%m-%d').date()
    )
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

async def user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_logger.info(f'Сообщение от пользователя ({update.effective_user.id}): {update.effective_message.text}')
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Хорошо, я передам..."
    )

if __name__ == '__main__':
    logger_config(bot_logger)
    bot_logger.debug('Preparing bot...')
    try:
        conn = psycopg2.connect(
            dbname=DB_DATABASE, 
            user=DB_USERNAME, 
            password=DB_PASSWORD, 
            host=DB_HOSTNAME,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        bot_logger.info('Succees connect to DB!')
    except OperationalError as err:
        bot_logger.error(f'Connect to DB error! {err}')

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('admin', admin))
    application.add_handler(CallbackQueryHandler(button_dispatcher))
    application.add_handler(MessageHandler(filters=filters.TEXT, callback=user_messages))
    application.run_polling()
