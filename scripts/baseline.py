#!/usr/bin/env python3
"""
Baseline inference script for Personal Expense Optimizer.

Runs a smart agent (powered by OpenAI) against all 3 tasks.
Produces reproducible baseline scores on the environment.

Usage:
    python baseline.py
    
Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key
    OPENAI_MODEL: Model to use (default: gpt-4o-mini)
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

import openai

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env.finance_env import PersonalExpenseOptimizer
from env.models import Action, Observation
from env.tasks import TaskGrader


class LLMAgent:
    """Agent that uses OpenAI LLM to make spending decisions."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.conversation_history = []
    
    def reset(self):
        """Reset conversation history for new episode."""
        self.conversation_history = []
    
    def get_action(self, observation: Observation, task_description: str) -> Action:
        """
        Get action from LLM based on observation.
        
        Args:
            observation: Current environment observation
            task_description: Description of the task objective
            
        Returns:
            Valid Action from the model
        """
        # Format observation for the model
        obs_text = self._format_observation(observation)
        
        # Create prompt
        prompt = self._create_prompt(obs_text, task_description)
        
        # Add to conversation
        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })
        
        # Get response from model
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.conversation_history,
            temperature=0.7,
            max_tokens=500
        )
        
        assistant_message = response.choices[0].message.content
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Parse action from response
        action = self._parse_action(assistant_message, observation)
        return action
    
    def _format_observation(self, obs: Observation) -> str:
        """Format observation as readable text."""
        return f"""
Current Status (Day {obs.day}/30):
- Total Budget: ₹{obs.monthly_income:.2f}
- Total Balance: ₹{obs.total_balance:.2f}
- Current Savings: ₹{obs.current_savings:.2f}
- Savings Goal: {obs.savings_goal_percentage*100:.0f}%

Category Budgets:
{chr(10).join(f"  - {cat}: ₹{obs.category_budgets[cat]:.2f} (Spent: ₹{obs.category_spent[cat]:.2f}, Remaining: ₹{obs.category_remaining[cat]:.2f})" 
  for cat in obs.category_budgets)}

Recent Transactions:
{chr(10).join(f"  - {t.description}: ₹{t.amount:.2f} ({t.category})" for t in obs.recent_transactions[-3:]) if obs.recent_transactions else "  None yet"}

Performance:
- Days On Budget: {obs.days_on_budget}
- Overspend Count: {obs.overspend_count}
"""

    def _create_prompt(self, obs_text: str, task_description: str) -> str:
        """Create prompt for the model."""
        return f"""You are an intelligent personal finance advisor. Your goal: {task_description}

{obs_text}

Based on the current state, you must decide on ONE of these actions:

1. allocate_budget - Set budget for categories (format: allocate_budget: food=300, transport=200, ...)
2. adjust_category - Adjust budget for one category (format: adjust_category: category=food, amount=50)
3. set_savings_goal - Set target savings percentage (format: set_savings_goal: target_percentage=0.25)
4. defer_expense - Defer a discretionary expense (format: defer_expense: defer_days=7)

Respond ONLY with your decision in the exact format shown above. No explanations."""

    def _parse_action(self, response: str, obs: Observation) -> Action:
        """Parse action from model response."""
        response = response.strip().lower()
        
        # Default action if parsing fails
        default_action = Action(
            action_type="adjust_category",
            category="food",
            amount=-10
        )
        
        try:
            if "allocate_budget" in response:
                # Extract allocations
                allocations = {}
                for cat in obs.category_budgets.keys():
                    # Parse "category=amount" format
                    search_str = f"{cat}="
                    if search_str in response:
                        start_idx = response.find(search_str) + len(search_str)
                        end_idx = response.find(",", start_idx)
                        if end_idx == -1:
                            end_idx = len(response)
                        try:
                            amount = float(response[start_idx:end_idx].strip())
                            allocations[cat] = amount
                        except ValueError:
                            pass
                
                if allocations:
                    return Action(action_type="allocate_budget", allocations=allocations)
            
            elif "adjust_category" in response:
                # Extract category and amount
                lines = response.split("\n")
                category = None
                amount = 50
                for line in lines:
                    if "category=" in line:
                        category = line.split("category=")[1].split(",")[0].strip()
                    if "amount=" in line:
                        try:
                            amount = float(line.split("amount=")[1].split(",")[0].strip())
                        except ValueError:
                            pass
                
                if category and category in obs.category_budgets:
                    return Action(action_type="adjust_category", category=category, amount=amount)
            
            elif "set_savings_goal" in response:
                target = 0.2
                if "target_percentage=" in response:
                    try:
                        target = float(response.split("target_percentage=")[1].split(",")[0].split()[0].strip())
                    except ValueError:
                        pass
                return Action(action_type="set_savings_goal", target_percentage=target)
            
            elif "defer_expense" in response:
                days = 7
                if "defer_days=" in response:
                    try:
                        days = int(response.split("defer_days=")[1].split(",")[0].split()[0].strip())
                    except ValueError:
                        pass
                return Action(action_type="defer_expense", defer_days=days)
        
        except Exception as e:
            print(f"  Warning: Action parsing error - {e}")
        
        return default_action


