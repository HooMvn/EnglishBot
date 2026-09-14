from dotenv import load_dotenv
load_dotenv()  # این خط فایل .env را می‌خواند

"""
Bot configuration file - Optimized for Render.com
"""
import os

# خواندن از متغیرهای محیطی رندر (اگر نبود، از مقدار پیش‌فرض استفاده می‌کند)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8877435739:AAHT0hg3Rdlaqt_lZxTPDglvJPa1RDedn0s")

admin_ids_str = os.environ.get("ADMIN_USER_IDS", "6312539820,1299192698")
ADMIN_USER_IDS = [int(x.strip()) for x in admin_ids_str.split(",")]

# مسیر دیتابیس در رندر متفاوت از ویندوز است
DB_PATH = os.environ.get("DB_PATH", "data/database.db")

VERSION = "1.0.0"