import functools
from typing import Callable

from aiogram.types import CallbackQuery

from app.models import UserRole


def role_required(*allowed_roles: UserRole):
    """
    Dekorator: faqat ruxsat berilgan rollarga kirish.
    
    Foydalanish:
        @router.callback_query(F.data == "menu:orders")
        @role_required(UserRole.admin, UserRole.manager)
        async def menu_orders(callback, session, **kwargs):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # callback yoki message ni topish
            event = args[0] if args else None
            user = kwargs.get("user")

            if user is None:
                if isinstance(event, CallbackQuery):
                    await event.answer(
                        "⚠️ Tizimga kirmagansiz.", show_alert=True
                    )
                return

            if user.role not in allowed_roles:
                if isinstance(event, CallbackQuery):
                    await event.answer(
                        "🚫 Sizda bu amal uchun ruxsat yo'q.",
                        show_alert=True,
                    )
                return

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def format_money(amount) -> str:
    """Pul summasini formatlash: 1,234,567 so'm."""
    return f"{float(amount):,.0f} so'm"


def format_progress_bar(percent: float, width: int = 10) -> str:
    """Vizual progress bar: ████░░░░░░ 40%"""
    filled = int(width * percent / 100)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {percent:.0f}%"


def truncate(text: str, max_len: int = 50) -> str:
    """Matnni qisqartirish."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
