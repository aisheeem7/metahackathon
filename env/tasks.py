"""
Task definitions and deterministic graders.
Each grader returns a score in [0.0, 1.0].
"""
from typing import Dict, Any

TASKS = {
    "budget_adherence_easy": {
        "id": "budget_adherence_easy",
        "difficulty": "easy",
        "description": "Stay within 10% of daily budget for at least 7 days.",
    },
    "category_optimization_medium": {
        "id": "category_optimization_medium",
        "difficulty": "medium",
        "description": "Optimize budget across 5 categories and reduce spending by 15%.",
    },
    "predictive_budgeting_hard": {
        "id": "predictive_budgeting_hard",
        "difficulty": "hard",
        "description": "Achieve 25% savings by strategic deferral of discretionary expenses.",
    },
}


def grade_budget_adherence_easy(env_state: Dict[str, Any]) -> float:
    """
    Score = fraction of categories where spending <= 110% of budget.
    Full score (1.0) when all 6 categories are within tolerance.
    """
    budgets = env_state.get("category_budgets", {})
    spent = env_state.get("category_spent", {})
    if not budgets:
        return 0.0
    within = sum(
        1 for cat, budget in budgets.items()
        if spent.get(cat, 0.0) <= budget * 1.10
    )
    return round(within / len(budgets), 4)


def grade_category_optimization_medium(env_state: Dict[str, Any]) -> float:
    """
    Score based on whether total spending is at least 15% below income.
    Partial credit proportional to progress toward that threshold.
    """
    income = env_state.get("monthly_income", 50000.0)
    spent = sum(env_state.get("category_spent", {}).values())
    target_spend = income * 0.85  # spend at most 85% → save at least 15%
    if spent <= target_spend:
        return 1.0
    # Partial credit: how far along toward target
    reduction_needed = spent - target_spend
    max_reduction = income - target_spend  # worst case: spent 100% of income
    score = max(0.0, 1.0 - reduction_needed / max_reduction)
    return round(score, 4)


def grade_predictive_budgeting_hard(env_state: Dict[str, Any]) -> float:
    """
    Score based on whether savings_goal_percentage >= 0.25 AND
    actual savings rate matches or exceeds the goal.
    """
    income = env_state.get("monthly_income", 50000.0)
    spent = sum(env_state.get("category_spent", {}).values())
    actual_savings_rate = max(0.0, (income - spent) / income)
    target = 0.25
    score = min(1.0, actual_savings_rate / target) if target > 0 else 0.0
    return round(score, 4)


GRADERS = {
    "budget_adherence_easy": grade_budget_adherence_easy,
    "category_optimization_medium": grade_category_optimization_medium,
    "predictive_budgeting_hard": grade_predictive_budgeting_hard,
}


def grade_task(task_id: str, env_state: Dict[str, Any]) -> Dict[str, Any]:
    if task_id not in GRADERS:
        return {"error": f"Unknown task: {task_id}", "score": 0.0}
    score = GRADERS[task_id](env_state)
    return {
        "task_id": task_id,
        "score": score,
        "difficulty": TASKS[task_id]["difficulty"],
        "description": TASKS[task_id]["description"],
    }
