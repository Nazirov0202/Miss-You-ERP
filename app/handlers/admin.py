from datetime import datetime

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
from app.models import Order, OrderStatus, User, UserRole
from app.services import order_service, transaction_service, user_service
from app.services.qc_service import get_qc_summary_for_order
from app.states import OrderCreateStates
from app.utils.helpers import role_required

router = Router(name="admin")


# ── Zakazlar menyusi ─────────────────────────────────────


@router.callback_query(F.data == "menu:orders")
@role_required(UserRole.admin, UserRole.manager, UserRole.sales)
async def menu_orders(callback: CallbackQuery, session: AsyncSession, **kwargs):
    orders = await order_service.get_all_orders(session)
    if not orders:
        await callback.message.edit_text(
            "📋 Hozircha hech qanday zakaz yo'q.",
            reply_markup=back_to_menu_kb(),
        )
    else:
        await callback.message.edit_text(
            f"📋 Barcha zakazlar ({len(orders)} ta):",
            reply_markup=orders_list_kb(orders),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("order:view:"))
async def view_order(callback: CallbackQuery, session: AsyncSession, **kwargs):
    order_id = int(callback.data.split(":")[2])
    order = await order_service.get_order_by_id(session, order_id)
    if not order:
        await callback.answer("Zakaz topilmadi", show_alert=True)
        return

    qc = await get_qc_summary_for_order(session, order_id)

    status_map = {
        "opened": "🟡 Ochildi",
        "cutting": "✂️ Bichuvda",
        "sewing": "🧵 Tikuvda",
        "qc": "🔍 QC da",
        "packing": "📦 Upakovkada",
        "done": "✅ Tayyor",
        "closed": "🔒 Yopildi",
    }

    deadline_str = order.deadline.strftime("%d.%m.%Y") if order.deadline else "—"

    text = (
        f"📋 Zakaz: {order.order_code}\n"
        f"{'─' * 30}\n"
        f"📌 Model: {order.model_name}\n"
        f"🧶 Mato: {order.fabric_type or '—'}\n"
        f"👤 Mijoz: {order.client_name or '—'}\n"
        f"{'─' * 30}\n"
        f"📊 Holat: {status_map.get(order.status.value, order.status.value)}\n"
        f"📦 Jami: {order.total_qty} dona\n"
        f"✅ Tayyor: {order.completed_qty} dona ({order.progress_percent}%)\n"
        f"⏳ Qoldi: {order.remaining_qty} dona\n"
        f"💰 Narx: {order.price_per_unit:,.0f} so'm/dona\n"
        f"📅 Muddat: {deadline_str}\n"
        f"{'─' * 30}\n"
        f"🔍 QC: ✅ {qc['total_accepted']} qabul / ❌ {qc['total_rejected']} brak\n"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    kb = InlineKeyboardBuilder()
    if order.status not in (OrderStatus.done, OrderStatus.closed):
        kb.row(
            InlineKeyboardButton(
                text="🔄 Holatni o'zgartirish",
                callback_data=f"order:status:{order.id}",
            )
        )
    kb.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:main"))

    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()


# ── Zakaz holati o'zgartirish ─────────────────────────────


@router.callback_query(F.data.startswith("order:status:"))
@role_required(UserRole.admin, UserRole.manager)
async def change_order_status(callback: CallbackQuery, session: AsyncSession, **kwargs):
    order_id = int(callback.data.split(":")[2])

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    kb = InlineKeyboardBuilder()
    statuses = [
        ("🟡 Ochildi", OrderStatus.opened),
        ("✂️ Bichuvda", OrderStatus.cutting),
        ("🧵 Tikuvda", OrderStatus.sewing),
        ("🔍 QC da", OrderStatus.qc),
        ("📦 Upakovka", OrderStatus.packing),
        ("✅ Tayyor", OrderStatus.done),
        ("🔒 Yopish", OrderStatus.closed),
    ]
    for text, status in statuses:
        kb.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"order:setstatus:{order_id}:{status.value}",
            )
        )
    kb.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"order:view:{order_id}"))

    await callback.message.edit_text("📊 Yangi holatni tanlang:", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("order:setstatus:"))
