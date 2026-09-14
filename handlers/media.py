"""
Media handlers: listing categorized video tracks with pagination, file names, and smart prefix removal.
"""
import logging
import re
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot import db
from keyboards import get_back_to_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

# ✅ تغییر به 16 تا در هر صفحه تا ردیف آخر کاملاً پر شود (4 ردیف 4 تایی)
BUTTONS_PER_PAGE = 16

# ✅ نگاشت نام کامل دسته‌ها برای نمایش در هدر
CATEGORY_NAMES = {
    "practical": "Practical English",
    "review": "Review and Check",
    "listening": "Video Listening",
    "interview": "Interview",
    "street": "On the Street"
}

def natural_sort_key(s):
    """تابع مرتب‌سازی طبیعی برای جلوگیری از مشکل 1, 10, 2"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def get_common_prefix(strings):
    """پیدا کردن پیشوند مشترک بین تمام رشته‌ها برای حذف از نمایش"""
    if not strings:
        return ""
    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    # حذف کاراکترهای جداکننده اضافی (مثل _ یا -) در انتهای پیشوند
    if prefix and prefix[-1] in ('_', '-', ' '):
        prefix = prefix[:-1]
    return prefix


@router.callback_query(F.data.startswith("media_list:"))
async def handle_media_list(callback: CallbackQuery) -> None:
    try:
        _, level, unit_str, category = callback.data.split(":")
        unit = int(unit_str)
        page = 0  # صفحه اول
        
        # ✅ استفاده از نام کامل دسته
        category_display = CATEGORY_NAMES.get(category, category.replace('_', ' ').title())
        
        # فقط ویدیوها را دریافت می‌کنیم
        videos = await db.get_media_by_category(level, unit, category, "video")
        
        if not videos:
            await callback.message.edit_text(
                f"️ هنوز ویدیویی برای بخش '{category_display}' در این سطح اضافه نشده است.",
                reply_markup=get_back_to_main_keyboard()
            )
            await callback.answer()
            return

        # ✅ مرتب‌سازی طبیعی (Natural Sort) بر اساس track_number
        videos.sort(key=lambda v: natural_sort_key(v.get('track_number', v.get('title', ''))))

        builder = InlineKeyboardBuilder()
        
        # هدر
        header = f"📂 محتوای بخش: <b>{category_display}</b>\n\n"
        
        # محاسبه محدوده صفحه
        start_idx = page * BUTTONS_PER_PAGE
        end_idx = min(start_idx + BUTTONS_PER_PAGE, len(videos))
        page_videos = videos[start_idx:end_idx]
        
        # ✅ پیدا کردن پیشوند مشترک بین تمام ویدیوهای این بخش
        all_titles = [v.get('title', '') for v in videos]
        common_prefix = get_common_prefix(all_titles)
        
        # اضافه کردن لیست نام فایل‌ها در متن پیام
        for idx, video in enumerate(page_videos, start=start_idx + 1):
            title = video.get('title', 'Unknown')
            
            # حذف پیشوند مشترک برای نمایش تمیزتر
            if title.startswith(common_prefix):
                display_title = title[len(common_prefix):]
            else:
                display_title = title
                
            # ✅ حذف آندرلاین اول اگر وجود داشت
            if display_title.startswith('_'):
                display_title = display_title[1:]
                
            # کوتاه کردن عنوان اگر خیلی طولانی بود
            if len(display_title) > 50:
                display_title = display_title[:47] + "..."
            header += f"{idx}. {display_title}\n"
        
        header += "\nلطفاً شماره مورد نظر را انتخاب کنید:"
        
        # اضافه کردن دکمه‌ها فقط با شماره ردیف
        for idx in range(start_idx + 1, end_idx + 1):
            builder.add(InlineKeyboardButton(
                text=f"{idx}",
                callback_data=f"play_video:{videos[idx-1]['id']}"
            ))
        
        # چیدمان 4 دکمه در هر ردیف
        builder.adjust(4)
        
        # دکمه‌های صفحه‌بندی
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ قبلی",
                callback_data=f"media_page:{level}:{unit}:{category}:{page-1}"
            ))
        if end_idx < len(videos):
            nav_buttons.append(InlineKeyboardButton(
                text="بعدی ▶️",
                callback_data=f"media_page:{level}:{unit}:{category}:{page+1}"
            ))
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        builder.row(InlineKeyboardButton(text=" بازگشت", callback_data=f"level_menu:{level}"))

        await callback.message.edit_text(header, reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling media list: {e}")
        await callback.answer("️ خطایی رخ داد.", show_alert=True)


@router.callback_query(F.data.startswith("media_page:"))
async def handle_media_page(callback: CallbackQuery) -> None:
    try:
        _, level, unit_str, category, page_num = callback.data.split(":")
        unit = int(unit_str)
        page = int(page_num)
        
        category_display = CATEGORY_NAMES.get(category, category.replace('_', ' ').title())
        
        videos = await db.get_media_by_category(level, unit, category, "video")
        
        if not videos:
            await callback.answer("⚠️ ویدیویی یافت نشد.", show_alert=True)
            return

        # ✅ مرتب‌سازی طبیعی (Natural Sort) بر اساس track_number
        videos.sort(key=lambda v: natural_sort_key(v.get('track_number', v.get('title', ''))))

        builder = InlineKeyboardBuilder()
        
        header = f" محتوای بخش: <b>{category_display}</b>\n\n"
        
        # محاسبه محدوده صفحه
        start_idx = page * BUTTONS_PER_PAGE
        end_idx = min(start_idx + BUTTONS_PER_PAGE, len(videos))
        page_videos = videos[start_idx:end_idx]
        
        # ✅ پیدا کردن پیشوند مشترک
        all_titles = [v.get('title', '') for v in videos]
        common_prefix = get_common_prefix(all_titles)
        
        # اضافه کردن لیست نام فایل‌ها
        for idx, video in enumerate(page_videos, start=start_idx + 1):
            title = video.get('title', 'Unknown')
            if title.startswith(common_prefix):
                display_title = title[len(common_prefix):]
            else:
                display_title = title
                
            # ✅ حذف آندرلاین اول
            if display_title.startswith('_'):
                display_title = display_title[1:]
                
            if len(display_title) > 50:
                display_title = display_title[:47] + "..."
            header += f"{idx}. {display_title}\n"
        
        header += "\nلطفاً شماره مورد نظر را انتخاب کنید:"
        
        # اضافه کردن دکمه‌ها
        for idx in range(start_idx + 1, end_idx + 1):
            builder.add(InlineKeyboardButton(
                text=f"{idx}",
                callback_data=f"play_video:{videos[idx-1]['id']}"
            ))
        
        # چیدمان 4 دکمه در هر ردیف
        builder.adjust(4)
        
        # دکمه‌های صفحه‌بندی
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="◀️ قبلی",
                callback_data=f"media_page:{level}:{unit}:{category}:{page-1}"
            ))
        if end_idx < len(videos):
            nav_buttons.append(InlineKeyboardButton(
                text="بعدی ▶️",
                callback_data=f"media_page:{level}:{unit}:{category}:{page+1}"
            ))
        
        if nav_buttons:
            builder.row(*nav_buttons)
        
        builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"level_menu:{level}"))

        await callback.message.edit_text(header, reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling media page: {e}")
        await callback.answer("⚠️ خطایی رخ داد.", show_alert=True)