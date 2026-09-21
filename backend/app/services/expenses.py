"""Business logic and queries for the expenses module. The pure functions here
are the ones covered by unit tests (see tests/test_summary.py)."""
import datetime as dt
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Expense

SPIKE_THRESHOLD_PERCENT = Decimal("20")
ZERO = Decimal("0")


# ---------- helpers ----------

def money(value) -> float:
    """Decimal -> JSON number, only at the response edge."""
    return round(float(value), 2)


def current_month() -> str:
    return dt.date.today().strftime("%Y-%m")


def previous_month(month: str) -> str:
    year, mon = (int(part) for part in month.split("-"))
    if mon == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{mon - 1:02d}"


def month_range(month: str) -> tuple[dt.date, dt.date]:
    """Return [first day of month, first day of next month)."""
    year, mon = (int(part) for part in month.split("-"))
    start = dt.date(year, mon, 1)
    end = dt.date(year + 1, 1, 1) if mon == 12 else dt.date(year, mon + 1, 1)
    return start, end


# ---------- pure calculations ----------

def compute_change(current: Decimal, previous: Decimal) -> tuple[Decimal, Decimal | None]:
    """Absolute change and percentage change. Percentage is None if previous is zero."""
    current, previous = Decimal(current), Decimal(previous)
    change = current - previous
    if previous == 0:
        return change, None
    return change, round(change * 100 / previous, 2)


def find_spikes(
    current: dict[str, Decimal],
    previous: dict[str, Decimal],
    threshold: Decimal = SPIKE_THRESHOLD_PERCENT,
) -> list[dict]:
    """Categories whose spend rose by strictly more than `threshold` percent.

    Categories with no spend last month are skipped: there is no baseline to compare to.
    """
    spikes = []
    for category, cur in current.items():
        prev = Decimal(previous.get(category, ZERO))
        if prev <= 0:
            continue
        pct = (Decimal(cur) - prev) * 100 / prev
        if pct > threshold:
            spikes.append(
                {
                    "category": category,
                    "previous": money(prev),
                    "current": money(cur),
                    "change_percent": float(round(pct, 2)),
                }
            )
    return sorted(spikes, key=lambda s: s["change_percent"], reverse=True)


# ---------- expenses (always scoped to one user) ----------

def _to_dict(e: Expense) -> dict:
    return {
        "id": e.id,
        "amount": money(e.amount),
        "category": e.category,
        "note": e.note,
        "date": e.spent_on,
        "created_at": e.created_at,
    }


def create_expense(
    db: Session,
    *,
    user_id: str,
    amount: Decimal,
    category: str,
    note: str | None,
    date: dt.date,
) -> dict:
    expense = Expense(
        id=str(uuid4()),
        user_id=user_id,
        amount=amount,
        category=category,
        note=note,
        spent_on=date,
    )

    db.add(expense)
    db.commit()
    db.refresh(expense)

    return _to_dict(expense)


def list_expenses(db: Session, *, user_id: str, category: str | None, start_date: dt.date | None,
                  end_date: dt.date | None, limit: int, offset: int) -> list[dict]:
    stmt = select(Expense).where(Expense.user_id == user_id)
    if category:
        stmt = stmt.where(Expense.category == category.strip().lower())
    if start_date:
        stmt = stmt.where(Expense.spent_on >= start_date)
    if end_date:
        stmt = stmt.where(Expense.spent_on <= end_date)
    stmt = stmt.order_by(Expense.spent_on.desc(), Expense.id.desc()).limit(limit).offset(offset)
    return [_to_dict(e) for e in db.scalars(stmt)]


def _totals_by_category(db: Session, user_id: str, month: str) -> dict[str, Decimal]:
    start, end = month_range(month)
    total = func.sum(Expense.amount).label("total")
    stmt = (
        select(Expense.category, total)
        .where(Expense.user_id == user_id, Expense.spent_on >= start, Expense.spent_on < end)
        .group_by(Expense.category)
        .order_by(total.desc(), Expense.category)
    )
    return {category: Decimal(t) for category, t in db.execute(stmt)}


def build_summary(db: Session, user_id: str, month: str) -> dict:
    prev_month = previous_month(month)
    current = _totals_by_category(db, user_id, month)
    previous = _totals_by_category(db, user_id, prev_month)

    total = sum(current.values(), ZERO)
    prev_total = sum(previous.values(), ZERO)
    change, change_pct = compute_change(total, prev_total)

    all_time = Decimal(db.scalar(select(func.sum(Expense.amount)).where(Expense.user_id == user_id)) or 0)

    by_category = [
        {
            "category": cat,
            "total": money(amount),
            "share_percent": float(round(amount * 100 / total, 2)) if total else 0.0,
        }
        for cat, amount in current.items()
    ]

    insights = []
    for spike in find_spikes(current, previous):
        spike["message"] = (
            f"{spike['category'].title()} spend rose {spike['change_percent']:.1f}% "
            f"vs {prev_month} ({spike['previous']:.2f} to {spike['current']:.2f})."
        )
        insights.append(spike)

    return {
        "month": month,
        "total_spend": money(total),
        "all_time_total": money(all_time),
        "by_category": by_category,
        "month_over_month": {
            "previous_month": prev_month,
            "previous_total": money(prev_total),
            "change_amount": money(change),
            "change_percent": None if change_pct is None else float(change_pct),
        },
        "insights": insights,
    }
