"""
Keyboard layouts used across the bot's handlers.
نسخه نهایی: ساختار Audios > Book Type > Units > Tracks
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

LEVEL_UNITS = {
    "starter": 12,
    "level_1": 12,
    "level_2": 12,
    "level_3": 10,
    "level_4": 10,
    "level_5": 10,
}

LEVEL_EMOJI = {
    "starter": "🟢",
    "level_1": "🔵",
    "level_2": "🟡",
    "level_3": "🟠",
    "level_4": "🔴",
    "level_5": "🟣",
}


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=f"{LEVEL_EMOJI['starter']} Starter"),
        KeyboardButton(text=f"{LEVEL_EMOJI['level_1']} Level 1")
    )
    builder.row(
        KeyboardButton(text=f"{LEVEL_EMOJI['level_2']} Level 2"),
        KeyboardButton(text=f"{LEVEL_EMOJI['level_3']} Level 3")
    )
    builder.row(
        KeyboardButton(text=f"{LEVEL_EMOJI['level_4']} Level 4"),
        KeyboardButton(text=f"{LEVEL_EMOJI['level_5']} Level 5")
    )
    builder.row(
        KeyboardButton(text="📚 منابع کتاب"),
        KeyboardButton(text="📊 پیشرفت من")
    )
    builder.row(KeyboardButton(text="⚙️ تنظیمات"))
    return builder.as_markup(resize_keyboard=True)


def get_request_access_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📨 درخواست دسترسی", callback_data="request_access"))
    return builder.as_markup()


def get_level_units_keyboard(level: str) -> InlineKeyboardMarkup:
    """منوی اصلی سطح: Audios + Videos + تمرینات + بازگشت"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="🎧 Audios",
        callback_data=f"audio_type:{level}"
    ))
    builder.row(InlineKeyboardButton(
        text="🎬 Videos",
        callback_data=f"videos_categories:{level}"
    ))
    builder.row(InlineKeyboardButton(
        text="📝 تمرینات",
        callback_data=f"exercises_menu:{level}"
    ))
    builder.row(InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back:main"))
    return builder.as_markup()


def get_audio_type_keyboard(level: str) -> InlineKeyboardMarkup:
    """انتخاب نوع کتاب صوتی: Student Book یا Workbook"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="📘 Student Book",
        callback_data=f"audio_units:{level}:student_book"
    ))
    builder.row(InlineKeyboardButton(
        text="📗 Workbook",
        callback_data=f"audio_units:{level}:workbook"
    ))
    
    builder.row(InlineKeyboardButton(text="🔙 بازگشت به منوی سطح", callback_data=f"level_menu:{level}"))
    return builder.as_markup()


def get_audio_units_keyboard(level: str, book_type: str) -> InlineKeyboardMarkup:
    """نمایش Unitها برای یک نوع کتاب صوتی"""
    builder = InlineKeyboardBuilder()
    num_units = LEVEL_UNITS.get(level, 12)
    
    for i in range(1, num_units + 1):
        builder.add(InlineKeyboardButton(
            text=f"Unit {i}",
            callback_data=f"audio_unit_select:{level}:{i}:{book_type}"
        ))
    builder.adjust(2)
    
    book_display = "Student Book" if book_type == "student_book" else "Workbook"
    builder.row(InlineKeyboardButton(
        text=f"🔙 بازگشت",
        callback_data=f"audio_type:{level}"
    ))
    return builder.as_markup()


def get_videos_categories_keyboard(level: str) -> InlineKeyboardMarkup:
    """نمایش دسته‌بندی‌های ویدیو برای یک سطح"""
    builder = InlineKeyboardBuilder()
    
    if level == "level_5":
        categories = [
            ("🎙 Interview", "interview"),
            ("🔄 Review and Check", "review"),
            ("🌆 On the Street", "street")
        ]
    else:
        categories = [
            ("💼 Practical English", "practical"),
            ("🔄 Review and Check", "review"),
            ("🎧 Video Listening", "listening")
        ]

    for text, cat in categories:
        builder.row(InlineKeyboardButton(
            text=text, 
            callback_data=f"media_list:{level}:0:{cat}"
        ))
    
    builder.row(InlineKeyboardButton(text="🔙 بازگشت به منوی سطح", callback_data=f"level_menu:{level}"))
    return builder.as_markup()


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back:main"))
    return builder.as_markup()