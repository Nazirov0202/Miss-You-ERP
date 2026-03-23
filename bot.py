import asyncio
import logging
import subprocess
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config import settings
from app.handlers import start, admin, worker, qc
from app.middlewares import AuthMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def run_migrations():
    """Startup da avtomatik migratsiya — Railway uchun muhim."""
    logger.info("Migratsiya tekshirilmoqda...")
    try:
        # Avval yangi migratsiya bor-yo'qligini tekshirish
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.info("Migratsiya muvaffaqiyatli: %s", result.stdout.strip())
        else:
            logger.warning("Migratsiya xatosi: %s", result.stderr.strip())
            # Agar migratsiya fayllari bo'lmasa, jadvallarni to'g'ridan-to'g'ri yaratamiz
            logger.info("Jadvallar to'g'ridan-to'g'ri yaratilmoqda...")
            _create_tables_directly()
    except Exception as e:
        logger.warning("Alembic ishlamadi: %s — to'g'ridan-to'g'ri yaratamiz", e)
        _create_tables_directly()


def _create_tables_directly():
    """Alembic ishlamasa, SQLAlchemy orqali jadvallarni yaratish."""
    from sqlalchemy import create_engine
    from app.models import Base

    sync_url = settings.database_url_sync
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    logger.info("Jadvallar SQLAlchemy orqali yaratildi.")


async def main():
    # Migratsiyani ishga tushirish
    run_migrations()

    # Redis storage (FSM uchun)
    redis = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis=redis)

    # Bot va Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Middleware
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Routerlarni ulash
    dp.include_routers(
        start.router,
        admin.router,
        worker.router,
        qc.router,
    )

    # Boshlash
    logger.info("✅ Bot ishga tushmoqda...")
    logger.info("📊 DB: %s", settings.database_url_sync.split("@")[-1] if "@" in settings.database_url_sync else "local")
    logger.info("🔴 Redis: %s", settings.redis_url.split("@")[-1] if "@" in settings.redis_url else settings.redis_url)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await redis.close()
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())
