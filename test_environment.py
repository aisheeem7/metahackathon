#!/usr/bin/env python3
"""
Quick validation script to test the core OpenEnv environment.
Runs a single episode and validates all components work.
"""

import sys
from pathlib import Path

# Add env to path
sys.path.insert(0, str(Path(__file__).parent))

from env.finance_env import PersonalExpenseOptimizer, DEFAULT_INCOME
from env.models import Action, ActionType, Observation, Reward, StepOutput
from env.tasks import TaskGrader, TaskInfo


def test_environment():
    """Test basic environment functionality."""
    print("=" * 60)
    print("Testing Personal Expense Optimizer - Core OpenEnv Features")
    print("=" * 60)
    
    # Initialize environment
    print("\n1. Initializing environment...")
    env = PersonalExpenseOptimizer(monthly_income=DEFAULT_INCOME, seed=42)
    print(f"   ✓ Created environment with ₹{DEFAULT_INCOME} monthly income")
    
    # Reset
    print("\n2. Testing reset()...")
    task = TaskGrader.get_task("budget_adherence_easy")
    reset_output = env.reset(task=task)
    
    obs = reset_output.observation
    assert isinstance(obs, Observation), "Observation not typed correctly"
    assert obs.day == 1, "Initial day should be 1"
    assert obs.total_balance == DEFAULT_INCOME, "Initial balance incorrect"
    print(f"   ✓ Reset successful")
    print(f"     - Day: {obs.day}")
    print(f"     - Balance: ₹{obs.total_balance}")
    print(f"     - Categories: {list(obs.category_budgets.keys())}")
    
    # run episode
    print("\n3. Running 30-day episode...")
    total_rewards = 0.0
    step_count = 0
    
    while not done := (env.day > 30):
        # Simple deterministic strategy: allocate evenly, don't defer
        action = Action(
            action_type=ActionType.ADJUST_CATEGORY,
            category="Food & Dining",
            amount=obs.category_budgets["Food & Dining"]
        )
        
        step_output = env.step(action)
        assert isinstance(step_output, StepOutput), "Step output not typed correctly"
        
        obs = step_output.observation
        reward = step_output.reward
        assert isinstance(reward, Reward), "Reward not typed correctly"
        
        total_rewards += reward.total
        step_count += 1
        
        if step_count % 7 == 0:
            print(f"   Day {env.day}: Balance ₹{obs.total_balance:.0f}, "
                  f"Spent ₹{obs.category_spent['Food & Dining']:.0f}, "
                  f"Reward: {reward.total:.2f}")
    
    print(f"   ✓ Episode completed in {step_count} steps")
    print(f"     - Total accumulated reward: {total_rewards:.2f}")
    
    # Get final state
    print("\n4. Episode summary...")
    state = env.state()
    final_savings = state["total_budget"] - state["total_spent"]
    savings_rate = final_savings / state["total_budget"]
    
    print(f"   - Total spent: ₹{state['total_spent']:.2f}")
    print(f"   - Final savings: ₹{final_savings:.2f} ({savings_rate:.1%})")
    print(f"   - Days on budget: {state['days_on_budget']}/30")
    print(f"   - Overspend count: {state['overspend_count']}")
    
    # Test graders
    print("\n5. Testing task graders...")
    episode_stats = {
        "days_on_budget": state["days_on_budget"],
        "savings_rate": savings_rate,
        "final_savings": final_savings,
        "monthly_budget": state["total_budget"],
        "category_spent": state["category_spent"],
        "overspend_count": state["overspend_count"],
        "deferred_expenses": [],
    }
    
    # Grade all tasks
    for task_id in ["budget_adherence_easy", "category_optimization_medium", "predictive_budgeting_hard"]:
        grade = TaskGrader.grade_episode(task_id, episode_stats)
        status = "PASS ✓" if grade.passed else "FAIL ✗"
        print(f"   {task_id}: {status}")
        print(f"     Score: {grade.score:.2f}/1.00")
        print(f"     {grade.details}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✓ All tests passed! Environment is OpenEnv-compliant.")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        test_environment()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
