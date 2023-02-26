from typing import Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils import ExtDate


def get_start_keyboard(date: str, fav_date: Union[str, None] = None):
    """Стартовое меню."""
    keyboard = [[InlineKeyboardButton("🌌 Картинка дня", callback_data=date)],]
    if fav_date:
        keyboard.append([InlineKeyboardButton("❤ Избранное", callback_data=fav_date)],)
    return InlineKeyboardMarkup(keyboard)

def build_fav_keyboard(prev: Union[str, None] = None, next: Union[str, None] = None):
    """Создание клавиатуры-листалки для Избранного."""
    keyboard = [[], [InlineKeyboardButton("return to menu", callback_data='menu'),],]
    if prev:
        keyboard[0].append(InlineKeyboardButton("⬅️", callback_data=f'fav: {prev}'))
    if next:
        keyboard[0].append(InlineKeyboardButton("➡️", callback_data=f'fav: {next}'))
    return InlineKeyboardMarkup(keyboard)

def build_listing_keyboard(date: str, is_prev: bool = False, is_next: bool = False):
    """Создание клавиатуры-листалки фото."""
    keyboard = [
        [InlineKeyboardButton("add to favorite", callback_data=f'favs_add: {date}'), ],
        [],
        [InlineKeyboardButton("return to menu", callback_data='menu'), ],
    ]
    if is_prev:
        prev_date = ExtDate.strptime(date, '%Y-%m-%d').get_prev_day()
        keyboard[1].append(InlineKeyboardButton("⬅️", callback_data=prev_date))
    if is_next:
        next_date = ExtDate.strptime(date, '%Y-%m-%d').get_next_day()
        keyboard[1].append(InlineKeyboardButton("➡️", callback_data=next_date))
    return InlineKeyboardMarkup(keyboard)

def build_return_to_menu_kb():
    """Клавиатура с кнопкой возврата в главное меню."""
    keyboard = [[InlineKeyboardButton("return to menu", callback_data='menu'), ], ]
    return InlineKeyboardMarkup(keyboard)
    