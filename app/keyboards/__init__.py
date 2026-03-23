from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.models import UserRole


# ── Asosiy menyular (rolga qarab) ────────────────────────


def get_main_menu(role: UserRole) -> InlineKeyboardMarkup:
    """Rolga qarab asosiy menyu qaytaradi."""
    menu_map = {
        UserRole.admin: _admin_menu,
        UserRole.manager: _manager_menu,
        UserRole.sales: _sales_menu,
        UserRole.worker: _worker_menu,
        UserRole.qc: _qc_menu,
        UserRole.warehouse: _warehouse_menu,
    }
    builder_fn = menu_map.get(role, _worker_menu)
    return builder_fn()


def _admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📋 Zakazlar", callback_data="menu:orders"),
        InlineKeyboardButton(text="👥 Xodimlar", callback_data="menu:staff"),
    )
    kb.row(
        InlineKeyboardButton(text="📊 Hisobotlar", callback_data="menu:reports"),
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="menu:settings"),
    )
    kb.row(
        InlineKeyboardButton(text="➕ Yangi zakaz", callback_data="order:create"),
    )
    kb.row(
        InlineKeyboardButton(
            text="👤 Xodim qo'shish", callback_data="staff:register"
        ),
    )
    return kb.as_markup()


def _manager_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📋 Zakazlar", callback_data="menu:orders"),
        InlineKeyboardButton(text="👥 Xodimlar", callback_data="menu:staff"),
    )
    kb.row(
        InlineKeyboardButton(text="📊 Hisobotlar", callback_data="menu:reports"),
    )
    return kb.as_markup()


def _sales_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="➕ Yangi zakaz", callback_data="order:create"),
        InlineKeyboardButton(text="📋 Zakazlar", callback_data="menu:orders"),
    )
    kb.row(
        InlineKeyboardButton(text="📊 Hisobotlar", callback_data="menu:reports"),
    )
    return kb.as_markup()


def _worker_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="🔨 Ish olish", callback_data="work:take"
        ),
        InlineKeyboardButton(
            text="✅ Ish topshirish", callback_data="work:submit"
        ),
    )
    kb.row(
        InlineKeyboardButton(
            text="💰 Mening balansim", callback_data="work:balance"
        ),
        InlineKeyboardButton(
            text="📊 Kunlik hisobot", callback_data="work:daily_report"
        ),
    )
    return kb.as_markup()


def _qc_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="🔍 Tekshirish", callback_data="qc:check"
        ),
        InlineKeyboardButton(
            text="📊 Hisobot", callback_data="qc:report"
        ),
    )
    return kb.as_markup()


def _warehouse_menu() -> InlineKeyboardMarkup:
    """MVP dan keyingi bosqichda kengaytiriladi."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="📦 Ombor (tez kunda)", callback_data="noop"
        ),
    )
    return kb.as_markup()


# ── Yordamchi klaviaturalar ──────────────────────────────


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:main")]
        ]
    )


def confirm_cancel_kb(confirm_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=confirm_data),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
            ]
        ]
    )


def orders_list_kb(orders: list, action_prefix: str = "order:view") -> InlineKeyboardMarkup:
    """Zakazlar ro'yxatini inline tugmalar sifatida ko'rsatadi."""
    kb = InlineKeyboardBuilder()
    for order in orders:
        status_emoji = {
            "opened": "🟡",
            "cutting": "✂️",
            "sewing": "🧵",
            "qc": "🔍",
            "packing": "📦",
            "done": "✅",
            "closed": "🔒",
        }.get(order.status.value, "⬜")
        kb.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {order.order_code} — {order.model_name} ({order.progress_percent}%)",
                callback_data=f"{action_prefix}:{order.id}",
            )
        )
    kb.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:main")
    )
    return kb.as_markup()


def role_select_kb() -> InlineKeyboardMarkup:
    """Rol tanlash uchun (ro'yxatdan o'tkazishda)."""
    kb = InlineKeyboardBuilder()
    roles = [
        ("👔 Admin", "role:admin"),
        ("📊 Boshqaruvchi", "role:manager"),
        ("💼 Savdo", "role:sales"),
        ("🧵 Ishchi", "role:worker"),
        ("🔍 QC nazoratchisi", "role:qc"),
        ("📦 Omborchi", "role:warehouse"),
    ]
    for text, data in roles:
        kb.row(InlineKeyboardButton(text=text, callback_data=data))
    return kb.as_markup()


def worker_type_kb() -> InlineKeyboardMarkup:
    """Ishchi turini tanlash."""
    kb = InlineKeyboardBuilder()
    types = [
        ("✂️ Bichuvchi", "wtype:bichuvchi"),
        ("🧵 Tikuvchi", "wtype:tikuvchi"),
        ("👕 Natelchi", "wtype:natelchi"),
        ("🔥 Dazmolchi", "wtype:dazmolchi"),
        ("🔘 Tugma qadovchi", "wtype:tugma_qadovchi"),
        ("📦 Upakovshik", "wtype:upakovshik"),
    ]
    for text, data in types:
        kb.row(InlineKeyboardButton(text=text, callback_data=data))
    return kb.as_markup()