@role_required(UserRole.admin, UserRole.manager)
async def set_order_status(callback: CallbackQuery, session: AsyncSession, **kwargs):
    parts = callback.data.split(":")
    order_id = int(parts[2])
    new_status = OrderStatus(parts[3])

    await order_service.update_order_status(session, order_id, new_status)
    await callback.answer(f"✅ Holat o'zgartirildi: {new_status.value}", show_alert=True)

    # Orqaga qaytish
    order = await order_service.get_order_by_id(session, order_id)
    await callback.message.edit_text(
        f"✅ {order.order_code} zakaz holati: {new_status.value}",
        reply_markup=back_to_menu_kb(),
    )


# ── Yangi zakaz ochish ──────────────────────────────────


@router.callback_query(F.data == "order:create")
@role_required(UserRole.admin, UserRole.sales)
async def start_create_order(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.message.edit_text(
        "📋 Yangi zakaz ochish\n\n"
        "Model nomini kiriting (masalan: Ko'ylak-A1):"
    )
    await state.set_state(OrderCreateStates.waiting_model_name)
    await callback.answer()


@router.message(OrderCreateStates.waiting_model_name)
async def order_model_name(message: Message, state: FSMContext):
    await state.update_data(model_name=message.text.strip())
    await message.answer("🧶 Mato turini kiriting (yoki '-' bosing):")
    await state.set_state(OrderCreateStates.waiting_fabric_type)


@router.message(OrderCreateStates.waiting_fabric_type)
async def order_fabric_type(message: Message, state: FSMContext):
    fabric = message.text.strip()
    await state.update_data(fabric_type=None if fabric == "-" else fabric)
    await message.answer("📦 Umumiy dona sonini kiriting:")
    await state.set_state(OrderCreateStates.waiting_total_qty)


@router.message(OrderCreateStates.waiting_total_qty)
async def order_total_qty(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Musbat butun son kiriting:")
        return
    await state.update_data(total_qty=qty)
    await message.answer("💰 Donabay narxni kiriting (so'm):")
    await state.set_state(OrderCreateStates.waiting_price_per_unit)


@router.message(OrderCreateStates.waiting_price_per_unit)
async def order_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(",", "").replace(" ", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Musbat son kiriting:")
        return
    await state.update_data(price_per_unit=price)
    await message.answer("👤 Mijoz nomini kiriting (yoki '-' bosing):")
    await state.set_state(OrderCreateStates.waiting_client_name)


@router.message(OrderCreateStates.waiting_client_name)
async def order_client_name(message: Message, state: FSMContext):
    client = message.text.strip()
    await state.update_data(client_name=None if client == "-" else client)
    await message.answer(
        "📅 Muddat kiriting (DD.MM.YYYY formatda, masalan: 15.04.2026)\n"
        "Yoki '-' bosing:"
    )
    await state.set_state(OrderCreateStates.waiting_deadline)


@router.message(OrderCreateStates.waiting_deadline)
async def order_deadline(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "-":
        await state.update_data(deadline=None)
    else:
        try:
            deadline = datetime.strptime(text, "%d.%m.%Y").date()
            await state.update_data(deadline=deadline)
        except ValueError:
            await message.answer("❌ Noto'g'ri format. DD.MM.YYYY kiriting yoki '-':")
            return

    data = await state.get_data()
    deadline_str = data["deadline"].strftime("%d.%m.%Y") if data.get("deadline") else "—"

    await message.answer(
        f"📋 Zakaz ma'lumotlari:\n"
        f"{'─' * 28}\n"
        f"📌 Model: {data['model_name']}\n"
        f"🧶 Mato: {data.get('fabric_type') or '—'}\n"
        f"📦 Soni: {data['total_qty']} dona\n"
        f"💰 Narx: {data['price_per_unit']:,.0f} so'm/dona\n"
        f"👤 Mijoz: {data.get('client_name') or '—'}\n"
        f"📅 Muddat: {deadline_str}\n\n"
        f"Tasdiqlaysizmi?",
        reply_markup=confirm_cancel_kb("order:confirm_create"),
    )
    await state.set_state(OrderCreateStates.confirm)


@router.callback_query(OrderCreateStates.confirm, F.data == "order:confirm_create")
async def confirm_create_order(
    callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession
):
    data = await state.get_data()

    order = await order_service.create_order(
        session=session,
        model_name=data["model_name"],
        total_qty=data["total_qty"],
        price_per_unit=data["price_per_unit"],
        created_by=user.id,
        fabric_type=data.get("fabric_type"),
        client_name=data.get("client_name"),
        deadline=data.get("deadline"),
    )

    await callback.message.edit_text(
        f"✅ Zakaz muvaffaqiyatli ochildi!\n\n"
        f"🔑 Kod: {order.order_code}\n"
        f"📌 Model: {order.model_name}\n"
        f"📦 Soni: {order.total_qty} dona",
        reply_markup=back_to_menu_kb(),
    )
    await state.clear()
    await callback.answer()


# ── Xodimlar ro'yxati ───────────────────────────────────


@router.callback_query(F.data == "menu:staff")
@role_required(UserRole.admin, UserRole.manager)
async def menu_staff(callback: CallbackQuery, session: AsyncSession, **kwargs):
    users = await user_service.get_all_users(session)
    if not users:
        await callback.message.edit_text(
            "👥 Xodimlar topilmadi.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    lines = ["👥 Xodimlar ro'yxati:\n"]
    for u in users:
        role_emoji = {
            "admin": "👔", "manager": "📊", "sales": "💼",
            "worker": "🧵", "qc": "🔍", "warehouse": "📦",
        }.get(u.role.value, "👤")
        wtype = f" ({u.worker_type})" if u.worker_type else ""
        lines.append(
            f"{role_emoji} {u.full_name}{wtype}\n"
            f"   💰 {u.balance:,.0f} so'm | 📱 {u.phone or '—'}"
        )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="👤 Xodim qo'shish", callback_data="staff:register"),
    )
    kb.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:main"),
    )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "staff:register")
@role_required(UserRole.admin)
async def staff_register_info(callback: CallbackQuery, **kwargs):
    await callback.message.edit_text(
        "👤 Yangi xodim qo'shish:\n\n"
        "Xodim o'zi /start buyrug'ini botga yuborishi kerak.\n"
        "Bot avtomatik ro'yxatdan o'tkazadi.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


# ── Hisobotlar ───────────────────────────────────────────


@router.callback_query(F.data == "menu:reports")
@role_required(UserRole.admin, UserRole.manager, UserRole.sales)
async def menu_reports(callback: CallbackQuery, session: AsyncSession, **kwargs):
    report = await transaction_service.get_admin_daily_summary(session)

    if report["worker_count"] == 0:
        await callback.message.edit_text(
            "📊 Bugun hali hech kim ish topshirmagan.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    lines = [
        f"📊 Kunlik hisobot — {datetime.now().strftime('%d.%m.%Y')}\n",
        f"👷 Ishchi soni: {report['worker_count']}",
        f"📦 Jami dona: {report['total_qty']}",
        f"💰 Jami summa: {report['total_amount']:,.0f} so'm\n",
        "─" * 28,
    ]

    for row in report["workers"]:
        lines.append(
            f"👤 {row.full_name}: {row.total_qty} dona "
            f"({row.total_amount:,.0f} so'm)"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


# ── Sozlamalar (placeholder) ─────────────────────────────


@router.callback_query(F.data == "menu:settings")
@role_required(UserRole.admin)
async def menu_settings(callback: CallbackQuery, **kwargs):
    await callback.message.edit_text(
        "⚙️ Sozlamalar — tez kunda qo'shiladi.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
