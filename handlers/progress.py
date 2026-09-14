"""
Handler for displaying a user's learning progress and streak statistics.
"""

import logging

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import db
from handlers.access import check_access
from keyboards import get_back_to_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "📊 پیشرفت من")
async def handle_show_progress(message: Message) -> None:
    """Show the user's overall progress: streak, completed exercises, and accuracy."""
    try:
        user_id = message.from_user.id

        if not await check_access(user_id):
            return

        streak = await db.get_user_streak(user_id)
        progress = await db.get_user_progress(user_id)

        completed_exercises = progress.get("completed_exercises", 0)
        total_questions = progress.get("total_questions", 0)
        total_score = progress.get("total_score", 0)
        accuracy = progress.get("accuracy", 0.0) or 0.0

        text = (
            "📊 پیشرفت یادگیری شما\n\n"
            f"🔥 تعداد روزهای متوالی فعالیت (Streak): {streak} روز\n\n"
            "📈 آمار کلی:\n"
            f"✅ تمرینات تکمیل‌شده: {completed_exercises}\n"
            f"🎯 مجموع سوالات پاسخ‌داده‌شده: {total_questions}\n"
            f"🏆 امتیاز کل: {total_score}\n"
            f"📊 درصد پاسخ‌های صحیح: {accuracy:.1f}%"
        )

        if completed_exercises == 0:
            text += (
                "\n\n👋 هنوز تمرینی را شروع نکرده‌اید. "
                "از منوی اصلی یک سطح را انتخاب کنید!"
            )

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back:main")
        )

        await message.answer(text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Error showing progress for user {message.from_user.id}: {e}")
        await message.answer(
            "⚠️ خطایی در نمایش پیشرفت رخ داد. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_to_main_keyboard(),
        )
