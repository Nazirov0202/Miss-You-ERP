from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Order, Transaction, TransactionType, User
from app.services import order_service, user_service


async def submit_work(
    session: AsyncSession,
    user_id: int,
    order_id: int,
    qty: int,
    note: str | None = None,
) -> Transaction:
    """
    Tikuvchi ish topshiradi:
    1. Zakazdagi completed_qty oshadi
    2. Xodim balansiga pul tushadi (qty × price_per_unit)
    3. Tranzaksiya yoziladi
    """
    order = await order_service.get_order_by_id(session, order_id)
    if not order:
        raise ValueError("Zakaz topilmadi")

    if qty <= 0:
        raise ValueError("Dona soni 0 dan katta bo'lishi kerak")

    remaining = order.total_qty - order.completed_qty
    if qty > remaining:
        raise ValueError(
            f"Zakazda faqat {remaining} dona qolgan. {qty} dona topshirib bo'lmaydi."
        )

    # Summani hisoblash
    amount = Decimal(str(qty)) * order.price_per_unit

    # Tranzaksiya yaratish
    txn = Transaction(
        user_id=user_id,
        order_id=order_id,
        qty=qty,
        amount=amount,
        type=TransactionType.work,
        note=note,
    )
    session.add(txn)

    # Zakaz completed_qty yangilash
    await order_service.update_completed_qty(session, order_id, qty)

    # Xodim balansini yangilash
    await user_service.update_balance(session, user_id, amount)

    await session.commit()
    await session.refresh(txn)
    return txn


async def get_daily_report(
    session: AsyncSession, user_id: int
) -> dict:
    """Xodimning bugungi kunlik hisoboti."""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    result = await session.execute(
        select(Transaction)
        .options(joinedload(Transaction.order))
        .where(
            Transaction.user_id == user_id,
            Transaction.created_at >= today_start,
            Transaction.created_at < today_end,
        )
        .order_by(Transaction.created_at)
    )
    transactions = list(result.scalars().all())

    total_qty = sum(t.qty for t in transactions)
    total_amount = sum(t.amount for t in transactions)

    return {
        "transactions": transactions,
        "total_qty": total_qty,
        "total_amount": total_amount,
        "count": len(transactions),
    }


async def get_admin_daily_summary(session: AsyncSession) -> dict:
    """Admin uchun bugungi umumiy hisobot."""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Bugungi barcha tranzaksiyalar
    result = await session.execute(
        select(
            Transaction.user_id,
            User.full_name,
            func.sum(Transaction.qty).label("total_qty"),
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("tx_count"),
        )
        .join(User, Transaction.user_id == User.id)
        .where(
            Transaction.created_at >= today_start,
            Transaction.created_at < today_end,
            Transaction.type == TransactionType.work,
        )
        .group_by(Transaction.user_id, User.full_name)
        .order_by(func.sum(Transaction.qty).desc())
    )
    rows = result.all()

    total_qty = sum(r.total_qty for r in rows)
    total_amount = sum(r.total_amount for r in rows)

    return {
        "workers": rows,
        "total_qty": total_qty,
        "total_amount": total_amount,
        "worker_count": len(rows),
    }
