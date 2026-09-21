import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _utcnow() -> dt.datetime:
    # MySQL DATETIME has no timezone, so store naive UTC consistently.
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, nullable=False)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        Index("ix_expenses_user_spent_on", "user_id", "spent_on"),
        Index("ix_expenses_user_category_spent_on", "user_id", "category", "spent_on"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    spent_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)