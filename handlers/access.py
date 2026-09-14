"""
Access control handlers.

Handles the "request access" flow: a user without access can request it,
the admin is notified with an inline approve/decline keyboard, and the
admin's decision updates the whitelist and access_requests table and
notifies the requesting user.
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import db, bot
from config import ADMIN_USER_IDS  # <-- تغییر: از لیست استفاده می‌کنیم

logger = logging.getLogger(__name__)

router = Router()


async def check_access(user_id: int) -> bool:
    """
    Check whether a user is allowed to use the bot.

    Returns True if the user is in the admin list or is present in the
    whitelist, False otherwise.
    """
    # چک لیست ادمین‌ها
    if user_id in ADMIN_USER_IDS:
        logger.info(f"✅ User {user_id} is ADMIN - access granted")
        return True
    
    # چک whitelist
    try:
        is_whitelisted = await db.is_in_whitelist(user_id)
        if is_whitelisted:
            logger.info(f"✅ User {user_id} is in whitelist - access granted")
            return True
        else:
            logger.warning(f"⚠️ User {user_id} is NOT in whitelist - access denied")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking whitelist for user {user_id}: {e}")
        return False


@router.callback_query(F.data == "request_access")
async def handle_request_access(callback: CallbackQuery) -> None:
    """Save an access request and notify ALL admins with a decision keyboard."""
    try:
        user = callback.from_user
        logger.info(f"📝 User {user.id} (@{user.username}) requesting access")

        await db.save_access_request(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        logger.info(f"✅ Access request saved for user {user.id}")

        await callback.message.edit_text(
            "✅ درخواست شما ارسال شد. لطفاً صبر کنید تا ادمین بررسی کند."
        )

        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(
                text="✅ تأیید", callback_data=f"approve_req:{user.id}"
            ),
            InlineKeyboardButton(
                text="❌ رد", callback_data=f"decline_req:{user.id}"
            ),
        )
        builder.adjust(2)

        admin_text = (
            "🔔 درخواست دسترسی جدید\n\n"
            f"👤 نام: {user.first_name} {user.last_name or ''}\n"
            f"🆔 یوزرنیم: @{user.username or 'ندارد'}\n"
            f"🔢 user_id: {user.id}\n"
            f"📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        # ارسال به تمام ادمین‌ها
        for admin_id in ADMIN_USER_IDS:
            try:
                await bot.send_message(
                    admin_id, admin_text, reply_markup=builder.as_markup()
                )
            except Exception as e:
                logger.error(f"❌ Failed to notify admin {admin_id}: {e}")
        
        logger.info(f"✅ All admins notified about user {user.id}'s request")

        await callback.answer()
    except Exception as e:
        logger.error(f"Error handling access request: {e}")
        await callback.answer("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.", show_alert=True)


@router.callback_query(F.data.startswith("approve_req:"))
async def handle_approve_request(callback: CallbackQuery) -> None:
    """Admin-only: approve a pending access request."""
    if callback.from_user.id not in ADMIN_USER_IDS:
        await callback.answer("⛔ فقط ادمین مجاز است", show_alert=True)
        return

    try:
        target_user_id = int(callback.data.split(":")[1])
        logger.info(f"✅ Admin {callback.from_user.id} approving request for user {target_user_id}")

        await db.add_to_whitelist(target_user_id, callback.from_user.id)
        logger.info(f"✅ User {target_user_id} added to whitelist")
        
        await db.update_request_status(target_user_id, "approved", callback.from_user.id)
        logger.info(f"✅ Request status updated to 'approved' for user {target_user_id}")

        await callback.message.edit_text(
            f"✅ کاربر تأیید و به لیست سفید اضافه شد.\n"
            f"(تأیید شده توسط ادمین {callback.from_user.id})"
        )

        await bot.send_message(
            target_user_id,
            "✅ درخواست شما تأیید شد! \n\nحالا می‌توانی از ربات استفاده کنی. دستور /start را بزن.",
        )
        logger.info(f"✅ User {target_user_id} notified about approval")

        await callback.answer()
    except Exception as e:
        logger.error(f"Error approving access request: {e}")
        await callback.answer("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.", show_alert=True)


@router.callback_query(F.data.startswith("decline_req:"))
async def handle_decline_request(callback: CallbackQuery) -> None:
    """Admin-only: decline a pending access request."""
    if callback.from_user.id not in ADMIN_USER_IDS:
        await callback.answer("⛔ فقط ادمین مجاز است", show_alert=True)
        return

    try:
        target_user_id = int(callback.data.split(":")[1])
        logger.info(f"❌ Admin {callback.from_user.id} declining request for user {target_user_id}")

        await db.update_request_status(target_user_id, "declined", callback.from_user.id)
        logger.info(f"✅ Request status updated to 'declined' for user {target_user_id}")

        await callback.message.edit_text(
            f"❌ درخواست کاربر رد شد.\n"
            f"(رد شده توسط ادمین {callback.from_user.id})"
        )

        await bot.send_message(
            target_user_id, "❌ متأسفانه درخواست دسترسی شما رد شد."
        )
        logger.info(f"✅ User {target_user_id} notified about decline")

        await callback.answer()
    except Exception as e:
        logger.error(f"Error declining access request: {e}")
        await callback.answer("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.", show_alert=True)