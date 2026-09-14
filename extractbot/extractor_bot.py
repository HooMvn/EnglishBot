"""
ربات استخراج File ID (نسخه نهایی، هوشمند و بدون باگ - ضد قطعی)
"""
print("✅ اسکریپت شروع به اجرا کرد!")

import asyncio
import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from aiogram.client.session.aiohttp import AiohttpSession

BOT_TOKEN = "8877435739:AAHT0hg3Rdlaqt_lZxTPDglvJPa1RDedn0s"
OUTPUT_FILE = "input.csv"
STATE_FILE = "bot_state.json"

router = Router()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# ----------------------------------------------------------------------
# مدیریت وضعیت (فقط داده‌های قابل ذخیره در JSON)
# ----------------------------------------------------------------------
def load_state():
    if Path(STATE_FILE).exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    safe_state = {}
    for user_id, data in state.items():
        safe_state[user_id] = {
            'metadata': data.get('metadata', ''),
            'count': data.get('count', 0)
        }
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(safe_state, f, ensure_ascii=False, indent=2)

state = load_state()
active_timers = {}

def natural_sort_key(filename):
    name = filename.lower()
    parts = re.split(r'(\d+)', name)
    return [int(p) if p.isdigit() else p for p in parts]

# ----------------------------------------------------------------------
# توابع کمکی
# ----------------------------------------------------------------------
async def send_batch_summary(user_id: int, bot: Bot):
    user_state = state.get(str(user_id), {})
    count = user_state.get('count', 0)
    metadata = user_state.get('metadata', '')
    
    if count > 0:
        summary = f"✅ <b>{count} فایل با موفقیت ذخیره شد!</b>\n"
        if metadata:
            summary += f"📝 Metadata: <b>{metadata}</b>"
        
        try:
            await bot.send_message(user_id, summary)
            logging.info(f"📊 خلاصه ارسال شد برای کاربر {user_id}: {count} فایل")
        except Exception as e:
            logging.error(f"Error sending summary: {e}")

async def schedule_batch_summary(user_id: int, bot: Bot, delay: float = 2.0):
    if user_id in active_timers:
        active_timers[user_id].cancel()
    
    async def delayed_summary():
        await asyncio.sleep(delay)
        await send_batch_summary(user_id, bot)
        if user_id in active_timers:
            del active_timers[user_id]
    
    task = asyncio.create_task(delayed_summary())
    active_timers[user_id] = task

# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🤖 <b>ربات استخراج File ID (نسخه نهایی)</b>\n\n"
        "💡 <b>نحوه کار:</b>\n"
        "1. یک پیام متنی بفرست (مثلاً: <code>#Starter</code>)\n"
        "2. فایل‌ها را فوروارد کن (تکی یا دسته‌جمعی)\n"
        "3. بعد از ۲ ثانیه توقف، خلاصه را می‌بینی.\n\n"
        "🛡️ <b>ویژگی:</b> اگر اینترنت قطع شود، اطلاعات از دست نمی‌رود!\n\n"
        "📋 <b>دستورات:</b>\n"
        "/status - وضعیت فعلی\n"
        "/reset - پاک کردن همه چیز\n"
        "/export - دریافت CSV مرتب‌شده (با هدر تضمین‌شده)"
    )

@router.message(Command("status"))
async def cmd_status(message: Message):
    user_state = state.get(str(message.from_user.id), {})
    await message.answer(
        f"📊 <b>وضعیت فعلی:</b>\n"
        f"🔢 فایل‌های ذخیره‌شده: <b>{user_state.get('count', 0)}</b>\n"
        f"📝 Metadata: <b>{user_state.get('metadata', 'تنظیم نشده')}</b>"
    )

@router.message(F.text & ~F.text.startswith('/'))
async def handle_text_metadata(message: Message):
    text = message.text.strip()
    if not text:
        return
    
    user_id = str(message.from_user.id)
    state[user_id] = {'metadata': text, 'count': 0}
    save_state(state)
    
    await message.answer(f"✅ Metadata تنظیم شد: <b>{text}</b>\nحالا فایل‌ها را فوروارد کن.")

