from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Yangi xodim ro'yxatdan o'tish."""
    waiting_full_name = State()
    waiting_phone = State()
    waiting_role = State()
    waiting_worker_type = State()


class OrderCreateStates(StatesGroup):
    """Zakaz ochish (admin)."""
    waiting_model_name = State()
    waiting_fabric_type = State()
    waiting_total_qty = State()
    waiting_price_per_unit = State()
    waiting_client_name = State()
    waiting_deadline = State()
    confirm = State()


class WorkSubmitStates(StatesGroup):
    """Tikuvchi ish topshirish."""
    select_order = State()
    enter_qty = State()
    confirm = State()


class QCCheckStates(StatesGroup):
    """Sifat nazorati."""
    select_order = State()
    enter_accepted_qty = State()
    enter_rejected_qty = State()
    enter_reject_reason = State()
    confirm = State()
