import os
import time
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Dice
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler

from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

NASA_TOKEN = os.getenv('NASA_TOKEN')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

ENDPOINT = ''


def get_start_menu():
    keyboard = [
        [
            InlineKeyboardButton("Start button", callback_data="1"),
            InlineKeyboardButton("Help", callback_data="2"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌌Картинка дня", callback_data="1")],
        [InlineKeyboardButton("❤️Избранное", callback_data="2")],
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


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f"Selected option: {query.data}")


async def get_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Hi, no pic yet...'
    )


if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(CallbackQueryHandler(button))

    get_pic_handler = CommandHandler('get', get_pic)

    #todo message handler with logging

    application.add_handler(get_pic_handler)
    application.add_handler(start_handler)

    application.run_polling()
