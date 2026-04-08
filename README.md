# Personal Expense Optimizer - OpenEnv Environment

<img src="https://img.shields.io/badge/OpenEnv-compliant-green" alt="OpenEnv Compliant" />
<img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+" />
<img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT License" />

## Overview

**Personal Expense Optimizer** is a real-world RL environment that simulates intelligent personal finance decision-making. Agents must optimize spending across budget categories while achieving savings goals—a task humans perform daily.

### Real-World Motivation

Personal finance is a complex, high-stakes domain where:
- People receive real transactions via SMS notifications
- Budget constraints are strict (income is fixed)
- Multiple competing objectives (save money, maintain lifestyle quality)
- Consequences of poor decisions compound over time

This environment models the core challenge: **given economic constraints and transaction patterns, how do agents make optimal spending decisions?**

---

## Environment Details

### Observation Space

The agent receives a structured observation at each step:

```python
class Observation(BaseModel):
    day: int                                  # Current day (1-30)
    total_balance: float                      # Remaining budget in INR
    category_budgets: Dict[str, float]       # Budget allocated per category
    category_spent: Dict[str, float]         # Already spent per category
    category_remaining: Dict[str, float]     # Remaining per category
    recent_transactions: List[Transaction]   # Last 5 transactions
    pending_transaction: Optional[Transaction] # Current transaction to decide on
    monthly_income: float                     # Monthly income (₹50,000)
    savings_goal_percentage: float            # Target savings % (20% default)
    current_savings: float                    # Amount saved so far
    days_on_budget: int                       # Days stayed within limits
    overspend_count: int                      # Times exceeded category budget
```

### Action Space

Agents choose from 4 action types:

| Action | Parameters | Purpose |
|--------|-----------|---------|
| `allocate_budget` | `allocations: Dict[str, float]` | Set monthly budget per category |
| `adjust_category` | `category: str, amount: float` | Increase/decrease single category budget |
| `set_savings_goal` | `target_percentage: float` | Set target savings (0.0-1.0) |
| `defer_expense` | `defer_days: int` | Defer discretionary expense to later |

### Reward Function

**Reward provides partial progress signals**:

```python
class Reward(BaseModel):
    total: float                    # Total reward (-1.0 to 1.0)
    budget_adherence: float         # Reward for staying in budget
    savings_progress: float         # Reward for meeting savings goal
    category_balance: float         # Reward for balanced spending
    transaction_decision: float     # Reward for smart decisions
    overspend_penalty: float        # Penalty for exceeding limits
```

---

## Tasks

### Task 1: Budget Adherence (Easy)
**Objective:** Stay within budget limits for 7+ days  
**Grading:** `score = min(1.0, days_on_budget / 7)`  
**Baseline:** 0.95

### Task 2: Category Optimization (Medium)
**Objective:** Optimize allocation + reduce spending 15% while maintaining balance  
**Grading:** Multi-criterion (allocation score + reduction + adherence)  
**Baseline:** 0.68

### Task 3: Predictive Budgeting (Hard)
**Objective:** Forecast expenses, zero-based budget, achieve 25% savings  
**Grading:** Multi-criterion (forecast accuracy + savings achievement + adherence)  
**Baseline:** 0.62
---

## Setup & Installation

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Validate Environment
```bash
python scripts/validate_env.py
```

Expected output: `✓ All validation tests passed! Environment is OpenEnv compliant.`

---

## Usage

### Python API
```python
from env.finance_env import PersonalExpenseOptimizer
from env.models import Action

env = PersonalExpenseOptimizer()
reset_output = env.reset()
observation = reset_output.observation

action = Action(
    action_type="allocate_budget",
    allocations={"food": 8000, "transport": 3000}
)
step_output = env.step(action)
print(f"Reward: {step_output.reward.total:.2f}")
```

### Flask Web Server
```bash
python -m backend.app
# Open http://localhost:5000
```

### REST API
```bash
# Reset
curl -X POST http://localhost:5000/api/env/reset

# Step
curl -X POST http://localhost:5000/api/env/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "allocate_budget", "allocations": {"food": 8000}}'

# Grade task
curl -X POST http://localhost:5000/api/tasks/budget_adherence_easy/grade \
  -H "Content-Type: application/json" \
  -d '{"days_on_budget": 9}'
```

---

## Baseline Scores

| Task | Difficulty | Score |
|------|-----------|-------|
| Budget Adherence | Easy | 0.95 |
| Category Optimization | Medium | 0.68 |
| Predictive Budgeting | Hard | 0.62 |
| **Average** | - | **0.75** |

### Run Baseline
```bash
export OPENAI_API_KEY="sk-..."
python scripts/baseline.py
```

Results saved to `results/baseline_scores.json`

---

## Docker Deployment

```bash
docker build -t expense-optimizer .
docker run -p 5000:5000 expense-optimizer
curl http://localhost:5000/health
```

---

## Project Structure
```
├── env/
│   ├── models.py          # Pydantic types
│   ├── finance_env.py     # Main environment
│   └── tasks.py           # Task graders
├── backend/
│   └── app.py             # Flask + OpenEnv API
├── scripts/
│   ├── validate_env.py    # Tests
│   └── baseline.py        # Baseline inference
├── openenv.yaml           # Metadata
└── Dockerfile
```

---

## OpenEnv Compliance

✅ Full OpenEnv spec compliance:
- Typed Pydantic models
- `reset()`, `step()`, `state()` methods
- Reward range: [-1.0, 1.0]
- 3+ tasks with deterministic graders
- All validation tests passing
