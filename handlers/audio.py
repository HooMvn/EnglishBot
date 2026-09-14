"""
Audio handlers: paginated audio track listing with clean sending.
"""
import logging
from typing import Optional
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot import bot, db
from keyboards import get_back_to_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

BUTTONS_PER_PAGE = 16


def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        seconds = 0
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


# ✅ تابع جدید: نمایش لیست ویس‌ها (قابل فراخوانی از navigation.py)
async def send_audio_list(message: Message, level: str, unit: int, book_type: str, page: int = 0) -> None:
    tracks = await db.get_audio_tracks(level, unit, book_type)

    if not tracks:
        book_display = "Student Book" if book_type == "student_book" else "Workbook"
        await message.edit_text(
            f"⚠️ هنوز ویسی برای {book_display} - Unit {unit} اضافه نشده است.",
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    builder = InlineKeyboardBuilder()
    
    book_display = "Student Book" if book_type == "student_book" else "Workbook"
    header = f" لیست ویس‌های {book_display} - Unit {unit}"
    
    start_idx = page * BUTTONS_PER_PAGE
    end_idx = min(start_idx + BUTTONS_PER_PAGE, len(tracks))
    page_tracks = tracks[start_idx:end_idx]
    
    for track in page_tracks:
        builder.add(InlineKeyboardButton(
            text=f"▶️ {track['track_number']}",
            callback_data=f"play_track:{track['id']}",
        ))
    
    builder.adjust(2)
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="️ قبلی◀️",
            callback_data=f"audio_page:{level}:{unit}:{book_type}:{page-1}"
        ))
    if end_idx < len(tracks):
        nav_buttons.append(InlineKeyboardButton(
            text="بعدی ▶️",
            callback_data=f"audio_page:{level}:{unit}:{book_type}:{page+1}"
        ))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(InlineKeyboardButton(
        text="🔙 بازگشت",
        callback_data=f"audio_units:{level}:{book_type}"
    ))

    await message.edit_text(header, reply_markup=builder.as_markup())


# Handler قدیمی (برای سازگاری)
@router.callback_query(F.data.startswith("audio_list:"))
async def handle_audio_list(callback: CallbackQuery) -> None:
    try:
        _, level, unit_num, book_type = callback.data.split(":")
        unit = int(unit_num)
        await send_audio_list(callback.message, level, unit, book_type)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling audio list: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("audio_page:"))
async def handle_audio_page(callback: CallbackQuery) -> None:
    try:
        _, level, unit_num, book_type, page_num = callback.data.split(":")
        unit = int(unit_num)
        page = int(page_num)
        await send_audio_list(callback.message, level, unit, book_type, page)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling audio page: {e}")
        await callback.answer("️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("play_track:"))
async def handle_play_track(callback: CallbackQuery) -> None:
    try:
        track_id = int(callback.data.split(":")[1])
        track = await db.get_audio_track(track_id)

        if not track:
            await callback.answer("⚠️ این ویس یافت نشد.", show_alert=True)
            return

        await bot.send_audio(
            chat_id=callback.message.chat.id,
            audio=track["audio_file_id"],
            title=track["title"],
            performer=f"Unit {track['unit']}",
        )

        await callback.answer()
    except Exception as e:
        logger.error(f"Error playing track: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)