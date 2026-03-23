from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import (
    back_to_menu_kb,
    confirm_cancel_kb,
    get_main_menu,
    orders_list_kb,
)
from app.models import User, UserRole
from app.services import order_service, transaction_service
from app.states import WorkSubmitStates
from app.utils.helpers import role_required

router = Router(name="worker")


# ── Ish olish ────────────────────────────────────────────


@router.callback_query(F.data == "work:take")
@role_required(UserRole.worker)
async def work_take(callback: CallbackQuery, session: AsyncSession, **kwargs):
    orders = await order_service.get_active_orders(session)
    if not orders:
        await callback.message.edit_text(
            "📋 Hozircha ochiq zakaz yo'q.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🔨 Mavjud zakazlar — tanlang:",
        reply_markup=orders_list_kb(orders, action_prefix="work:info"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("work:info:"))
async def work_order_info(callback: CallbackQuery, session: AsyncSession, **kwargs):
    order_id = int(callback.data.split(":")[2])
    order = await order_service.get_order_by_id(session, order_id)
    if not order:
        await callback.answer("Zakaz topilmadi", show_alert=True)
        return

    text = (
        f"📋 {order.order_code} — {order.model_name}\n"
        f"📦 Jami: {order.total_qty} | ✅ Tayyor: {order.completed_qty} | "
        f"⏳ Qoldi: {order.remaining_qty}\n"
        f"💰 Narx: {order.price_per_unit:,.0f} so'm/dona"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    kb = InlineKeyboardBuilder()
    if order.remaining_qty > 0:
        kb.row(
            InlineKeyboardButton(
                text="✅ Ish topshirish",
                callback_data=f"work:start_submit:{order.id}",
            )
        )
    kb.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="work:take"))

    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()


# ── Ish topshirish ───────────────────────────────────────


@router.callback_query(F.data == "work:submit")
@role_required(UserRole.worker)
async def work_submit_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    orders = await order_service.get_active_orders(session)
    if not orders:
        await callback.message.edit_text(
            "📋 Hozircha ochiq zakaz yo'q.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Ish topshirish — zakazni tanlang:",
        reply_markup=orders_list_kb(orders, action_prefix="work:start_submit"),
    )
    await state.set_state(WorkSubmitStates.select_order)
    await callback.answer()


@router.callback_query(F.data.startswith("work:start_submit:"))
async def work_select_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    order_id = int(callback.data.split(":")[2])
    order = await order_service.get_order_by_id(session, order_id)
    if not order:
        await callback.answer("Zakaz topilmadi", show_alert=True)
        return

    await state.update_data(order_id=order_id, order_code=order.order_code)
    await callback.message.edit_text(
        f"📋 Zakaz: {order.order_code} — {order.model_name}\n"
        f"⏳ Qolgan: {order.remaining_qty} dona\n\n"
        f"Necha dona topshirasiz? Sonni kiriting:"
    )
    await state.set_state(WorkSubmitStates.enter_qty)
    await callback.answer()


@router.message(WorkSubmitStates.enter_qty)
async def work_enter_qty(message: Message, state: FSMContext, session: AsyncSession):
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Musbat butun son kiriting:")
        return

    data = await state.get_data()
    order = await order_service.get_order_by_id(session, data["order_id"])

    if qty > order.remaining_qty:
        await message.answer(
            f"❌ Zakazda faqat {order.remaining_qty} dona qolgan.\n"
            f"Kamroq son kiriting:"
        )
        return

    amount = qty * float(order.price_per_unit)
    await state.update_data(qty=qty, amount=amount)

    await message.answer(
        f"📋 Zakaz: {order.order_code}\n"
        f"📦 Dona: {qty}\n"
        f"💰 Summa: {amount:,.0f} so'm\n\n"
        f"Tasdiqlaysizmi?",
        reply_markup=confirm_cancel_kb("work:confirm_submit"),
    )
    await state.set_state(WorkSubmitStates.confirm)


@router.callback_query(WorkSubmitStates.confirm, F.data == "work:confirm_submit")
async def work_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    session: AsyncSession,
):
    data = await state.get_data()

    try:
        txn = await transaction_service.submit_work(
            session=session,
            user_id=user.id,
            order_id=data["order_id"],
            qty=data["qty"],
        )
    except ValueError as e:
        await callback.message.edit_text(
            f"❌ Xatolik: {e}",
            reply_markup=back_to_menu_kb(),
        )
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text(
        f"✅ Ish muvaffaqiyatli topshirildi!\n\n"
        f"📋 Zakaz: {data['order_code']}\n"
        f"📦 Dona: {data['qty']}\n"
        f"💰 Hisoblandi: {txn.amount:,.0f} so'm\n"
        f"💰 Joriy balans: {user.balance + txn.amount:,.0f} so'm",
        reply_markup=get_main_menu(user.role),
    )
    await state.clear()
    await callback.answer()


# ── Balans ko'rish ───────────────────────────────────────


@router.callback_query(F.data == "work:balance")
@role_required(UserRole.worker)
async def work_balance(callback: CallbackQuery, user: User, session: AsyncSession, **kwargs):
    # Freshdan o'qish
    from app.services.user_service import get_user_by_id
    fresh_user = await get_user_by_id(session, user.id)

    await callback.message.edit_text(
        f"💰 Mening balansim\n"
        f"{'─' * 28}\n"
        f"👤 {fresh_user.full_name}\n"
        f"💰 Joriy balans: {fresh_user.balance:,.0f} so'm",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


# ── Kunlik hisobot ───────────────────────────────────────


@router.callback_query(F.data == "work:daily_report")
@role_required(UserRole.worker)
async def work_daily_report(callback: CallbackQuery, user: User, session: AsyncSession, **kwargs):
    report = await transaction_service.get_daily_report(session, user.id)

    if report["count"] == 0:
        await callback.message.edit_text(
            "📊 Bugun hali ish topshirmagansiz.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    from datetime import datetime
    lines = [
        f"📊 Kunlik hisobot — {datetime.now().strftime('%d.%m.%Y')}\n",
        f"👤 {user.full_name}\n",
    ]

    for txn in report["transactions"]:
        order_code = txn.order.order_code if txn.order else "—"
        lines.append(f"  📋 {order_code}: {txn.qty} dona → {txn.amount:,.0f} so'm")

    lines.append(f"\n{'─' * 28}")
    lines.append(f"📦 Jami: {report['total_qty']} dona")
    lines.append(f"💰 Jami: {report['total_amount']:,.0f} so'm")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
