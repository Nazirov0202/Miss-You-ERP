from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import back_to_menu_kb, confirm_cancel_kb, orders_list_kb
from app.models import User, UserRole
from app.services import order_service
from app.services.qc_service import create_qc_result, get_qc_summary_for_order
from app.states import QCCheckStates
from app.utils.helpers import role_required

router = Router(name="qc")


# ── Tekshirish boshlash ──────────────────────────────────


@router.callback_query(F.data == "qc:check")
@role_required(UserRole.qc, UserRole.admin)
async def qc_start_check(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    orders = await order_service.get_active_orders(session)
    if not orders:
        await callback.message.edit_text(
            "🔍 Tekshirish uchun zakaz yo'q.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🔍 Tekshirish — zakazni tanlang:",
        reply_markup=orders_list_kb(orders, action_prefix="qc:select"),
    )
    await state.set_state(QCCheckStates.select_order)
    await callback.answer()


@router.callback_query(QCCheckStates.select_order, F.data.startswith("qc:select:"))
async def qc_select_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    order_id = int(callback.data.split(":")[2])
    order = await order_service.get_order_by_id(session, order_id)
    if not order:
        await callback.answer("Zakaz topilmadi", show_alert=True)
        return

    qc_sum = await get_qc_summary_for_order(session, order_id)

    await state.update_data(order_id=order_id, order_code=order.order_code)
    await callback.message.edit_text(
        f"🔍 Zakaz: {order.order_code} — {order.model_name}\n"
        f"📦 Jami: {order.total_qty} | ✅ Tayyor: {order.completed_qty}\n"
        f"🔍 Tekshirilgan: ✅ {qc_sum['total_accepted']} | ❌ {qc_sum['total_rejected']}\n\n"
        f"Qabul qilingan dona sonini kiriting:"
    )
    await state.set_state(QCCheckStates.enter_accepted_qty)
    await callback.answer()


@router.message(QCCheckStates.enter_accepted_qty)
async def qc_accepted_qty(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ 0 yoki undan katta son kiriting:")
        return

    await state.update_data(accepted_qty=qty)
    await message.answer("❌ Rad etilgan (brak) dona sonini kiriting (0 bo'lsa 0 yozing):")
    await state.set_state(QCCheckStates.enter_rejected_qty)


@router.message(QCCheckStates.enter_rejected_qty)
async def qc_rejected_qty(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ 0 yoki undan katta son kiriting:")
        return

    await state.update_data(rejected_qty=qty)

    if qty > 0:
        await message.answer("📝 Brak sababini yozing:")
        await state.set_state(QCCheckStates.enter_reject_reason)
    else:
        await state.update_data(reject_reason=None)
        data = await state.get_data()
        await message.answer(
            f"🔍 QC natijasi:\n"
            f"📋 Zakaz: {data['order_code']}\n"
            f"✅ Qabul: {data['accepted_qty']} dona\n"
            f"❌ Brak: 0 dona\n\n"
            f"Tasdiqlaysizmi?",
            reply_markup=confirm_cancel_kb("qc:confirm"),
        )
        await state.set_state(QCCheckStates.confirm)


@router.message(QCCheckStates.enter_reject_reason)
async def qc_reject_reason(message: Message, state: FSMContext):
    await state.update_data(reject_reason=message.text.strip())
    data = await state.get_data()

    await message.answer(
        f"🔍 QC natijasi:\n"
        f"📋 Zakaz: {data['order_code']}\n"
        f"✅ Qabul: {data['accepted_qty']} dona\n"
        f"❌ Brak: {data['rejected_qty']} dona\n"
        f"📝 Sabab: {data['reject_reason']}\n\n"
        f"Tasdiqlaysizmi?",
        reply_markup=confirm_cancel_kb("qc:confirm"),
    )
    await state.set_state(QCCheckStates.confirm)


@router.callback_query(QCCheckStates.confirm, F.data == "qc:confirm")
async def qc_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    session: AsyncSession,
):
    data = await state.get_data()

    qc = await create_qc_result(
        session=session,
        order_id=data["order_id"],
        inspector_id=user.id,
        accepted_qty=data["accepted_qty"],
        rejected_qty=data.get("rejected_qty", 0),
        reject_reason=data.get("reject_reason"),
    )

    await callback.message.edit_text(
        f"✅ QC natijasi saqlandi!\n\n"
        f"📋 Zakaz: {data['order_code']}\n"
        f"✅ Qabul: {qc.accepted_qty}\n"
        f"❌ Brak: {qc.rejected_qty}",
        reply_markup=back_to_menu_kb(),
    )
    await state.clear()
    await callback.answer()


# ── QC hisobot ───────────────────────────────────────────


@router.callback_query(F.data == "qc:report")
@role_required(UserRole.qc, UserRole.admin)
async def qc_report(callback: CallbackQuery, session: AsyncSession, **kwargs):
    orders = await order_service.get_active_orders(session)

    if not orders:
        await callback.message.edit_text(
            "📊 Hisobot — hozircha zakaz yo'q.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    lines = [f"📊 QC Hisobot — {datetime.now().strftime('%d.%m.%Y')}\n"]

    for order in orders:
        qc_sum = await get_qc_summary_for_order(session, order.id)
        lines.append(
            f"📋 {order.order_code}: "
            f"✅ {qc_sum['total_accepted']} | "
            f"❌ {qc_sum['total_rejected']} | "
            f"🔍 {qc_sum['check_count']} marta"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
