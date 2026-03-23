from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole


async def get_user_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    phone: str | None = None,
    role: UserRole = UserRole.worker,
    worker_type: str | None = None,
) -> User:
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        phone=phone,
        role=role,
        worker_type=worker_type,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_all_workers(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(
            User.role == UserRole.worker,
            User.is_active == True,  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(User.is_active == True).order_by(User.id)  # noqa: E712
    )
    return list(result.scalars().all())


async def update_balance(
    session: AsyncSession, user_id: int, amount: Decimal
) -> None:
    """Balansga pul qo'shish (yoki ayirish, manfiy son bo'lsa)."""
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(balance=User.balance + amount)
    )
    await session.commit()
