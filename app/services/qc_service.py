from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import QCResult


async def create_qc_result(
    session: AsyncSession,
    order_id: int,
    inspector_id: int,
    accepted_qty: int,
    rejected_qty: int = 0,
    reject_reason: str | None = None,
) -> QCResult:
    qc = QCResult(
        order_id=order_id,
        inspector_id=inspector_id,
        accepted_qty=accepted_qty,
        rejected_qty=rejected_qty,
        reject_reason=reject_reason,
    )
    session.add(qc)
    await session.commit()
    await session.refresh(qc)
    return qc


async def get_qc_summary_for_order(
    session: AsyncSession, order_id: int
) -> dict:
    """Bitta zakaz bo'yicha QC xulosasi."""
    result = await session.execute(
        select(
            func.sum(QCResult.accepted_qty).label("total_accepted"),
            func.sum(QCResult.rejected_qty).label("total_rejected"),
            func.count(QCResult.id).label("check_count"),
        ).where(QCResult.order_id == order_id)
    )
    row = result.one()
    return {
        "total_accepted": row.total_accepted or 0,
        "total_rejected": row.total_rejected or 0,
        "check_count": row.check_count or 0,
    }


async def get_qc_history(
    session: AsyncSession, order_id: int
) -> list[QCResult]:
    result = await session.execute(
        select(QCResult)
        .options(joinedload(QCResult.inspector))
        .where(QCResult.order_id == order_id)
        .order_by(QCResult.created_at.desc())
    )
    return list(result.scalars().all())
