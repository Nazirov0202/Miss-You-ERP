from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import (
    get_main_menu,
    role_select_kb,
    worker_type_kb,
)
from app.models import User, UserRole
from app.services.user_service import create_user
from app.states import RegistrationStates

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    user: User | None,
    session: AsyncSession,
):
    if user:
        role_name = {
            UserRole.admin: "Rahbar",
            UserRole.manager: "Boshqaruvchi",
            UserRole.sales: "Savdo",
            UserRole.worker: f"Ishchi ({user.worker_type or ''})",
            UserRole.qc: "QC nazoratchisi",
            UserRole.warehouse: "Omborchi",
        }.get(user.role, user.role.value)

        await message.answer(
            f"👋 Xush kelibsiz, {user.full_name}!\n"
            f"📌 Rolingiz: {role_name}\n\n"
            f"Quyidagi menyudan tanlang:",
            reply_markup=get_main_menu(user.role),
        )
        return

    # Yangi foydalanuvchi — ro'yxatdan o'tkazish
    await message.answer(
        "👋 Telegram ERP tizimiga xush kelibsiz!\n\n"
        "Ro'yxatdan o'tish uchun ismingizni kiriting\n"
        "(masalan: Abdullayev Sardor):"
    )
    await state.set_state(RegistrationStates.waiting_full_name)


@router.message(RegistrationStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("❌ Ism juda qisqa. Kamida 3 ta harf kiriting:")
        return
    await state.update_data(full_name=name)
    await message.answer(
        f"✅ Ism: {name}\n\n"
        "📱 Telefon raqamingizni kiriting\n"
        "(masalan: +998901234567):"
    )
    await state.set_state(RegistrationStates.waiting_phone)


@router.message(RegistrationStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    # Oddiy validatsiya
    cleaned = phone.replace("+", "").replace(" ", "").replace("-", "")
    if not cleaned.isdigit() or len(cleaned) < 9:
        await message.answer("❌ Noto'g'ri format. Qaytadan kiriting (masalan: +998901234567):")
        return
    await state.update_data(phone=phone)
    await message.answer(
        "👤 Rolingizni tanlang:",
        reply_markup=role_select_kb(),
    )
    await state.set_state(RegistrationStates.waiting_role)


@router.callback_query(RegistrationStates.waiting_role, F.data.startswith("role:"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role_str = callback.data.split(":")[1]
    role = UserRole(role_str)
    await state.update_data(role=role)

    if role == UserRole.worker:
        await callback.message.edit_text(
            "🔧 Ishchi turingizni tanlang:",
            reply_markup=worker_type_kb(),
        )
        await state.set_state(RegistrationStates.waiting_worker_type)
    else:
        # Ishchi emas — to'g'ridan-to'g'ri yaratish
        await _finish_registration(callback, state)

    await callback.answer()


@router.callback_query(
    RegistrationStates.waiting_worker_type, F.data.startswith("wtype:")
)
async def process_worker_type(callback: CallbackQuery, state: FSMContext):
    wtype = callback.data.split(":")[1]
    await state.update_data(worker_type=wtype)
    await _finish_registration(callback, state)
    await callback.answer()


async def _finish_registration(callback: CallbackQuery, state: FSMContext):
    """Ro'yxatdan o'tishni yakunlash."""
    data = await state.get_data()
    session: AsyncSession = callback.message.bot.get("session_factory")  # type: ignore

    # Yangi sessiya ochish (middleware sessiyasi callback da eskirgan bo'lishi mumkin)
    from app.database import async_session as sf

    async with sf() as session:
        user = await create_user(
            session=session,
            telegram_id=callback.from_user.id,
            full_name=data["full_name"],
            phone=data.get("phone"),
            role=data["role"],
            worker_type=data.get("worker_type"),
        )

    role_name = {
        UserRole.admin: "Rahbar",
        UserRole.manager: "Boshqaruvchi",
        UserRole.sales: "Savdo",
        UserRole.worker: f"Ishchi ({user.worker_type or ''})",
        UserRole.qc: "QC nazoratchisi",
        UserRole.warehouse: "Omborchi",
    }.get(user.role, user.role.value)

    await callback.message.edit_text(
        f"✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
        f"👤 Ism: {user.full_name}\n"
        f"📱 Telefon: {user.phone}\n"
        f"📌 Rol: {role_name}\n\n"
        f"Quyidagi menyudan tanlang:",
        reply_markup=get_main_menu(user.role),
    )
    await state.clear()


# ── Bosh menyuga qaytish ─────────────────────────────────


@router.callback_query(F.data == "menu:main")
async def back_to_main(callback: CallbackQuery, user: User, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        f"🏠 Bosh menyu — {user.full_name}",
        reply_markup=get_main_menu(user.role),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, user: User, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Bekor qilindi.\n\n🏠 Bosh menyu:",
        reply_markup=get_main_menu(user.role),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer("Bu funksiya tez kunda qo'shiladi! ⏳", show_alert=True)
