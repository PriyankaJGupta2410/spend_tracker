"""Pydantic models for the expenses module (expenses CRUD + summary)."""
import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=["249.50"])
    category: str = Field(min_length=1, max_length=50, examples=["food"])
    note: str | None = Field(default=None, max_length=200)
    date: dt.date

    @field_validator("category")
    @classmethod
    def normalise_category(cls, value: str) -> str:
        # "Food", "food " and "FOOD" must land in the same bucket in the summary.
        return value.lower()

    @field_validator("note")
    @classmethod
    def empty_note_is_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("date")
    @classmethod
    def not_in_future(cls, value: dt.date) -> dt.date:
        if value > dt.date.today():
            raise ValueError("date cannot be in the future")
        return value


class ExpenseOut(BaseModel):
    id: str
    amount: float
    category: str
    note: str | None
    date: dt.date
    created_at: dt.datetime


class CategoryTotal(BaseModel):
    category: str
    total: float
    share_percent: float


class MonthOverMonth(BaseModel):
    previous_month: str
    previous_total: float
    change_amount: float
    # None when the previous month had no spend (a percentage would be undefined).
    change_percent: float | None


class Insight(BaseModel):
    category: str
    previous: float
    current: float
    change_percent: float
    message: str


class Summary(BaseModel):
    month: str
    total_spend: float
    all_time_total: float
    by_category: list[CategoryTotal]
    month_over_month: MonthOverMonth
    insights: list[Insight]
