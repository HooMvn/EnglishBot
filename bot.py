"""
Main bot file - Entry point for Render.com (Webhook Mode)
"""
import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN, DB_PATH
from database import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
db = Database()

async def on_startup():
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8080")
    webhook_url = f"{render_url}/webhook/{BOT_TOKEN}"
    logger.info(f"Setting webhook to: {webhook_url}")
    await bot.set_webhook(webhook_url)
    logger.info("✅ Webhook set successfully!")

async def main():
    try:
        # ساخت پوشه دیتابیس در رندر
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        logger.info("Initializing database...")
        await db.init_db()
        await db.setup_sample_data()
        logger.info("✅ Database initialized successfully")

        # ایمپورت و ثبت روترها
        from handlers import (
            access, start, navigation, audio, video, media,
            exercises, extra_exercises, resources, progress,
        )
        dp.include_router(access.router)
        dp.include_router(start.router)
        dp.include_router(navigation.router)
        dp.include_router(audio.router)
        dp.include_router(video.router)
        dp.include_router(media.router)
        dp.include_router(exercises.router)
        dp.include_router(extra_exercises.router)
        dp.include_router(resources.router)
        dp.include_router(progress.router)

        # راه‌اندازی سرور وب برای Webhook
        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_requests_handler.register(app, path=f"/webhook/{BOT_TOKEN}")
        setup_application(app, dp, bot=bot)

        await on_startup()

        port = int(os.environ.get("PORT", 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=port)
        
        logger.info(f"🚀 Bot is running on port {port}...")
        await site.start()
        
        # نگه داشتن برنامه در حالت اجرا
        await asyncio.Future()

    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())