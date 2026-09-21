"""Business logic and queries, split module-wise (auth.py / expenses.py).

Everything is re-exported here so existing code / tests can keep doing
`from app import services` and `services.<name>(...)`.
"""
from .auth import create_user, get_user_by_username
from .expenses import (build_summary, compute_change, create_expense, current_month,
                       find_spikes, list_expenses, money, month_range, previous_month)

__all__ = [
    "get_user_by_username",
    "create_user",
    "money",
    "current_month",
    "previous_month",
    "month_range",
    "compute_change",
    "find_spikes",
    "create_expense",
    "list_expenses",
    "build_summary",
]
