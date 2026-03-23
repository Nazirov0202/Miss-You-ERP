from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus


async def generate_order_code(session: AsyncSession) -> str:
    """ZK-2026-001 formatda unikal kod yaratadi."""
    year = datetime.now().year
    prefix = f"ZK-{year}-"
    result = await session.execute(
        select(func.count(Order.id)).where(Order.order_code.like(f"{prefix}%"))
    )
    count = result.scalar() or 0
    return f"{prefix}{count + 1:03d}"


async def create_order(
    session: AsyncSession,
    model_name: str,
    total_qty: int,
    price_per_unit: float,
    created_by: int,
    fabric_type: str | None = None,
    client_name: str | None = None,
    deadline: date | None = None,
) -> Order:
    code = await generate_order_code(session)
    order = Order(
        order_code=code,
        model_name=model_name,
        fabric_type=fabric_type,
        total_qty=total_qty,
        price_per_unit=price_per_unit,
        client_name=client_name,
        deadline=deadline,
        created_by=created_by,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def get_active_orders(session: AsyncSession) -> list[Order]:
    result = await session.execute(
        select(Order)
        .where(Order.status.notin_([OrderStatus.closed, OrderStatus.done]))
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all_orders(session: AsyncSession) -> list[Order]:
    result = await session.execute(
        select(Order).order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())


async def get_order_by_id(session: AsyncSession, order_id: int) -> Order | None:
    return await session.get(Order, order_id)


async def update_completed_qty(
    session: AsyncSession, order_id: int, add_qty: int
) -> Order:
    """Zakazning completed_qty ni oshiradi."""
    order = await get_order_by_id(session, order_id)
    if not order:
        raise ValueError(f"Zakaz topilmadi: {order_id}")

    new_completed = order.completed_qty + add_qty
    if new_completed > order.total_qty:
        raise ValueError(
            f"Jami {order.total_qty} dona, allaqachon {order.completed_qty} tayyor. "
            f"{add_qty} dona qo'shib bo'lmaydi."
        )

    await session.execute(
        update(Order)
        .where(Order.id == order_id)
        .values(completed_qty=new_completed)
    )
    await session.commit()
    await session.refresh(order)
    return order


async def update_order_status(
    session: AsyncSession, order_id: int, status: OrderStatus
) -> None:
    await session.execute(
        update(Order).where(Order.id == order_id).values(status=status)
    )
    await session.commit()
