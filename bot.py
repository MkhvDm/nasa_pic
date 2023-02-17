import os
import time
import logging
import requests
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler

from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

NASA_TOKEN = os.getenv('NASA_TOKEN')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

date = '2023-02-14'
DATE = datetime.now()

ENDPOINT = 'https://api.nasa.gov/planetary/apod?api_key={}&date={}'

def build_listing_keyboard(date: str):
    prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    keyboard = [
        [InlineKeyboardButton("prev", callback_data=prev_date), InlineKeyboardButton("next", callback_data=next_date), ],
        [InlineKeyboardButton("add to favorite", callback_data='favs'), ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_prev_keyboard(date: str):
    prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    keyboard = [
        [InlineKeyboardButton("prev", callback_data=prev_date), ],
        [InlineKeyboardButton("add to favorite", callback_data='favs'), ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = DATE.strftime('%Y-%m-%d')
    keyboard = [
        [InlineKeyboardButton("🌌 Картинка дня", callback_data=date)],
        [InlineKeyboardButton("❤ Избранное", callback_data="2")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # todo get or create user
    message = (
        f'Привет, {update.effective_user.first_name}!'
        '\nПосмотрим на звёзды сегодня?'
    )
    # print(update.effective_chat.first_name)  # alter.
    
    await update.message.reply_text(message, reply_markup=reply_markup)
    # await context.bot.send_message(
    #     chat_id=update.effective_chat.id,
    #     text='Hi, no pic yet...'
    # )


async def button_gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    print(f'QUERY: {query}')
    date = query.data
    print(f'date_1: {date}')
    print(f"date_2{datetime.now().strftime('%Y-%m-%d')}")

    if date == datetime.now().strftime('%Y-%m-%d'):
        reply_markup = build_prev_keyboard(date)
    else:
        reply_markup = build_listing_keyboard(date)
        pass
    prev_or_next = query.data
    # date = (DATE - timedelta(days=1)).strftime('%Y-%m-%d') if prev_or_next == 'prev' else ((DATE + timedelta(days=1)).strftime('%Y-%m-%d'))

    endpoint = ENDPOINT.format(NASA_TOKEN, date)
    print(endpoint)
    response = requests.get(endpoint).json()
    # print(response)
    image_url = response.get('url')
    chat = update.effective_chat
    await query.answer()
    await context.bot.send_photo(chat.id, image_url, reply_markup=reply_markup)
    # await query.edit_message_text(text=f"Selected option: {query.data}")


# async def get_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     response = requests.get(ENDPOINT.format(NASA_TOKEN, date)).json()
#     print(response)
#     await context.bot.send_message(
#         chat_id=update.effective_chat.id,
#         text='Hi, no pic yet...'
#     )


if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    # application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CallbackQueryHandler(button_gold))


    # get_pic_handler = CommandHandler('get', get_pic)

    #todo message handler with logging

    # application.add_handler(get_pic_handler)
    application.add_handler(start_handler)

    application.run_polling()
