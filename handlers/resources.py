"""
Resource handlers: نمایش گروه‌بندی شده منابع (PDF, Audios, Videos)
"""
import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot import bot, db
from handlers.access import check_access
from keyboards import LEVEL_EMOJI, get_back_to_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

# ✅ اصلاح: حذف گروه Scripts و ادغام با Videos
RESOURCE_GROUPS = {
    "pdf": {
        "name": "📕 PDFs",
        "types": ["student_book_pdf", "workbook_pdf", "teacher_pdf"]
    },
    "audios": {
        "name": "🎧 Audios",
        "types": ["student_book_audio", "workbook_audio"]
    },
    "videos": {
        "name": "🎬 Videos",
        "types": [
            "practical_video", "review_video", "listening_video", 
            "interview_video", "street_video",
            "script_pdf", "script_zip"  # ✅ اسکریپت‌ها در Videos
        ]
    }
}


@router.message(F.text.contains("منابع"))
async def handle_resources_menu(message: Message) -> None:
    try:
        if not await check_access(message.from_user.id):
            return

        builder = InlineKeyboardBuilder()
        for level, emoji in LEVEL_EMOJI.items():
            name = level.replace("_", " ").title()
            builder.add(InlineKeyboardButton(text=f"{emoji} {name}", callback_data=f"resources_level:{level}"))
        builder.adjust(2)
        builder.row(InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back:main"))

        await message.answer("📚 منابع کتاب\n\nلطفاً سطح مورد نظر را انتخاب کن:", reply_markup=builder.as_markup())
    except Exception as e:
        logger.error(f"Error showing resources menu: {e}")


@router.callback_query(F.data.startswith("resources_level:"))
async def handle_resources_level(callback: CallbackQuery) -> None:
    try:
        _, level = callback.data.split(":")
        resources = await db.get_resources_by_level(level)

        if not resources:
            await callback.message.edit_text(
                "هنوز منبعی برای این سطح ثبت نشده است.",
                reply_markup=get_back_to_main_keyboard(),
            )
            await callback.answer()
            return

        # گروه‌بندی منابع
        grouped_resources = {group: [] for group in RESOURCE_GROUPS.keys()}
        
        for res in resources:
            rtype = res.get("resource_type", "unknown")
            for group, config in RESOURCE_GROUPS.items():
                if rtype in config["types"]:
                    grouped_resources[group].append(res)
                    break

        # ساخت دکمه‌ها
        builder = InlineKeyboardBuilder()
        level_name = level.replace("_", " ").title()
        emoji = LEVEL_EMOJI.get(level, "📘")
        
        for group_key, config in RESOURCE_GROUPS.items():
            count = len(grouped_resources[group_key])
            if count > 0:
                builder.row(InlineKeyboardButton(
                    text=f"{config['name']} ({count} فایل)",
                    callback_data=f"download_group:{level}:{group_key}"
                ))
        
        builder.row(InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back:main"))

        await callback.message.edit_text(
            f"📚 منابع سطح {emoji} {level_name}:\n\nلطفاً دسته مورد نظر را انتخاب کنید:",
            reply_markup=builder.as_markup()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("download_group:"))
async def handle_download_group(callback: CallbackQuery) -> None:
    temp_message = None
    try:
        _, level, group_key = callback.data.split(":")
        
        if group_key not in RESOURCE_GROUPS:
            await callback.answer("⚠️ گروه نامعتبر است.", show_alert=True)
            return
        
        resources = await db.get_resources_by_level(level)
        config = RESOURCE_GROUPS[group_key]
        
        # فیلتر کردن فایل‌های این گروه
        filtered = [r for r in resources if r.get("resource_type") in config["types"]]
        
        if not filtered:
            await callback.answer("⚠️ فایلی در این گروه وجود ندارد.", show_alert=True)
            return
        
        temp_message = await callback.message.answer(f"⏳ در حال ارسال {config['name']}، لطفاً صبر کنید...")
        
        # ارسال فایل‌ها بدون کپشن
        for res in filtered:
            await bot.send_document(
                chat_id=callback.message.chat.id,
                document=res["file_id"],
            )
        
        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling download request: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)
    finally:
        if temp_message is not None:
            try:
                await temp_message.delete()
            except Exception:
                pass