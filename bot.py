import os
import time
import logging
import requests
from datetime import datetime, timedelta
from pytz import timezone

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler
from telegram.constants import MessageLimit

from utils import ExtDate
import database as db

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ENDPOINT = 'https://api.nasa.gov/planetary/apod?api_key={}&date={}'


NASA_TOKEN = os.getenv('NASA_TOKEN')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
NASA_API_TZ = timezone('US/Eastern')
# MessageLimit.CAPTION_LENGTH = 4096

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


def build_listing_keyboard(date: str):
    # prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    prev_date = ExtDate.strptime(date, '%Y-%m-%d').get_prev_day()
    # next_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = ExtDate.strptime(date, '%Y-%m-%d').get_next_day()

    keyboard = [
        [InlineKeyboardButton("add to favorite", callback_data='favs'), ],
        [InlineKeyboardButton("prev", callback_data=prev_date), InlineKeyboardButton("next", callback_data=next_date), ],
        [InlineKeyboardButton("return to menu", callback_data='menu'), ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_prev_keyboard(date: str):
    # prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    prev_date = ExtDate.strptime(date, '%Y-%m-%d').get_prev_day()
    keyboard = [
        [InlineKeyboardButton("add to favorite", callback_data='favs'), ],
        [InlineKeyboardButton("prev", callback_data=prev_date), ],
        [InlineKeyboardButton("return to menu", callback_data='menu'), ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.User(update.effective_user) # TODO PAUSE HERE
    if user.exists():
        print('С Возвращением. Ты уже существуешь.')
    else:
        user.commit()
    print(f'User in db: {user}')

    # date = ExtDate.now(tz=NASA_API_TZ)
    # print(f'TYPE DATE: {type(date)}')
    # date = date.yyyy_mm_dd()  # FIXME WORK ON eastern US timezone
    date = datetime.now(tz=NASA_API_TZ).strftime('%Y-%m-%d')
    print(f'DATE on start: {date}')

    keyboard = [
        [InlineKeyboardButton("🌌 Картинка дня", callback_data=date)],
        [InlineKeyboardButton("❤ Избранное", callback_data="favs")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # todo get or create user
    message = (
        f'Привет, {update.effective_user.first_name}!'
        '\nПосмотрим на звёзды сегодня?'
    )    
    # await update.message.reply_text(message, reply_markup=reply_markup)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup
    )


async def button_dispatcher(update: Update, context):
    query_data = update.callback_query.data
    print(f'dispatch: {query_data}')
    if query_data == 'favs':
        await favs(update, context)
    elif query_data == 'menu':
        await update.callback_query.delete_message()
        await start(update, context)
    else:
        await get_img(update, context)


async def get_img(update: Update, context: ContextTypes.DEFAULT_TYPE): # rename listing
    """Parses the CallbackQuery and updates the message text."""
    print('---------------------------------------')
    query = update.callback_query
    await query.answer()
    date_str = query.data
    print(f'DATE: {date_str}')
    endpoint = ENDPOINT.format(NASA_TOKEN, date_str)
    response = requests.get(endpoint).json()
    # print(f'RESPONSE: {response}')
    image_url = response.get('url')
    caption = f'Картинка от {date_str[-2:]}.{date_str[-5:-3]}\n' + response.get('explanation')
    print(f'caption len: {len(caption)}')
    if len(caption) > 1024:
        caption_ext = caption[1024:2048]
        caption = caption[:1021] + '...'

    if date_str == datetime.now(tz=NASA_API_TZ).strftime('%Y-%m-%d'):  #ExtDate.now().yyyy_mm_dd():
        reply_markup = build_prev_keyboard(date_str)
    else:
        reply_markup = build_listing_keyboard(date_str)

    chat = update.effective_chat
    print('***********************************')
    # print(f'IS IMG? {query.message.photo}')
    if not query.message.photo:
        await query.delete_message()
        await context.bot.send_photo(chat.id, image_url, caption, reply_markup=reply_markup)
        return
    print('***********************************')

    await query.edit_message_media(media=InputMediaPhoto(image_url, caption), reply_markup=reply_markup)
    # await context.bot.edit_message_media(media=image_url, chat_id=chat.id, reply_markup=reply_markup)
    # await query.edit_message_reply_markup()
    # await context.bot.send_photo(chat.id, image_url, reply_markup=reply_markup)
    # await query.edit_message_text(text=f"Selected option: {query.data}")

async def favs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("return to menu", callback_data='menu'), ],
    ]
    message = 'TODO листалка избранные фото'    
    await query.edit_message_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard))
    # await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))


if __name__ == '__main__':

    conn = psycopg2.connect(dbname='postgres', user='postgres', password='postgres_pass', host='localhost')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

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

    # cursor.execute('''
    # CREATE TABLE users
    # (USER_ID INT PRIMARY KEY NOT NULL,
    # FIRST_NAME TEXT,
    # LAST_NAME TEXT,
    # USERNAME TEXT,
    # IS_BOT BOOLEAN
    # );
    # ''')
    # conn.commit() # (ID, FIRST_NAME, LAST_NAME) VALUES (1, 'Tester', 'Testerov')

    # cursor.execute('''
    # CREATE TABLE favs
    # (
    # ID INT PRIMARY KEY NOT NULL
    # USER_ID INT NOT NULL,
    # pic_date TEXT NOT NULL
    # );
    # ''')
    # conn.commit()

    # cursor.execute('''
    #     SELECT * FROM users; 
    #     ''')
    # conn.commit()


    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_dispatcher))
    # application.add_handler(CallbackQueryHandler(favs))

    #todo message handler with logging
    application.run_polling()