@router.message(F.audio | F.document | F.voice | F.video)
async def handle_file(message: Message):
    file_info = message.audio or message.document or message.voice or message.video
    if not file_info:
        return
    
    file_type = "audio" if message.audio else "video" if message.video else "document" if message.document else "voice"
    file_id = file_info.file_id
    filename = getattr(file_info, 'file_name', None) or f"file_{file_info.file_unique_id}"
    duration = getattr(file_info, 'duration', 0) or 0
    file_size = getattr(file_info, 'file_size', 0) or 0
    size_mb = round(file_size / (1024 * 1024), 2)
    
    user_id = str(message.from_user.id)
    if user_id not in state:
        state[user_id] = {'metadata': '', 'count': 0}
    
    metadata = state[user_id].get('metadata', '')
    
    # ذخیره آنی در CSV (با بررسی هوشمند برای نوشتن هدر فقط در صورت نیاز)
    file_exists = Path(OUTPUT_FILE).exists()
    # اگر فایل وجود ندارد یا وجود دارد اما کاملاً خالی است، هدر را بنویس
    write_header = not file_exists or (file_exists and Path(OUTPUT_FILE).stat().st_size == 0)
    
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["filename", "file_type", "file_id", "duration", "size_mb", "metadata", "added_time"])
        writer.writerow([filename, file_type, file_id, duration, size_mb, metadata, datetime.now().isoformat()])
    
    state[user_id]['count'] = state[user_id].get('count', 0) + 1
    save_state(state)
    
    current_count = state[user_id]['count']
    logging.info(f"✅ Saved: {filename} | Type: {file_type} | Meta: {metadata} | Count: {current_count}")
    
    await schedule_batch_summary(message.from_user.id, message.bot, delay=2.0)

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    user_id = str(message.from_user.id)
    if user_id in state:
        del state[user_id]
        save_state(state)
    if Path(OUTPUT_FILE).exists():
        Path(OUTPUT_FILE).unlink()
    
    if message.from_user.id in active_timers:
        active_timers[message.from_user.id].cancel()
        del active_timers[message.from_user.id]
        
    await message.answer("🗑 همه چیز پاک شد و از نو شروع کن.")

@router.message(Command("export"))
async def cmd_export(message: Message):
    if not Path(OUTPUT_FILE).exists():
        await message.answer("📭 فایلی وجود ندارد.")
        return
    
    # خواندن تمام خطوط فایل به صورت خام
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    if not lines:
        await message.answer("📭 فایل خالی است.")
        return

    # بررسی هوشمند: آیا خط اول هدر است یا دیتا؟
    first_line = lines[0].strip()
    if first_line.startswith("filename"):
        header = first_line + "\n"
        data_lines = lines[1:]
    else:
        # اگر هدر ندارد، یک هدر استاندارد اضافه می‌کنیم و همه خطوط را دیتا در نظر می‌گیریم
        header = "filename,file_type,file_id,duration,size_mb,metadata,added_time\n"
        data_lines = lines

    # حذف خطوط کاملاً خالی برای جلوگیری از باگ و شمارش اشتباه
    clean_rows = [line.strip() for line in data_lines if line.strip()]
    
    # تابع سورت ایمن بر اساس نام فایل (ستون اول)
    def sort_key(line):
        parts = line.split(",", 1)
        filename = parts[0] if parts else ""
        return natural_sort_key(filename)
        
    sorted_rows = sorted(clean_rows, key=sort_key)
    
    sorted_file = f"extracted_sorted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # نوشتن فایل نهایی با هدر تضمین‌شده
    with open(sorted_file, "w", newline="", encoding="utf-8") as f:
        f.write(header)
        for row in sorted_rows:
            f.write(row + "\n")
    
    with open(sorted_file, "rb") as f:
        await message.answer_document(
            BufferedInputFile(f.read(), filename=sorted_file),
            caption=f"📊 {len(sorted_rows)} رکورد مرتب‌شده (کامل و با هدر استاندارد)"
        )
    
    # پاک کردن فایل موقت از سرور ربات
    Path(sorted_file).unlink()

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
async def main():
    PROXY_URL = "socks5://127.0.0.1:10808"
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.include_router(router)
    
    logging.info("Extractor Bot starting with SOCKS5 proxy (Port 10808)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())