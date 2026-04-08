"""
Task definitions and graders for Personal Expense Optimizer environment.

Each task defines a concrete objective and includes a deterministic grader
that scores agent performance from 0.0-1.0.
"""

from typing import Dict, List
from dataclasses import dataclass
from pathlib import Path
import json

from .models import TaskInfo, Observation


@dataclass
class TaskGrade:
    """Result of task grading."""
    task_id: str
    score: float  # 0.0-1.0
    criteria_scores: Dict[str, float]
    passed: bool
    details: str


class TaskGrader:
    """Grades agent performance on defined tasks."""
    
    TASKS = {
        "budget_adherence_easy": TaskInfo(
            task_id="budget_adherence_easy",
            difficulty="easy",
            description="Stay within 10% of daily budget for at least 7 days in a 30-day month.",
            success_criteria={
                "days_on_budget_minimum": 7,
                "budget_overrun_tolerance": 0.10,
            },
            max_episodes=1
        ),
        
        "category_optimization_medium": TaskInfo(
            task_id="category_optimization_medium",
            difficulty="medium",
            description="Allocate budget optimally across 5 categories and reduce spending by 15% while staying within limits for 20+ days.",
            success_criteria={
                "days_on_budget_minimum": 20,
                "spending_reduction": 0.15,
                "savings_rate_target": 0.20,
                "category_balance_score": 0.7,
            },
            max_episodes=1
        ),
        
        "predictive_budgeting_hard": TaskInfo(
            task_id="predictive_budgeting_hard",
            difficulty="hard",
            description="Achieve 25% savings by predicting expenses and strategically deferring discretionary expenses.",
            success_criteria={
                "savings_rate_target": 0.25,
                "days_on_budget_minimum": 25,
                "deferred_expenses_count_minimum": 5,
            },
            max_episodes=1
        ),
    }

    @staticmethod
    def get_task(task_id: str) -> TaskInfo:
        """Get task definition by ID."""
        if task_id not in TaskGrader.TASKS:
            raise ValueError(f"Unknown task: {task_id}. Available: {list(TaskGrader.TASKS.keys())}")
        return TaskGrader.TASKS[task_id]

    @staticmethod
    def grade_easy(episode_stats: Dict) -> TaskGrade:
        """
        Grade 'budget_adherence_easy' task.
        
        Criteria:
        - Days on budget >= 7
        - Acceptable for demo/validation
        
        Score: (days_on_budget / 7) capped at 1.0
        """
        days_on_budget = episode_stats.get("days_on_budget", 0)
        target_days = 7
        
        score = min(1.0, days_on_budget / target_days)
        passed = days_on_budget >= target_days
        
        return TaskGrade(
            task_id="budget_adherence_easy",
            score=score,
            criteria_scores={"days_on_budget": min(1.0, days_on_budget / target_days)},
            passed=passed,
            details=f"Achieved {days_on_budget}/{target_days} days on budget. Score: {score:.2f}"
        )

    @staticmethod
    def grade_medium(episode_stats: Dict) -> TaskGrade:
        """
        Grade 'category_optimization_medium' task.
        
        Criteria (equal weights):
        1. days_on_budget >= 20 (40 points)
        2. savings_rate >= 0.20 (30 points)
        3. spending_reduction >= 0.15 (20 points)
        4. category_balance >= 0.7 (10 points)
        
        Total: 100 points → 1.0 score
        """
        days_on_budget = episode_stats.get("days_on_budget", 0)
        savings_rate = episode_stats.get("savings_rate", 0.0)
        final_savings = episode_stats.get("final_savings", 0)
        category_spent = episode_stats.get("category_spent", {})
        monthly_budget = episode_stats.get("monthly_budget", 50000)
        
        # Criterion 1: Days on budget (40%)
        days_score = min(1.0, days_on_budget / 20)
        
        # Criterion 2: Savings rate (30%)
        savings_score = min(1.0, savings_rate / 0.20)
        
        # Criterion 3: Spending reduction (baseline = 1.0 * budget spent)
        # Simple baseline: agent spends 80% of budget by default
        baseline_spending = monthly_budget * 0.80
        actual_spending = monthly_budget - final_savings
        spending_reduction = (baseline_spending - actual_spending) / baseline_spending
        reduction_score = min(1.0, max(0, spending_reduction / 0.15))
        
        # Criterion 4: Category balance (diverse spending)
        if category_spent:
            spent_values = list(category_spent.values())
            avg_spent = sum(spent_values) / len(spent_values) if spent_values else 0
            variance = sum((x - avg_spent) ** 2 for x in spent_values) / len(spent_values) if spent_values else 0
            # Lower variance = better balance. Max variance for 5 equal categories = 0
            # Reasonable "bad" variance = high concentration (one category >> others)
            max_variance = (avg_spent * 0.8) ** 2 * 5  # Estimate of unbalanced distribution
            category_balance = max(0, 1.0 - (variance / max_variance)) if max_variance > 0 else 1.0
        else:
            category_balance = 0.5
        balance_score = min(1.0, category_balance)
        
        # Weighted average
        score = (
            days_score * 0.40 +
            savings_score * 0.30 +
            reduction_score * 0.20 +
            balance_score * 0.10
        )
        
        passed = (
            days_on_budget >= 20 and
            savings_rate >= 0.20 and
            spending_reduction >= 0.15
        )
        
        return TaskGrade(
            task_id="category_optimization_medium",
            score=score,
            criteria_scores={
                "days_on_budget": days_score,
                "savings_rate": savings_score,
                "spending_reduction": reduction_score,
                "category_balance": balance_score,
            },
            passed=passed,
            details=(
                f"Days: {days_on_budget}/20 ({days_score:.2f}), "
                f"Savings: {savings_rate:.1%}/20% ({savings_score:.2f}), "
                f"Reduction: {spending_reduction:.1%}/15% ({reduction_score:.2f}), "
                f"Balance: {balance_score:.2f}. Total: {score:.2f}"
            )
        )

    @staticmethod
    def grade_hard(episode_stats: Dict) -> TaskGrade:
        """
        Grade 'predictive_budgeting_hard' task.
        
        Criteria (equal weights):
        1. savings_rate >= 0.25 (40%)
        2. days_on_budget >= 25 (30%)
        3. deferred_expenses >= 5 (20%)
        4. decision_quality (10%)
        
        Score: Weighted average of all criteria
        """
        savings_rate = episode_stats.get("savings_rate", 0.0)
        days_on_budget = episode_stats.get("days_on_budget", 0)
        deferred_expenses = len(episode_stats.get("deferred_expenses", []))
        overspend_count = episode_stats.get("overspend_count", 0)
        
        # Criterion 1: Aggressive savings (40%)
        savings_score = min(1.0, savings_rate / 0.25)
        
        # Criterion 2: Very tight budget adherence (30%)
        days_score = min(1.0, days_on_budget / 25)
        
        # Criterion 3: Strategic deferral (20%)
        defer_score = min(1.0, deferred_expenses / 5)
        
        # Criterion 4: Decision quality (10%) - penalize overspends
        decision_quality = max(0, 1.0 - (overspend_count * 0.1))
        decision_score = min(1.0, decision_quality)
        
        # Weighted average
        score = (
            savings_score * 0.40 +
            days_score * 0.30 +
            defer_score * 0.20 +
            decision_score * 0.10
        )
        
        passed = (
            savings_rate >= 0.25 and
            days_on_budget >= 25 and
            deferred_expenses >= 5
        )
        
        return TaskGrade(
            task_id="predictive_budgeting_hard",
            score=score,
            criteria_scores={
                "savings_rate": savings_score,
                "days_on_budget": days_score,
                "deferred_expenses": defer_score,
                "decision_quality": decision_score,
            },
            passed=passed,
            details=(
                f"Savings: {savings_rate:.1%}/25% ({savings_score:.2f}), "
                f"Days: {days_on_budget}/25 ({days_score:.2f}), "
                f"Deferred: {deferred_expenses}/5 ({defer_score:.2f}), "
                f"Quality: {decision_score:.2f}. Total: {score:.2f}"
            )
        )

    @staticmethod
    def grade_episode(task_id: str, episode_stats: Dict) -> TaskGrade:
        """Grade episode for given task."""
        if task_id == "budget_adherence_easy":
            return TaskGrader.grade_easy(episode_stats)
        elif task_id == "category_optimization_medium":
            return TaskGrader.grade_medium(episode_stats)
        elif task_id == "predictive_budgeting_hard":
            return TaskGrader.grade_hard(episode_stats)
        else:
            raise ValueError(f"Unknown task: {task_id}")


def save_grades(task_id: str, grades: List[TaskGrade], output_path: Path) -> None:
    """Save task grades to JSON file."""
    grades_dict = [
        {
            "task_id": g.task_id,
            "score": g.score,
            "criteria_scores": g.criteria_scores,
            "passed": g.passed,
            "details": g.details,
        }
        for g in grades
    ]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(grades_dict, f, indent=2)
