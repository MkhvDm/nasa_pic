import logging
import os
import re
from datetime import datetime
from http import HTTPStatus
from typing import Union, Tuple, List

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.errors import OperationalError
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pytz import timezone
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      InputMediaPhoto, Update, InlineQueryResultArticle)
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, MessageHandler, ContextTypes,
                          filters)

import database as db
from bot_logger import logger_config
from utils import ExtDate
from uuid import uuid4

load_dotenv()

bot_logger = logging.getLogger(__name__)

ENDPOINT = 'https://api.nasa.gov/planetary/apod?api_key={}&date={}'
NASA_TOKEN = os.getenv('NASA_TOKEN')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_TEST')
NASA_API_TZ = timezone('US/Eastern')
MAX_CAPTION_SIZE = 1024

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

def get_start_keyboard(date: str, fav_date: Union[str, None] = None):
    """Стартовое меню."""
    keyboard = [[InlineKeyboardButton("🌌 Картинка дня", callback_data=date)],]
    if fav_date:
        keyboard.append([InlineKeyboardButton("❤ Избранное", callback_data=fav_date)],)
    return InlineKeyboardMarkup(keyboard)

def build_fav_keyboard(prev: str, next: Union[str, None] = None):
    # TODO favorite listing
    if next:
        pass
    else:
        keyboard = [
            [InlineKeyboardButton("⬅️", callback_data=f'fav: {prev}'), ],
            [InlineKeyboardButton("return to menu", callback_data='menu'), ],
        ]
    return InlineKeyboardMarkup(keyboard)

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

def build_return_to_menu_kb():
    """Клавиатура с кнопкой возврата в главное меню."""
    keyboard = [[InlineKeyboardButton("return to menu", callback_data='menu'), ], ]
    return InlineKeyboardMarkup(keyboard)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.User(user).user_id == 214733890:
        bot_logger.info(f'Админ {user.username} в здании!')
    else:
        await context.bot.send_message(
            update.effective_chat.id, 'Нет прав!', reply_markup=build_return_to_menu_kb()
        )
        return
    users = db.User.get_all()[:10]
    resp = '\n'.join(
        [f'{user[0].first_name} {user[0].last_name} - {user[0].username}' for user in users]
    )
    await context.bot.send_message(
        update.effective_chat.id, resp  #, reply_markup=build_return_to_menu_kb()
    )
    favs = db.Favorite.get_all()
    resp_favs = '\n'.join(
        [f'{str(fav[0].id)}: {fav[0].user_id} - {fav[0].pic_date}' for fav in favs]
    )
    print(f'resp favs: {resp_favs}')
    await context.bot.send_message(
        update.effective_chat.id, resp_favs, reply_markup=build_return_to_menu_kb()
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
    print(f'type(user_fav) is {type(user_fav)}')
    bot_logger.info(f'User have fav? - {user_fav}')
    if user_fav:
        print(f'user_fav[0].pic_date: {user_fav[0].pic_date}')
        fav_date = f'fav: {user_fav[0].pic_date}'
        print(f'insert fav query: {fav_date}')
    else:
        fav_date = None

    message = (
        f'Привет, {update.effective_user.first_name}!'
        '\nПосмотрим на звёзды сегодня?'
    )    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=get_start_keyboard(date, fav_date)
    )

async def button_dispatcher(update: Update, context):
    """Перенаправление на нужный обработчик исходя из текста запроса."""
    query_data = update.callback_query.data
    bot_logger.debug('Запрос: {query_data}')
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

def get_api_response(date: str) -> Tuple[str, List[str]]:
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
    return (image_url, captions)


async def get_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение картинок и возвращение клавиатуры-листалки."""
    query = update.callback_query
    await query.answer()
    date_str = query.data
    bot_logger.info(f'Получение фото от {date_str}')
    image_url, captions = get_api_response(date_str)

    if date_str == datetime.now(tz=NASA_API_TZ).strftime('%Y-%m-%d'):
        reply_markup = build_prev_keyboard(date_str)
    else:
        reply_markup = build_listing_keyboard(date_str)

    chat = update.effective_chat
    if not query.message.photo:
        await query.delete_message()
        await context.bot.send_photo(chat.id, image_url, captions[0], reply_markup=reply_markup)
        return

    await query.edit_message_media(media=InputMediaPhoto(image_url, captions[0]), reply_markup=reply_markup)

async def favs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возвращает дату последнего избранного фото. FIXME"""
    query = update.callback_query
    query_fav_date = query.data
    await query.answer()
    bot_logger.info(f'Query-запрос: {query_fav_date}')
    parsed_date = re.match('fav: (\d\d\d\d-\d\d-\d\d)', query_fav_date).group(1)
    bot_logger.info(f'Match: {parsed_date}')
    image_url, captions = get_api_response(parsed_date)
    ####
    if parsed_date == db.User(update.effective_user).get_last_fav()[0].pic_date:
        # prev only 
        # keyboard_gen
        pass 
    else:
        # gen prev + next
        # keyboard_gen
        pass
    all_favs = db.User(update.effective_user).get_all_favs()
    # print(f'{all_favs[0][0]}')  # out of range
    # print(f'{all_favs[1][0]}')  # out of range
    # print(f'types: {type(all_favs[0][0])}, {type(all_favs[1][0])}')
    # print(f'{all_favs[0][0] > all_favs[1][0]}')

    for i, fav in enumerate(all_favs):
        print(f'FAV[{i}]: {fav} - id = {fav[0].id}')

    # next_date = parsed_date
    # prev_date = ...
    reply_markup = build_fav_keyboard(parsed_date)
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
    
    # await query.edit_message_text(text=message, reply_markup=reply_markup)

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

        # cursor.execute(
        #     '''
        #     DROP TABLE favs;
        #     '''
        # )
        # conn.commit()
        # cursor.execute(
        #     '''
        #     DROP TABLE users;
        #     '''
        # )
        # conn.commit()
        # cursor.execute(
        #     '''
        #     DROP TABLE alembic_version;
        #     '''
        # )
        # conn.commit()

    except OperationalError as err:
        bot_logger.error(f'Connect to DB error! {err}')

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('admin', admin))
    application.add_handler(CallbackQueryHandler(button_dispatcher))
    application.add_handler(MessageHandler(filters=filters.TEXT, callback=user_messages))
    application.run_polling()
