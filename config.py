"""
Bot configuration file - 100% Secure (No hardcoded tokens)
"""
import os

# خواندن توکن از متغیرهای محیطی (Render یا فایل .env لوکال)
# اگر تنظیم نشده باشد، برنامه با خطا متوقف می‌شود تا فراموش نکنید آن را اضافه کنید
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set! Please add it to Render Environment Variables or your local .env file.")

# خواندن آیدی ادمین‌ها
admin_ids_str = os.environ.get("ADMIN_USER_IDS", "6312539820,1299192698")
ADMIN_USER_IDS = [int(x.strip()) for x in admin_ids_str.split(",")]

# مسیر دیتابیس
DB_PATH = os.environ.get("DB_PATH", "data/database.db")

VERSION = "1.0.0"