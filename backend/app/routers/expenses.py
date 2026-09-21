"""Expenses routes: create/list expenses, monthly summary."""
import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import services
from ..database import get_db
from ..models import User
from ..schemas.expenses import ExpenseCreate, ExpenseOut, Summary
from ..security import get_current_user

MONTH_PATTERN = r"^(19|20)\d{2}-(0[1-9]|1[0-2])$"

router = APIRouter(tags=["expenses"])


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(payload: ExpenseCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return services.create_expense(
        db, user_id=user.id, amount=payload.amount, category=payload.category,
        note=payload.note, date=payload.date,
    )

@router.get("/expenses/categories", response_model=list[str])
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Distinct categories the user has already logged an expense under, for dropdowns."""
    return services.expenses.list_categories(db, user_id=user.id)

@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    category: str | None = Query(default=None, max_length=50),
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise StarletteHTTPException(422, "start_date must be on or before end_date")
    return services.list_expenses(
        db, user_id=user.id, category=category, start_date=start_date, end_date=end_date,
        limit=limit, offset=offset,
    )


@router.get("/summary", response_model=Summary)
def summary(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN, examples=["2026-09"]),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return services.build_summary(db, user.id, month or services.current_month())
