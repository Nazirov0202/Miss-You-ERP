from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.database import async_session
from app.services.user_service import get_user_by_telegram_id


class AuthMiddleware(BaseMiddleware):
    """
    Har bir xabar/callback da:
    1. DB sessiya ochadi
    2. Telegram ID bo'yicha userni topadi
    3. data["session"] va data["user"] ga qo'yadi

    Ro'yxatdan o'tmagan foydalanuvchilarga faqat /start ruxsat beriladi.
    """

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["session"] = session

            telegram_id = event.from_user.id if event.from_user else None
            if telegram_id:
                user = await get_user_by_telegram_id(session, telegram_id)
                data["user"] = user
            else:
                data["user"] = None

            # Ro'yxatdan o'tmagan foydalanuvchi — faqat /start ga ruxsat
            if data["user"] is None:
                if isinstance(event, Message) and event.text and event.text.startswith("/start"):
                    return await handler(event, data)
                if isinstance(event, CallbackQuery):
                    cb_data = event.data or ""
                    # Ro'yxatdan o'tish jarayonidagi callbacklarga ruxsat
                    if cb_data.startswith("role:") or cb_data.startswith("wtype:"):
                        return await handler(event, data)

                if isinstance(event, Message):
                    # FSM state da bo'lsa (registration) — o'tkazamiz
                    state = data.get("state")
                    if state:
                        current_state = await state.get_state()
                        if current_state and "Registration" in current_state:
                            return await handler(event, data)

                    await event.answer(
                        "⚠️ Siz tizimda ro'yxatdan o'tmagansiz.\n"
                        "/start buyrug'ini yuboring."
                    )
                    return
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Siz tizimda ro'yxatdan o'tmagansiz.", show_alert=True
                    )
                    return

            return await handler(event, data)
