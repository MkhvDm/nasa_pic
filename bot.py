import os
import time
import logging
import requests
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler

from utils import ExtDate

from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

NASA_TOKEN = os.getenv('NASA_TOKEN')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

ENDPOINT = 'https://api.nasa.gov/planetary/apod?api_key={}&date={}'

def build_listing_keyboard(date: str):
    # prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    prev_date = ExtDate.strptime(date, '%Y-%m-%d').get_prev_day()
    # next_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = ExtDate.strptime(date, '%Y-%m-%d').get_next_day()

    keyboard = [
        [InlineKeyboardButton("add to favorite", callback_data='favs'), ],
        [InlineKeyboardButton("prev", callback_data=prev_date), InlineKeyboardButton("next", callback_data=next_date), ],
        [InlineKeyboardButton("return to menu", callback_data='start'), ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_prev_keyboard(date: str):
    # prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    prev_date = ExtDate.strptime(date, '%Y-%m-%d').get_prev_day()
    keyboard = [
        [InlineKeyboardButton("add to favorite", callback_data='favs'), ],
        [InlineKeyboardButton("prev", callback_data=prev_date), ],
        [InlineKeyboardButton("return to menu", callback_data='start'), ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = ExtDate.now().get_str_yyyy_mm_dd()

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
    # print(update.effective_chat.first_name)  # alter.
    
    await update.message.reply_text(message, reply_markup=reply_markup)
    # await context.bot.send_message(
    #     chat_id=update.effective_chat.id,
    #     text='Hi, no pic yet...'
    # )


async def button_gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    # print(f'QUERY: {query}')
    date_str = query.data

    if date_str == ExtDate.now().get_str_yyyy_mm_dd():
        reply_markup = build_prev_keyboard(date_str)
    else:
        reply_markup = build_listing_keyboard(date_str)

    endpoint = ENDPOINT.format(NASA_TOKEN, date_str)
    response = requests.get(endpoint).json()
    # print(response)
    image_url = response.get('url')
    caption = f'Картинка от ...' # TODO
    explanation = response.get('explanation')

    chat = update.effective_chat
    await query.answer()
    await context.bot.send_photo(chat.id, image_url, caption=explanation, reply_markup=reply_markup)
    # await context.bot.edit_message_caption(chat.id, inline_message_id='test_message')
    # await context.bot.edit_message_media()
    # await query.edit_message_reply_markup()

    # await context.bot.send_photo(chat.id, image_url, reply_markup=reply_markup)
    # await query.edit_message_text(text=f"Selected option: {query.data}")

async def favs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("return to menu", callback_data='start'), ],
    ]
    message = 'TODO листалка избранные фото'    
    await query.edit_message_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard))
    # await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

# async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#     keyboard = [
#         [InlineKeyboardButton("return to menu", callback_data='start'), ],
#     ]
#     await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
#     # await query.edit_message_text(text='MENU', reply_markup=InlineKeyboardMarkup(keyboard))
#     # await update.message.reply_text('--menu--', reply_markup=InlineKeyboardMarkup(keyboard))


if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_gold))
    application.add_handler(CallbackQueryHandler(favs))

    #todo message handler with logging
    application.run_polling()
