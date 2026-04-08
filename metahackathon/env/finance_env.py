"""
Personal Expense Optimization Environment - OpenEnv compliant.

Real-world task: Agent must allocate monthly budget across categories
and make smart spending decisions to meet savings goals while staying
within budget constraints.

Simulates realistic transaction patterns from SMS data.
"""

import random
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from .models import (
    Action, ActionType, Observation, Reward, Transaction,
    TaskInfo, StepOutput, ResetOutput
)


# Realistic SMS transaction patterns by category
TRANSACTION_PATTERNS = {
    "Food & Dining": [
        ("Swiggy", [250, 300, 350, 400], 0.4),
        ("Starbucks", [150, 200], 0.3),
        ("ZomatoGold", [500], 0.2),
        ("DMart Groceries", [1000, 1200, 1500], 0.3),
        ("Restaurant", [800, 1000, 1200], 0.15),
    ],
    "Transport": [
        ("Uber", [120, 150, 200], 0.35),
        ("Ola", [100, 150, 180], 0.3),
        ("Metro Recharge", [100, 200], 0.2),
        ("Petrol/Fuel", [1000, 1200, 1500], 0.1),
        ("Train Ticket", [500, 800], 0.05),
    ],
    "Shopping": [
        ("Amazon", [500, 1000, 2000, 3000], 0.2),
        ("Flipkart", [300, 800, 1500], 0.15),
        ("Myntra", [1000, 1500, 2000], 0.15),
        ("Local Shops", [200, 500], 0.2),
    ],
    "Health": [
        ("Apollo Pharmacy", [300, 500, 800], 0.2),
        ("Gym Membership", [500, 1000], 0.1),
        ("Doctor", [500, 1500, 2000], 0.08),
        ("Health Insurance", [1000, 2000, 3000], 0.05),
    ],
    "Bills": [
        ("Electricity", [800, 1200, 1500], 0.15),
        ("Water", [200, 300], 0.15),
        ("Internet", [500, 700], 0.15),
        ("Mobile Bill", [200, 300, 500], 0.15),
        ("Netflix/Spotify", [100, 200, 300], 0.1),
        ("Insurance", [1000, 1500, 2000], 0.1),
    ]
}

DEFAULT_INCOME = 50000  # ₹50k monthly income


