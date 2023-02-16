import os
import time
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

NASA_TOKEN = os.getenv('NASA_TOKEN')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

ENDPOINT = ''


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # todo get or create user
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Hi, no pic yet...'
    )


async def get_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Hi, no pic yet...'
    )


if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    get_pic_handler = CommandHandler('get', get_pic)

    application.add_handler()
    application.add_handler(start_handler)

    application.run_polling()
