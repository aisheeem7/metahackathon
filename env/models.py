"""
Pydantic models for Personal Expense Optimization environment.
Implements OpenEnv spec with typed Action, Observation, and Reward.
"""

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ActionType(str, Enum):
    """Available agent actions for budget management."""
    ALLOCATE_BUDGET = "allocate_budget"
    ADJUST_CATEGORY = "adjust_category"
    SET_SAVINGS_GOAL = "set_savings_goal"
    DEFER_EXPENSE = "defer_expense"


class Action(BaseModel):
    """
    Agent action in the expense optimization environment.
    
    Examples:
        allocate_budget: Set monthly budget limits per category
        adjust_category: Change budget allocation for a specific category
        set_savings_goal: Set target monthly savings percentage
        defer_expense: Choose to defer a discretionary expense to next month
    """
    action_type: ActionType = Field(..., description="Type of action to perform")
    category: Optional[str] = Field(None, description="Target category (Food, Transport, Shopping, Health, Bills)")
    amount: Optional[float] = Field(None, description="Budget amount in INR or savings goal percentage")
    defer_days: Optional[int] = Field(None, description="Days to defer expense (for defer_expense action)")
    
    class Config:
        use_enum_values = True


class Transaction(BaseModel):
    """Simulated real-world transaction from SMS."""
    category: str = Field(..., description="Expense category")
    amount: float = Field(..., ge=0, description="Transaction amount in INR")
    date: int = Field(..., description="Day of month (1-30)")
    description: str = Field(..., description="Transaction description")
    is_discretionary: bool = Field(False, description="Can this expense be deferred?")


class Observation(BaseModel):
    """
    Current state observation for the agent.
    Provides all information needed to make spending decisions.
    """
    day: int = Field(..., ge=1, le=30, description="Current day of month")
    total_balance: float = Field(..., ge=0, description="Remaining monthly budget in INR")
    
    # Category budgets and spending
    category_budgets: Dict[str, float] = Field(..., description="Allocated budget per category")
    category_spent: Dict[str, float] = Field(..., description="Already spent per category")
    category_remaining: Dict[str, float] = Field(..., description="Remaining budget per category")
    
    # Recent transactions
    recent_transactions: List[Transaction] = Field(..., description="Last 5 transactions")
    pending_transaction: Optional[Transaction] = Field(None, description="Current unprocessed transaction")
    
    # Goals and metrics
    monthly_income: float = Field(..., description="Monthly income in INR")
    savings_goal_percentage: float = Field(..., description="Target savings as % of income")
    current_savings: float = Field(..., description="Amount saved so far")
    projected_savings: float = Field(..., description="Estimated final savings if no more spending")
    
    # Performance indicators
    days_on_budget: int = Field(..., description="Days stayed within category limits")
    overspend_count: int = Field(..., description="Times exceeded category budget")
    
    class Config:
        arbitrary_types_allowed = True


class Reward(BaseModel):
    """
    Reward signal with detailed breakdown for learning.
    Provides partial progress signals throughout episode.
    """
    total: float = Field(..., ge=-1.0, le=1.0, description="Total reward (-1.0 to 1.0)")
    
    # Component rewards
    budget_adherence: float = Field(..., ge=-1.0, le=1.0, description="Reward for staying in budget")
    savings_progress: float = Field(..., ge=-1.0, le=1.0, description="Reward for meeting savings goal")
    category_balance: float = Field(..., ge=-1.0, le=1.0, description="Reward for balanced spending across categories")
    transaction_decision: float = Field(..., ge=-1.0, le=1.0, description="Reward for smart transaction decisions")
    
    # Penalties
    overspend_penalty: float = Field(0, le=0, description="Penalty for exceeding limits")
    poor_decisions: int = Field(0, ge=0, description="Count of poor decisions")
    
    class Config:
        arbitrary_types_allowed = True


class TaskInfo(BaseModel):
    """Metadata about the current task."""
    task_id: str = Field(..., description="Unique task identifier")
    difficulty: Literal["easy", "medium", "hard"] = Field(..., description="Task difficulty level")
    description: str = Field(..., description="Human-readable task description")
    success_criteria: Dict[str, float] = Field(..., description="Grading criteria and thresholds")
    max_episodes: int = Field(1, description="Number of episodes to run")


class StepOutput(BaseModel):
    """Output of environment.step() - OpenEnv compliant."""
    observation: Observation
    reward: Reward
    done: bool = Field(..., description="Episode complete?")
    info: Dict = Field(default_factory=dict, description="Additional info (task_score, etc.)")


class ResetOutput(BaseModel):
    """Output of environment.reset() - OpenEnv compliant."""
    observation: Observation
    info: Dict = Field(default_factory=dict, description="Episode metadata")