class PersonalExpenseOptimizer:
    """
    OpenEnv-compliant environment for personal expense optimization.
    
    Task: Allocate monthly ₹50k budget across 5 categories and make
    spending decisions to meet savings goals (20% by default).
    
    Episodes run for 30 days (1 month). Each day, agent receives
    1-3 realistic transactions and must decide whether to spend,
    defer, or adjust budget allocations.
    """

    def __init__(self, monthly_income: float = DEFAULT_INCOME, seed: int = None):
        self.monthly_income = monthly_income
        self.monthly_budget = monthly_income
        self.categories = ["Food & Dining", "Transport", "Shopping", "Health", "Bills"]
        
        if seed is not None:
            random.seed(seed)
        
        # Episode state
        self.day = 1
        self.category_budgets: Dict[str, float] = {}
        self.category_spent: Dict[str, float] = {}
        self.total_spent = 0.0
        self.current_savings = 0.0
        self.savings_goal_percentage = 0.2  # 20% target savings
        
        # Decision tracking
        self.days_on_budget = 0
        self.overspend_count = 0
        self.deferred_expenses: List[Tuple[str, float, int]] = []
        self.transaction_history: List[Transaction] = []
        self.decision_history: List[Dict] = []
        
        # Current transaction
        self.pending_transaction: Optional[Transaction] = None
        self.transaction_processed = False

    def reset(self, task: Optional[TaskInfo] = None) -> ResetOutput:
        """
        Reset environment to start of month.
        
        Args:
            task: Optional task configuration
            
        Returns:
            ResetOutput with initial observation and metadata
        """
        self.day = 1
        self.total_spent = 0.0
        self.current_savings = self.monthly_budget
        self.days_on_budget = 0
        self.overspend_count = 0
        self.deferred_expenses = []
        self.transaction_history = []
        self.decision_history = []
        self.transaction_processed = False
        
        # Initialize budget allocations (default: equal split)
        for cat in self.categories:
            self.category_budgets[cat] = self.monthly_budget / len(self.categories)
            self.category_spent[cat] = 0.0
        
        obs = self._get_observation()
        return ResetOutput(
            observation=obs,
            info={"task": task.dict() if task else None, "episode_start": datetime.now().isoformat()}
        )

    def step(self, action: Action) -> StepOutput:
        """
        Execute one step of the environment.
        
        Args:
            action: Agent's decision
            
        Returns:
            StepOutput with observation, reward, done, and info
        """
        info = {}
        
        # Process agent action
        if action.action_type == ActionType.ALLOCATE_BUDGET:
            self._handle_allocate_budget(action)
        elif action.action_type == ActionType.ADJUST_CATEGORY:
            self._handle_adjust_category(action)
        elif action.action_type == ActionType.SET_SAVINGS_GOAL:
            self._handle_set_savings_goal(action)
        elif action.action_type == ActionType.DEFER_EXPENSE:
            self._handle_defer_expense(action)
        
        # Generate transaction if needed
        if self.pending_transaction is None:
            self.pending_transaction = self._generate_transaction()
            self.transaction_processed = False
        
        # Check if transaction was processed (implicitly by adjust)
        # If still pending, apply it with minimum cost decision
        if not self.transaction_processed and self.pending_transaction:
            self._apply_transaction(self.pending_transaction, deferred=False)
        
        # Calculate reward
        reward = self._calculate_reward()
        
        # Update day counter
        self.day += 1
        done = self.day > 30
        
        # Check budget adherence
        if self._check_within_budget():
            self.days_on_budget += 1
        
        if done:
            # Final savings calculation
            self.current_savings = self.monthly_budget - self.total_spent
            info["final_savings"] = self.current_savings
            info["savings_percentage"] = (self.current_savings / self.monthly_budget) * 100
            info["task_score"] = self._grade_episode()
        
        obs = self._get_observation()
        return StepOutput(
            observation=obs,
            reward=reward,
            done=done,
            info=info
        )

    def state(self) -> Dict:
        """Get current state as dictionary."""
        return {
            "day": self.day,
            "total_budget": self.monthly_budget,
            "total_spent": self.total_spent,
            "current_savings": self.monthly_budget - self.total_spent,
            "category_budgets": self.category_budgets.copy(),
            "category_spent": self.category_spent.copy(),
            "savings_goal_percentage": self.savings_goal_percentage,
            "days_on_budget": self.days_on_budget,
            "overspend_count": self.overspend_count,
        }

    # Private helper methods
    
    def _get_observation(self) -> Observation:
        """Construct typed observation from current state."""
        category_remaining = {
            cat: max(0, self.category_budgets[cat] - self.category_spent[cat])
            for cat in self.categories
        }
        
        return Observation(
            day=self.day,
            total_balance=max(0, self.monthly_budget - self.total_spent),
            category_budgets=self.category_budgets.copy(),
            category_spent=self.category_spent.copy(),
            category_remaining=category_remaining,
            recent_transactions=self.transaction_history[-5:],
            pending_transaction=self.pending_transaction,
            monthly_income=self.monthly_income,
            savings_goal_percentage=self.savings_goal_percentage,
            current_savings=self.monthly_budget - self.total_spent,
            projected_savings=max(0, self.monthly_budget - self.total_spent),
            days_on_budget=self.days_on_budget,
            overspend_count=self.overspend_count,
        )

    def _generate_transaction(self) -> Transaction:
        """Generate realistic transaction from SMS patterns."""
        category = random.choice(self.categories)
        patterns = TRANSACTION_PATTERNS[category]
        
        # Pick a merchant and amount
        merchant, amounts, frequency = random.choices(patterns, k=1)[0]
        amount = random.choice(amounts)
        
        # Discretionary transactions: food, shopping, entertainment
        is_discretionary = category in ["Food & Dining", "Shopping"]
        
        transaction = Transaction(
            category=category,
            amount=amount,
            date=self.day,
            description=f"{merchant} - ₹{amount}",
            is_discretionary=is_discretionary
        )
        return transaction

    def _apply_transaction(self, txn: Transaction, deferred: bool = False) -> None:
        """Apply transaction to spending."""
        if not deferred:
            self.category_spent[txn.category] += txn.amount
            self.total_spent += txn.amount
            self.transaction_history.append(txn)
        else:
            # Deferred: add cost and remember for later
            self.deferred_expenses.append((txn.category, txn.amount, self.day))
        
        self.pending_transaction = None
        self.transaction_processed = True

    def _handle_allocate_budget(self, action: Action) -> None:
        """Handle ALLOCATE_BUDGET action."""
        if action.amount is None:
            return
        
        # Distribute budget among all categories based on percentages
        total = sum(self.category_budgets.values())
        for cat in self.categories:
            self.category_budgets[cat] = (self.category_budgets[cat] / total) * action.amount

    def _handle_adjust_category(self, action: Action) -> None:
        """Handle ADJUST_CATEGORY action."""
        if action.category not in self.categories or action.amount is None:
            return
        
        self.category_budgets[action.category] = action.amount
        
        # If there's a pending transaction in this category, this implicitly approves it
        if self.pending_transaction and self.pending_transaction.category == action.category:
            if self.category_spent[action.category] + self.pending_transaction.amount <= action.amount:
                self._apply_transaction(self.pending_transaction, deferred=False)

    def _handle_set_savings_goal(self, action: Action) -> None:
        """Handle SET_SAVINGS_GOAL action."""
        if action.amount is None:
            return
        
        # Clamp savings goal to 0-50%
        self.savings_goal_percentage = max(0, min(0.5, action.amount / 100))

    def _handle_defer_expense(self, action: Action) -> None:
        """Handle DEFER_EXPENSE action."""
        if self.pending_transaction and self.pending_transaction.is_discretionary:
            self._apply_transaction(self.pending_transaction, deferred=True)

    def _check_within_budget(self) -> bool:
        """Check if currently within all category budgets."""
        return all(
            self.category_spent[cat] <= self.category_budgets[cat] * 1.1  # 10% tolerance
            for cat in self.categories
        )

    def _calculate_reward(self) -> Reward:
        """
        Calculate comprehensive reward with multiple components.
        Provides partial progress signals throughout episode.
        """
        # 1. Budget adherence reward (0 to 1, penalty if over)
        overspended_categories = sum(
            1 for cat in self.categories
            if self.category_spent[cat] > self.category_budgets[cat]
        )
        
        if overspended_categories > 0:
            self.overspend_count += 1
            budget_adherence = -0.5
        else:
            budget_adherence = min(1.0, 1.0 - (self.total_spent / self.monthly_budget) * 0.3)
        
        # 2. Savings progress reward
        target_savings = self.monthly_budget * self.savings_goal_percentage
        current_savings = self.monthly_budget - self.total_spent
        savings_progress = min(1.0, max(0, current_savings / target_savings)) if target_savings > 0 else 1.0
        
        # 3. Category balance (reward diverse spending, penalize concentration)
        spent_percentages = [
            self.category_spent[cat] / max(1, self.category_budgets[cat])
            for cat in self.categories
        ]
        avg_spend = sum(spent_percentages) / len(self.categories)
        variance = sum((x - avg_spend) ** 2 for x in spent_percentages) / len(self.categories)
        category_balance = max(-1.0, 1.0 - variance)  # Lower variance = higher reward
        
        # 4. Transaction decision reward
        transaction_decision = 0.5
        if self.pending_transaction:
            if self.pending_transaction.is_discretionary and len(self.deferred_expenses) > 0:
                transaction_decision = 1.0  # Good: deferred discretionary
            elif not self.pending_transaction.is_discretionary:
                transaction_decision = 0.8  # Good: essential expenses
        
        # Penalties
        overspend_penalty = -0.3 * min(1.0, overspended_categories / len(self.categories))
        
        # Total reward (average of components, then apply penalties)
        total = (budget_adherence + savings_progress + category_balance + transaction_decision) / 4.0
        total = max(-1.0, min(1.0, total + overspend_penalty))
        
        return Reward(
            total=total,
            budget_adherence=budget_adherence,
            savings_progress=savings_progress,
            category_balance=category_balance,
            transaction_decision=transaction_decision,
            overspend_penalty=overspend_penalty,
            poor_decisions=self.overspend_count,
        )

    def _grade_episode(self) -> Dict[str, float]:
        """Grade the episode performance (for task graders)."""
        final_savings = self.monthly_budget - self.total_spent
        savings_rate = final_savings / self.monthly_budget
        
        return {
            "final_savings": final_savings,
            "savings_rate": savings_rate,
            "days_on_budget": self.days_on_budget,
            "budget_adherence_score": self.days_on_budget / 30,
            "savings_goal_met": 1.0 if savings_rate >= self.savings_goal_percentage else 0.0,
        }

if __name__ == "__main__":
    # Test the environment
    env = PersonalExpenseOptimizer()
    reset_output = env.reset()
    obs = reset_output.observation
    
    for _ in range(5):
        # Test different action types
        actions = [
            Action(action_type=ActionType.ALLOCATE_BUDGET, amount=50000),
            Action(action_type=ActionType.ADJUST_CATEGORY, category="Food & Dining", amount=10000),
            Action(action_type=ActionType.SET_SAVINGS_GOAL, amount=20),
            Action(action_type=ActionType.DEFER_EXPENSE),
        ]
        action = random.choice(actions)
        step_output = env.step(action)
        print(f"Day {step_output.observation.day}: Reward={step_output.reward.total:.2f}")