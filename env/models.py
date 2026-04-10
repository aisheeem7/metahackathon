"""
Typed Pydantic models for the Personal Expense Optimizer environment.
"""
from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    id: str
    day: int
    category: str
    amount: float
    description: str
    deferred: bool = False


class Observation(BaseModel):
    day: int = Field(..., description="Current simulation day (1-30)")
    total_balance: float = Field(..., description="Current account balance in INR")
    category_budgets: Dict[str, float] = Field(..., description="Budget per category")
    category_spent: Dict[str, float] = Field(..., description="Amount spent per category")
    recent_transactions: List[Transaction] = Field(default_factory=list)
    monthly_income: float = Field(..., description="Monthly income in INR")
    savings_goal_percentage: float = Field(..., description="Target savings as fraction (0-1)")
    pending_transaction: Optional[Transaction] = None


class Action(BaseModel):
    action_type: str = Field(
        ...,
        description="One of: allocate_budget, adjust_category, set_savings_goal, defer_expense"
    )
    category: Optional[str] = None
    amount: Optional[float] = None
    defer_days: Optional[int] = 0


class Reward(BaseModel):
    budget_adherence: float = 0.0
    savings_progress: float = 0.0
    category_efficiency: float = 0.0
    total: float = 0.0
