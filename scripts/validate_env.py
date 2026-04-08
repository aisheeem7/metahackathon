#!/usr/bin/env python3
"""
Validation script for OpenEnv compliance.
Tests that the environment meets OpenEnv spec.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from env.finance_env import PersonalExpenseOptimizer
from env.models import Observation, Action, Reward
from env.tasks import TaskGrader


def test_initialization():
    """Test environment initialization."""
    print("✓ Testing initialization...")
    try:
        env = PersonalExpenseOptimizer()
        print("  ✓ Environment created successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_reset():
    """Test reset functionality."""
    print("✓ Testing reset()...")
    try:
        env = PersonalExpenseOptimizer()
        reset_output = env.reset()
        obs = reset_output.observation
        
        assert isinstance(obs, Observation)
        assert obs.day == 1
        assert obs.total_balance == obs.monthly_income
        print(f"  ✓ reset() returns valid ResetOutput with Observation")
        print(f"    - Days remaining: {30 - obs.day}")
        print(f"    - Budget: ₹{obs.monthly_income}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step():
    """Test step functionality."""
    print("✓ Testing step()...")
    try:
        env = PersonalExpenseOptimizer()
        env.reset()
        
        action = Action(
            action_type="allocate_budget",
            allocations={"food": 300, "transport": 200, "shopping": 150, "entertainment": 100, "utilities": 250}
        )
        
        step_output = env.step(action)
        obs = step_output.observation
        reward = step_output.reward
        done = step_output.done
        info = step_output.info
        
        assert isinstance(obs, Observation)
        assert isinstance(reward, Reward)
        assert isinstance(done, bool)
        assert isinstance(info, dict)
        
        print(f"  ✓ step() returns valid StepOutput")
        print(f"    - Reward total: {reward.total:.2f}")
        print(f"    - Budget adherence: {reward.budget_adherence:.2f}")
        print(f"    - Done: {done}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state():
    """Test state functionality."""
    print("✓ Testing state()...")
    try:
        env = PersonalExpenseOptimizer()
        env.reset()
        
        state = env.state()
        assert isinstance(state, dict)
        assert "day" in state
        assert "total_budget" in state
        
        print(f"  ✓ state() returns valid dict")
        print(f"    - State keys: {list(state.keys())}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_action_types():
    """Test all action types."""
    print("✓ Testing action types...")
    try:
        env = PersonalExpenseOptimizer()
        env.reset()
        
        action_types = [
            Action(action_type="allocate_budget", allocations={"food": 300}),
            Action(action_type="adjust_category", category="food", amount=50),
            Action(action_type="set_savings_goal", target_percentage=0.25),
        ]
        
        for action in action_types:
            env.step(action)
            print(f"  ✓ {action.action_type}")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_graders():
    """Test task graders."""
    print("✓ Testing task graders...")
    try:
        grader = TaskGrader()
        
        episode_stats = {
            "days_on_budget": 7,
            "total_savings": 1000,
        }
        
        easy_grade = grader.grade_easy(episode_stats)
        assert 0.0 <= easy_grade.score <= 1.0
        print(f"  ✓ Easy task grader: score={easy_grade.score:.2f}")
        
        medium_grade = grader.grade_medium(episode_stats)
        assert 0.0 <= medium_grade.score <= 1.0
        print(f"  ✓ Medium task grader: score={medium_grade.score:.2f}")
        
        hard_grade = grader.grade_hard(episode_stats)
        assert 0.0 <= hard_grade.score <= 1.0
        print(f"  ✓ Hard task grader: score={hard_grade.score:.2f}")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("OpenEnv Validation Tests")
    print("="*60 + "\n")
    
    tests = [
        test_initialization,
        test_reset,
        test_step,
        test_state,
        test_action_types,
        test_task_graders,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print("="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    if passed == total:
        print("✓ All validation tests passed! Environment is OpenEnv compliant.")
        return 0
    else:
        print("✗ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
