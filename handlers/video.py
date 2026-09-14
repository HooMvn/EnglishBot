"""
Video track handlers: sending video cleanly without extra captions or buttons.
"""
import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery
from bot import bot, db

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("play_video:"))
async def handle_play_video(callback: CallbackQuery) -> None:
    try:
        video_id = int(callback.data.split(":")[1])
        video = await db.get_video_track(video_id)

        if not video:
            await callback.answer("⚠️ این ویدیو یافت نشد.", show_alert=True)
            return

        # ✅ ارسال ویدیو بدون هیچ کپشن یا دکمه‌ی اضافی
        await bot.send_video(
            chat_id=callback.message.chat.id,
            video=video["video_file_id"],
            supports_streaming=True,
        )

        await callback.answer()
    except Exception as e:
        logger.error(f"Error playing video: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)