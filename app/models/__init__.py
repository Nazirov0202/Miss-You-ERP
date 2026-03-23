import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Enumlar ──────────────────────────────────────────────


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    sales = "sales"
    warehouse = "warehouse"
    worker = "worker"
    qc = "qc"


class OrderStatus(str, enum.Enum):
    opened = "opened"
    cutting = "cutting"
    sewing = "sewing"
    qc = "qc"
    packing = "packing"
    done = "done"
    closed = "closed"


class TransactionType(str, enum.Enum):
    work = "work"
    bonus = "bonus"
    penalty = "penalty"
    returned = "return"


class InventoryAction(str, enum.Enum):
    incoming = "incoming"
    outgoing = "outgoing"


class TransferStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


# ── Jadvallar ────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.worker
    )
    worker_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.id} {self.full_name} [{self.role.value}]>"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    model_name: Mapped[str] = mapped_column(String(255))
    fabric_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_qty: Mapped[int] = mapped_column(Integer)
    completed_qty: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.opened
    )
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="order")
    qc_results: Mapped[list["QCResult"]] = relationship(back_populates="order")

    @property
    def remaining_qty(self) -> int:
        return self.total_qty - self.completed_qty

    @property
    def progress_percent(self) -> float:
        if self.total_qty == 0:
            return 0.0
        return round(self.completed_qty / self.total_qty * 100, 1)

    def __repr__(self) -> str:
        return f"<Order {self.order_code} [{self.status.value}]>"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    qty: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type"),
        default=TransactionType.work,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="transactions")
    order: Mapped["Order"] = relationship(back_populates="transactions")


class Inventory(Base):
    """MVP dan keyingi bosqichda ishlatiladi."""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(20))
    qty_on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class InventoryLog(Base):
    """MVP dan keyingi bosqichda ishlatiladi."""

    __tablename__ = "inventory_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"))
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True
    )
    action: Mapped[InventoryAction] = mapped_column(
        Enum(InventoryAction, name="inventory_action")
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    performed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class Transfer(Base):
    """MVP dan keyingi bosqichda ishlatiladi."""

    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    from_user: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_user: Mapped[int] = mapped_column(ForeignKey("users.id"))
    qty: Mapped[int] = mapped_column(Integer)
    batch_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, name="transfer_status"),
        default=TransferStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )


class QCResult(Base):
    __tablename__ = "qc_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    inspector_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    accepted_qty: Mapped[int] = mapped_column(Integer, default=0)
    rejected_qty: Mapped[int] = mapped_column(Integer, default=0)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="qc_results")
    inspector: Mapped["User"] = relationship(foreign_keys=[inspector_id])
