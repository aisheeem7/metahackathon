#!/usr/bin/env python3
"""
Test Flask API endpoints
"""

import sys
sys.path.insert(0, '.')

print('Testing Flask API endpoints...\n')

from backend.app import app
import json

# Create test client
client = app.test_client()

# Test 1: Health check
print('TEST 1: Health check')
response = client.get('/health')
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Response: {data}')
assert response.status_code == 200
assert data['status'] == 'healthy'
print('  ✓ Health check works\n')

# Test 2: Environment info
print('TEST 2: Environment info')
response = client.get('/api/env/info')
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Environment: {data["name"]}')
print(f'  Action space: {data["action_space"]["actions"]}')
print('  ✓ Env info works\n')

# Test 3: Reset environment
print('TEST 3: Reset environment')
response = client.post('/api/env/reset')
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Initial day: {data["observation"]["day"]}')
print(f'  Initial balance: ₹{data["observation"]["total_balance"]:.0f}')
assert response.status_code == 200
assert data["observation"]["day"] == 1
print('  ✓ Reset works\n')

# Test 4: Take a step (adjust_category)
print('TEST 4: Step action (adjust_category)')
response = client.post('/api/env/step', 
    json={
        'action_type': 'adjust_category',
        'category': 'Food & Dining',
        'amount': 8000
    }
)
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Day: {data["observation"]["day"]}')
print(f'  Reward: {data["reward"]["total"]:.3f}')
assert response.status_code == 200
assert data["observation"]["day"] == 2
print('  ✓ Step works\n')

# Test 5: Set savings goal
print('TEST 5: Step action (set_savings_goal)')
response = client.post('/api/env/step',
    json={
        'action_type': 'set_savings_goal',
        'amount': 25
    }
)
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Savings goal: {data["observation"]["savings_goal_percentage"]*100:.0f}%')
assert response.status_code == 200
print('  ✓ Set savings goal works\n')

# Test 6: Defer expense
print('TEST 6: Step action (defer_expense)')
response = client.post('/api/env/step',
    json={
        'action_type': 'defer_expense',
        'defer_days': 7
    }
)
data = response.get_json()
print(f'  Status: {response.status_code}')
assert response.status_code == 200
print('  ✓ Defer expense works\n')

# Test 7: Get state
print('TEST 7: Get environment state')
response = client.get('/api/env/state')
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Current day: {data["day"]}')
print(f'  Total spent: ₹{data["total_spent"]:.0f}')
print(f'  Days on budget: {data["days_on_budget"]}')
assert response.status_code == 200
print('  ✓ Get state works\n')

# Test 8: Get tasks
print('TEST 8: Get all tasks')
response = client.get('/api/tasks')
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Tasks: {list(data.keys())}')
assert response.status_code == 200
assert len(data) >= 3
print(f'  Task 1: {data["budget_adherence_easy"]["difficulty"]} - {data["budget_adherence_easy"]["description"][:50]}...')
print('  ✓ Get tasks works\n')

# Test 9: Grade easy task
print('TEST 9: Grade task (budget_adherence_easy)')
response = client.post('/api/tasks/budget_adherence_easy/grade',
    json={
        'monthly_budget': 50000,
        'days_on_budget': 10,
        'category_spent': {},
        'deferred_expenses': [],
        'overspend_count': 0
    }
)
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Score: {data["score"]:.3f}')
print(f'  Passed: {data["passed"]}')
print(f'  Details: {data["details"]}')
assert response.status_code == 200
assert 0.0 <= data['score'] <= 1.0
print('  ✓ Grade task works\n')

# Test 10: Grade hard task
print('TEST 10: Grade task (predictive_budgeting_hard)')
response = client.post('/api/tasks/predictive_budgeting_hard/grade',
    json={
        'monthly_budget': 50000,
        'days_on_budget': 26,
        'savings_rate': 0.26,
        'deferred_expenses': [('Food', 300), ('Shopping', 500), ('Food', 200), ('Shopping', 400), ('Food', 150)],
        'category_spent': {
            'Food & Dining': 5000,
            'Transport': 3000,
            'Shopping': 2000,
            'Health': 1500,
            'Bills': 15000
        },
        'overspend_count': 1
    }
)
data = response.get_json()
print(f'  Status: {response.status_code}')
print(f'  Score: {data["score"]:.3f}')
print(f'  Passed: {data["passed"]}')
print(f'  Details: {data["details"]}')
assert response.status_code == 200
assert 0.0 <= data['score'] <= 1.0
print('  ✓ Grade hard task works\n')

print('='*60)
print('✓ ALL API TESTS PASSED - Backend is fully functional!')
print('='*60)
