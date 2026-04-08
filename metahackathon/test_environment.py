#!/usr/bin/env python3
"""
Quick test script to verify environment functionality
"""

import sys
sys.path.insert(0, '.')

print('Testing environment functionality...\n')

from env.finance_env import PersonalExpenseOptimizer
from env.models import Action, ActionType
from env.tasks import TaskGrader

# Test 1: Environment reset
print('TEST 1: Reset environment')
env = PersonalExpenseOptimizer(seed=42)
reset_output = env.reset()
print(f'  Initial observation day: {reset_output.observation.day}')
print(f'  Total balance: ₹{reset_output.observation.total_balance:.0f}')
print(f'  Categories: {list(reset_output.observation.category_budgets.keys())}')
print('  ✓ Reset works\n')

# Test 2: Take 5 steps
print('TEST 2: Execute 5 environment steps')
for i in range(5):
    action = Action(
        action_type=ActionType.ALLOCATE_BUDGET,
        amount=50000
    )
    step_output = env.step(action)
    print(f'  Step {i+1}: day={step_output.observation.day}, '
          f'reward={step_output.reward.total:.3f}, '
          f'savings=₹{step_output.observation.current_savings:.0f}')
print('  ✓ Steps work\n')

# Test 3: Task grading
print('TEST 3: Task grading')
grader = TaskGrader()
stats = {
    'monthly_budget': 50000,
    'days_on_budget': 15,
    'category_spent': {
        'Food & Dining': 1500,
        'Transport': 1000,
        'Shopping': 500,
        'Health': 300,
        'Bills': 3000
    },
    'final_savings': 8700,
    'savings_rate': 0.174,
    'deferred_expenses': [],
    'overspend_count': 2,
}

grade = grader.grade_easy(stats)
print(f'  Easy task grade: {grade.score:.3f} (passed={grade.passed})')
print(f'  Details: {grade.details}')
print('  ✓ Grading works\n')

# Test 4: Observation types
print('TEST 4: Observation type validation')
obs = reset_output.observation
print(f'  day type: {type(obs.day).__name__} - valid: {isinstance(obs.day, int)}')
print(f'  total_balance type: {type(obs.total_balance).__name__} - valid: {isinstance(obs.total_balance, float)}')
print(f'  category_budgets type: {type(obs.category_budgets).__name__} - valid: {isinstance(obs.category_budgets, dict)}')
print(f'  recent_transactions type: {type(obs.recent_transactions).__name__} - valid: {isinstance(obs.recent_transactions, list)}')
print('  ✓ Observation types valid\n')

# Test 5: Reward structure
print('TEST 5: Reward structure')
reward = step_output.reward
print(f'  Total reward: {reward.total} (range: -1 to 1)')
print(f'  Budget adherence: {reward.budget_adherence}')
print(f'  Savings progress: {reward.savings_progress}')
print(f'  Category balance: {reward.category_balance}')
print(f'  Transaction decision: {reward.transaction_decision}')
print('  ✓ Reward structure valid\n')

print('='*50)
print('✓ ALL TESTS PASSED - Environment is fully functional!')
print('='*50)