def run_task(env: PersonalExpenseOptimizer, agent: LLMAgent, task_id: str, 
             task_description: str, max_days: int = 30) -> Dict[str, Any]:
    """
    Run a single task episode.
    
    Returns:
        Episode statistics for grading
    """
    print(f"\n  Running {task_id}...")
    
    agent.reset()
    reset_output = env.reset()
    obs = reset_output.observation
    
    total_reward = 0.0
    episode_stats = {
        "days_on_budget": 0,
        "total_savings": 0,
        "category_balance_score": 0.0,
    }
    
    for day in range(max_days):
        try:
            # Get action from agent
            action = agent.get_action(obs, task_description)
            
            # Step environment
            step_output = env.step(action)
            obs = step_output.observation
            reward = step_output.reward
            done = step_output.done
            
            total_reward += reward.total
            
            # Update stats
            episode_stats["days_on_budget"] = obs.days_on_budget
            episode_stats["total_savings"] = obs.current_savings
            
            if done:
                break
        
        except Exception as e:
            print(f"    Error on day {day+1}: {e}")
            break
    
    episode_stats["total_reward"] = total_reward
    return episode_stats


def main():
    """Run baseline inference on all 3 tasks."""
    
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return 1
    
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    print(f"Using model: {model}")
    
    # Task definitions
    tasks = {
        "budget_adherence_easy": {
            "description": "Stay within budget limits for 7 days. Be conservative with spending.",
            "max_days": 30
        },
        "category_optimization_medium": {
            "description": "Optimally allocate budget across 5 categories. Reduce spending by 15% while maintaining quality.",
            "max_days": 30
        },
        "predictive_budgeting_hard": {
            "description": "Predict expenses for the month and create a zero-based budget. Achieve 25% savings.",
            "max_days": 30
        }
    }
    
    # Initialize environment and agent
    env = PersonalExpenseOptimizer()
    agent = LLMAgent(model=model)
    
    # Run all tasks
    results = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "tasks": {}
    }
    
    print("\n" + "="*60)
    print("OpenEnv Baseline Inference")
    print("="*60)
    
    grader = TaskGrader()
    
    for task_id, task_config in tasks.items():
        print(f"\nTask: {task_id}")
        print(f"Description: {task_config['description']}")
        
        try:
            # Run episode
            episode_stats = run_task(
                env, agent, task_id, 
                task_config['description'],
                max_days=task_config['max_days']
            )
            
            # Grade task
            if "easy" in task_id:
                grade = grader.grade_easy(episode_stats)
            elif "medium" in task_id:
                grade = grader.grade_medium(episode_stats)
            else:
                grade = grader.grade_hard(episode_stats)
            
            results["tasks"][task_id] = {
                "score": grade.score,
                "passed": grade.passed,
                "details": grade.details,
                "criteria_scores": grade.criteria_scores,
                "episode_stats": episode_stats
            }
            
            print(f"  Score: {grade.score:.2f}")
            print(f"  Passed: {grade.passed}")
            print(f"  Details: {grade.details}")
        
        except Exception as e:
            print(f"  Error running task: {e}")
            import traceback
            traceback.print_exc()
            results["tasks"][task_id] = {
                "score": 0.0,
                "passed": False,
                "error": str(e)
            }
    
    # Calculate average score
    scores = [r["score"] for r in results["tasks"].values() if "score" in r]
    average_score = sum(scores) / len(scores) if scores else 0.0
    results["average_score"] = average_score
    
    # Save results
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    results_file = results_dir / "baseline_scores.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    print(f"Average Score: {average_score:.2f}")
    print(f"Results saved to: {results_file}")
    print("="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
