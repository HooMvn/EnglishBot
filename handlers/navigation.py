import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery
from keyboards import (
    LEVEL_EMOJI, 
    get_level_units_keyboard, 
    get_main_menu_keyboard,
    get_audio_type_keyboard,
    get_audio_units_keyboard,
    get_videos_categories_keyboard,
    get_back_to_main_keyboard
)

router = Router()
logger = logging.getLogger(__name__)

def _level_display(level: str) -> str:
    emoji = LEVEL_EMOJI.get(level, "📘")
    name = level.replace("_", " ").title()
    return f"{emoji} {name}"


# ✅ بازگشت به منوی سطح (Audios/Videos/تمرینات)
@router.callback_query(F.data.startswith("level_menu:"))
async def handle_back_to_level(callback: CallbackQuery) -> None:
    try:
        _, level = callback.data.split(":")
        await callback.message.edit_text(
            f"📚 سطح: {_level_display(level)}\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=get_level_units_keyboard(level),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling back-to-level: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data == "back:main")
async def handle_back_to_main(callback: CallbackQuery) -> None:
    try:
        await callback.message.delete()
        await callback.message.answer(
            "🏠 منوی اصلی\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=get_main_menu_keyboard(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling back-to-main: {e}")
        await callback.answer("️ خطایی رخ داد.", show_alert=True)


# ✅ نمایش Student Book / Workbook
@router.callback_query(F.data.startswith("audio_type:"))
async def handle_audio_type(callback: CallbackQuery) -> None:
    try:
        _, level = callback.data.split(":")
        await callback.message.edit_text(
            "🎧 نوع کتاب صوتی را انتخاب کنید:",
            reply_markup=get_audio_type_keyboard(level),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling audio type: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


# ✅ نمایش Unitها برای یک نوع کتاب
@router.callback_query(F.data.startswith("audio_units:"))
async def handle_audio_units(callback: CallbackQuery) -> None:
    try:
        _, level, book_type = callback.data.split(":")
        book_display = "Student Book" if book_type == "student_book" else "Workbook"
        await callback.message.edit_text(
            f"📚 {book_display}\n\nلطفاً Unit مورد نظر را انتخاب کنید:",
            reply_markup=get_audio_units_keyboard(level, book_type),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling audio units: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


# ✅ وقتی Unit را می‌زند، لیست ویس‌ها را نشان دهد
@router.callback_query(F.data.startswith("audio_unit_select:"))
async def handle_audio_unit_select(callback: CallbackQuery) -> None:
    try:
        _, level, unit_num, book_type = callback.data.split(":")
        unit = int(unit_num)
        from handlers.audio import send_audio_list
        await send_audio_list(callback.message, level, unit, book_type)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling audio unit select: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


# ✅ نمایش دسته‌بندی ویدیوها
@router.callback_query(F.data.startswith("videos_categories:"))
async def handle_videos_categories(callback: CallbackQuery) -> None:
    try:
        _, level = callback.data.split(":")
        await callback.message.edit_text(
            "🎬 دسته‌بندی ویدیوها:\n\nلطفاً دسته مورد نظر را انتخاب کنید:",
            reply_markup=get_videos_categories_keyboard(level),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling videos categories: {e}")
        await callback.answer("️ خطایی رخ داد.", show_alert=True)


# ✅ منوی تمرینات (placeholder)
@router.callback_query(F.data.startswith("exercises_menu:"))
async def handle_exercises_menu(callback: CallbackQuery) -> None:
    try:
        _, level = callback.data.split(":")
        await callback.message.edit_text(
            "🛠 بخش تمرینات در حال ساخت است.\n\nبه زودی تمرینات این سطح اضافه خواهد شد.",
            reply_markup=get_back_to_main_keyboard(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling exercises menu: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)