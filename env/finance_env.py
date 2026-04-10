"""
Core logic for the Personal Expense Optimizer environment.
Simulates a 30-day monthly budget cycle with SMS-style transactions.
"""
import random
from copy import deepcopy
from typing import Dict, Tuple, List

from env.models import Action, Observation, Reward, Transaction

MONTHLY_INCOME = 50000.0
SAVINGS_GOAL = 0.20  # 20% default savings goal
CATEGORIES = ["Food", "Transport", "Entertainment", "Bills", "Shopping", "Health"]

# Daily transaction pool (realistic INR amounts)
TRANSACTION_POOL = [
    ("Food",          200,  800,  "Grocery / restaurant"),
    ("Transport",     50,   500,  "Cab / fuel"),
    ("Entertainment", 300,  1500, "OTT / outing"),
    ("Bills",         500,  3000, "Electricity / internet"),
    ("Shopping",      500,  3000, "Clothes / gadgets"),
    ("Health",        200,  1500, "Pharmacy / clinic"),
]

DEFAULT_BUDGETS: Dict[str, float] = {
    "Food":          10000.0,
    "Transport":      5000.0,
    "Entertainment":  5000.0,
    "Bills":          8000.0,
    "Shopping":       7000.0,
    "Health":         5000.0,
}


def _make_transaction(day: int, txn_id: int) -> Transaction:
    cat, lo, hi, desc = random.choice(TRANSACTION_POOL)
    return Transaction(
        id=f"txn_{day}_{txn_id}",
        day=day,
        category=cat,
        amount=round(random.uniform(lo, hi), 2),
        description=desc,
    )


class FinanceEnv:
    """OpenEnv-compliant 30-day personal expense simulation."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = random.Random(seed)
        self.reset()

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self) -> Observation:
        random.seed(self.seed)
        self.day: int = 1
        self.balance: float = MONTHLY_INCOME
        self.monthly_income: float = MONTHLY_INCOME
        self.savings_goal: float = SAVINGS_GOAL
        self.category_budgets: Dict[str, float] = deepcopy(DEFAULT_BUDGETS)
        self.category_spent: Dict[str, float] = {c: 0.0 for c in CATEGORIES}
        self.transactions: List[Transaction] = []
        self.deferred: List[Transaction] = []
        self.done: bool = False
        self._step_count: int = 0

        # Pre-generate all 30 days of transactions for determinism
        self._all_transactions: List[Transaction] = []
        for d in range(1, 31):
            count = random.randint(1, 3)
            for i in range(count):
                self._all_transactions.append(_make_transaction(d, i))

        self._pending_idx: int = 0
        return self._observe()

    def step(self, action: Action) -> Tuple[Observation, Reward, bool]:
        if self.done:
            return self._observe(), Reward(), True

        self._apply_action(action)
        self._process_day_transactions()

        self.day += 1
        self._step_count += 1

        if self.day > 30:
            self.done = True

        reward = self._compute_reward()
        return self._observe(), reward, self.done

    def state(self) -> dict:
        return self._observe().model_dump()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_action(self, action: Action) -> None:
        at = action.action_type
        cat = action.category
        amt = action.amount or 0.0

        if at == "allocate_budget" and cat in self.category_budgets:
            self.category_budgets[cat] = max(0.0, amt)

        elif at == "adjust_category" and cat in self.category_budgets:
            self.category_budgets[cat] = max(0.0, self.category_budgets[cat] + amt)

        elif at == "set_savings_goal":
            self.savings_goal = max(0.0, min(1.0, amt / 100.0 if amt > 1 else amt))

        elif at == "defer_expense":
            # Defer next pending transaction for this category
            pending = self._get_pending_transactions()
            for txn in pending:
                if cat and txn.category == cat:
                    txn.deferred = True
                    days = max(1, action.defer_days or 3)
                    txn.day = min(30, txn.day + days)
                    break

    def _process_day_transactions(self) -> None:
        today_txns = [
            t for t in self._all_transactions
            if t.day == self.day and not t.deferred
        ]
        for txn in today_txns:
            self.balance -= txn.amount
            self.category_spent[txn.category] = (
                self.category_spent.get(txn.category, 0.0) + txn.amount
            )
            self.transactions.append(txn)

    def _get_pending_transactions(self) -> List[Transaction]:
        return [t for t in self._all_transactions if t.day >= self.day and not t.deferred]

    def _compute_reward(self) -> Reward:
        # Budget adherence: fraction of categories within budget
        within = sum(
            1 for c in CATEGORIES
            if self.category_spent.get(c, 0) <= self.category_budgets.get(c, 0)
        )
        budget_adherence = within / len(CATEGORIES)

        # Savings progress: how close to savings goal
        spent_total = sum(self.category_spent.values())
        actual_savings = (self.monthly_income - spent_total) / self.monthly_income
        savings_progress = min(1.0, max(0.0, actual_savings / self.savings_goal)) if self.savings_goal > 0 else 0.0

        # Category efficiency: inverse of overspend ratio
        overspend_fracs = []
        for c in CATEGORIES:
            budget = self.category_budgets.get(c, 1.0) or 1.0
            spent = self.category_spent.get(c, 0.0)
            overspend_fracs.append(max(0.0, (spent - budget) / budget))
        category_efficiency = max(0.0, 1.0 - sum(overspend_fracs) / len(CATEGORIES))

        total = round(
            0.4 * budget_adherence + 0.4 * savings_progress + 0.2 * category_efficiency, 4
        )
        return Reward(
            budget_adherence=round(budget_adherence, 4),
            savings_progress=round(savings_progress, 4),
            category_efficiency=round(category_efficiency, 4),
            total=total,
        )

    def _observe(self) -> Observation:
        recent = self.transactions[-5:] if self.transactions else []
        pending = self._get_pending_transactions()
        pending_txn = pending[0] if pending else None
        return Observation(
            day=self.day,
            total_balance=round(self.balance, 2),
            category_budgets=dict(self.category_budgets),
            category_spent=dict(self.category_spent),
            recent_transactions=recent,
            monthly_income=self.monthly_income,
            savings_goal_percentage=self.savings_goal,
            pending_transaction=pending_txn,
        )
