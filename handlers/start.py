"""
/start command handler and main-menu reply-keyboard button handlers.
"""

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot import db
from handlers.access import check_access
from keyboards import (
    get_level_units_keyboard,
    get_main_menu_keyboard,
    get_request_access_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)

# Maps the reply-keyboard button text to the internal level identifier
# used throughout the database and callback data.
LEVEL_BUTTON_TO_LEVEL = {
    "🟢 Starter": "starter",
    "🔵 Level 1": "level_1",
    "🟡 Level 2": "level_2",
    "🟠 Level 3": "level_3",
    "🔴 Level 4": "level_4",
    "🟣 Level 5": "level_5",
}


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle the /start command: gate access, else show the main menu."""
    try:
        user_id = message.from_user.id

        # Update user activity (streak) regardless of access status.
        await db.update_user_activity(user_id)

        if not await check_access(user_id):
            req = await db.get_request_by_user(user_id)

            if req and req["status"] == "pending":
                await message.answer(
                    "⏳ درخواست دسترسی شما قبلاً ارسال شده و در انتظار بررسی ادمین است."
                )
            elif req and req["status"] == "declined":
                await message.answer(
                    "❌ درخواست قبلی شما رد شده است. در صورت نیاز مجدداً درخواست دهید.",
                    reply_markup=get_request_access_keyboard(),
                )
            else:
                await message.answer(
                    "⛔ دسترسی محدود\n\n"
                    "این ربات فقط برای کاربران تأیید شده است.\n"
                    "اگر فکر می‌کنی باید دسترسی داشته باشی، روی دکمه زیر بزن:",
                    reply_markup=get_request_access_keyboard(),
                )
            return

        # User has access.
        await message.answer(
            f"👋 سلام {message.from_user.first_name}!\n\n"
            "به ربات تمرین انگلیسی خوش آمدید. 🇺🇸\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=get_main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error handling /start for message {message.message_id}: {e}")


@router.message(F.text.in_(LEVEL_BUTTON_TO_LEVEL.keys()))
async def handle_level_selection(message: Message) -> None:
    """Handle main-menu level button clicks by showing the level's units."""
    try:
        if not await check_access(message.from_user.id):
            # /start manages the access-request flow; ignore silently here.
            return

        level = LEVEL_BUTTON_TO_LEVEL.get(message.text)
        if level:
            await message.answer(
                f"📚 سطح انتخاب شده: {message.text}\nلطفاً یک Unit را انتخاب کنید:",
                reply_markup=get_level_units_keyboard(level),
            )
    except Exception as e:
        logger.error(f"Error handling level selection '{message.text}': {e}")


@router.message(F.text == "⚙️ تنظیمات")
async def handle_settings_selection(message: Message) -> None:
    """Placeholder for the settings section."""
    if not await check_access(message.from_user.id):
        return
    await message.answer("⚙️ تنظیمات به زودی اضافه می‌شود.")
