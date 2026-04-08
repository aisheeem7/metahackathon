#!/usr/bin/env python3
"""
Baseline inference script for Personal Expense Optimizer environment.
Runs an LLM agent against all 3 tasks and produces reproducible baseline scores.

Usage:
    export OPENAI_API_KEY="sk-..."
    python baseline.py

This script demonstrates:
- Environment initialization and reset
- Structured action generation via LLM
- Episode execution for all 3 tasks
- Task grading and score calculation
- Result logging and reproducibility
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from env.finance_env import PersonalExpenseOptimizer
from env.models import Action, ActionType
from env.tasks import TaskGrader

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)


class BaselineAgent:
    """
    LLM-based agent for budget optimization using structured prompting.
    Uses OpenAI API to generate actions given environment state.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        """
        Initialize agent with OpenAI client.
        
        Args:
            model: OpenAI model to use (default: gpt-4o-mini for cost/speed)
            temperature: Sampling temperature (0.0-1.0)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Export it: export OPENAI_API_KEY='sk-...'"
            )
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.api_call_count = 0
        self.total_api_cost = 0.0
    
    def _format_observation(self, obs: Dict[str, Any]) -> str:
        """Format observation into readable text for LLM."""
        text = f"""
Current Budget State (Day {obs['day']}/30):
- Total Balance: ₹{obs['total_balance']:.0f}
- Current Savings: ₹{obs['current_savings']:.0f} ({obs['current_savings']/obs['monthly_income']*100:.1f}%)
- Savings Goal: {obs['savings_goal_percentage']*100:.0f}%
- Days On Budget: {obs['days_on_budget']}/30
- Over-spends: {obs['overspend_count']}

Category Budgets:
"""
        for cat in ["Food & Dining", "Transport", "Shopping", "Health", "Bills"]:
            spent = obs['category_spent'].get(cat, 0)
            budget = obs['category_budgets'].get(cat, 0)
            pct = (spent / max(1, budget)) * 100 if budget > 0 else 0
            text += f"  {cat}: ₹{spent:.0f}/₹{budget:.0f} ({pct:.0f}%)\n"
        
        if obs['pending_transaction']:
            txn = obs['pending_transaction']
            text += f"""
Pending Transaction:
  Category: {txn['category']}
  Amount: ₹{txn['amount']}
  Description: {txn['description']}
  Discretionary: {txn['is_discretionary']}
"""
        
        return text
    
    def _parse_action(self, response_text: str) -> Action:
        """
        Parse LLM response into Action object.
        Tries to extract JSON action format or parse natural language.
        """
        # Try to extract JSON action
        try:
            # Look for JSON block
            import re
            json_match = re.search(r'\{.*?"action_type".*?\}', response_text, re.DOTALL)
            if json_match:
                action_dict = json.loads(json_match.group())
                return Action(
                    action_type=action_dict['action_type'],
                    category=action_dict.get('category'),
                    amount=action_dict.get('amount'),
                    defer_days=action_dict.get('defer_days')
                )
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Fallback: default to allocate_budget
        return Action(
            action_type=ActionType.ALLOCATE_BUDGET,
            amount=50000
        )
    
    def get_action(self, obs: Dict[str, Any], task_description: str) -> Action:
        """
        Query LLM for next action given current observation.
        
        Args:
            obs: Current observation from environment
            task_description: Description of current task
            
        Returns:
            Action object to execute
        """
        obs_text = self._format_observation(obs)
        
        prompt = f"""You are an AI agent optimizing personal finances. Your task:

{task_description}

Current State:
{obs_text}

Available Actions:
1. allocate_budget(amount): Adjust overall monthly budget
2. adjust_category(category, amount): Change budget for specific category
3. set_savings_goal(amount): Set savings goal percentage (0-50%)
4. defer_expense(): Defer current discretionary expense

Respond in JSON format:
{{"action_type": "action_name", "category": "if_needed", "amount": "if_needed"}}

Choose the action that best helps achieve the task. Be strategic and proactive."""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            self.api_call_count += 1
            
            # Estimate cost (rough approximation)
            # gpt-4o-mini: $0.15/1M input, $0.60/1M output
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.total_api_cost += (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000
            
            response_text = response.content[0].text
            action = self._parse_action(response_text)
            
            return action
            
        except Exception as e:
            print(f"ERROR querying OpenAI: {e}")
            # Fallback action
            return Action(action_type=ActionType.ALLOCATE_BUDGET, amount=50000)
    
    def print_stats(self):
        """Print API usage statistics."""
        print(f"\nAPI Usage:")
        print(f"  Total Calls: {self.api_call_count}")
        print(f"  Estimated Cost: ${self.total_api_cost:.4f}")


def run_episode(
    task_id: str,
    agent: BaselineAgent,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Run one complete episode for a given task.
    
    Args:
        task_id: Task identifier
        agent: BaselineAgent instance
        seed: Random seed for reproducibility
        
    Returns:
        Episode results including score
    """
    # Initialize environment
    env = PersonalExpenseOptimizer(seed=seed)
    grader = TaskGrader()
    task_info = grader.get_task(task_id)
    
    # Reset
    reset_output = env.reset(task=task_info)
    obs = reset_output.observation.model_dump(mode='json')
    
    total_reward = 0.0
    step_count = 0
    episode_stats = {
        "monthly_budget": env.monthly_budget,
        "days_on_budget": 0,
        "category_spent": env.category_spent.copy(),
        "deferred_expenses": [],
        "overspend_count": 0,
    }
    
    print(f"\n{'='*60}")
    print(f"Running Task: {task_id} ({task_info.difficulty})")
    print(f"Description: {task_info.description}")
    print(f"{'='*60}\n")
    
    # Episode loop
    while not obs['total_balance'] <= 0 and step_count < 30:
        # Get action from agent
        action = agent.get_action(obs, task_info.description)
        
        # Execute action
        step_output = env.step(action)
        obs = step_output.observation.model_dump(mode='json')
        reward = step_output.reward.model_dump(mode='json')
        done = step_output.done
        
        total_reward += reward['total']
        step_count += 1
        
        # Update stats
        episode_stats['days_on_budget'] = obs['days_on_budget']
        episode_stats['category_spent'] = obs['category_spent'].copy()
        episode_stats['overspend_count'] = obs['overspend_count']
        episode_stats['deferred_expenses'] = env.deferred_expenses.copy()
        
        print(f"Day {step_count}: Reward={reward['total']:+.3f} | "
              f"Balance=₹{obs['total_balance']:.0f} | "
              f"Savings={obs['current_savings']:.0f}")
        
        if done:
            break
    
    # Final calculations
    final_savings = env.monthly_budget - env.total_spent
    episode_stats['final_savings'] = final_savings
    episode_stats['savings_rate'] = final_savings / env.monthly_budget
    
    # Grade the episode
    grade = grader.grade_episode(task_id, episode_stats)
    
    return {
        "task_id": task_id,
        "difficulty": task_info.difficulty,
        "steps": step_count,
        "total_reward": total_reward,
        "avg_reward": total_reward / step_count if step_count > 0 else 0,
        "final_savings": final_savings,
        "savings_rate": episode_stats['savings_rate'],
        "days_on_budget": episode_stats['days_on_budget'],
        "score": grade.score,
        "passed": grade.passed,
        "details": grade.details,
        "criteria_scores": grade.criteria_scores
    }


def main():
    """Main entry point for baseline evaluation."""
    parser = argparse.ArgumentParser(
        description="Baseline inference for Personal Expense Optimizer"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (default: 0.7)"
    )
    parser.add_argument(
        "--task",
        choices=["easy", "medium", "hard", "all"],
        default="all",
        help="Which task(s) to run (default: all)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--output",
        default="baseline_results.json",
        help="Output file for results (default: baseline_results.json)"
    )
    
    args = parser.parse_args()
    
    # Validate API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Export it: export OPENAI_API_KEY='sk-...'")
        sys.exit(1)
    
    # Initialize agent
    try:
        agent = BaselineAgent(model=args.model, temperature=args.temperature)
        print(f"Initialized agent with model: {args.model}")
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    # Map tasks
    task_map = {
        "easy": "budget_adherence_easy",
        "medium": "category_optimization_medium",
        "hard": "predictive_budgeting_hard",
    }
    
    if args.task == "all":
        tasks = list(task_map.values())
    else:
        tasks = [task_map[args.task]]
    
    # Run episodes
    results = []
    start_time = time.time()
    
    for task_id in tasks:
        try:
            result = run_episode(task_id, agent, seed=args.seed)
            results.append(result)
        except Exception as e:
            print(f"ERROR running task {task_id}: {e}")
            import traceback
            traceback.print_exc()
    
    elapsed = time.time() - start_time
    
    # Print summary
    print(f"\n{'='*60}")
    print("BASELINE EVALUATION RESULTS")
    print(f"{'='*60}\n")
    
    total_score = 0
    for result in results:
        print(f"Task: {result['task_id']} ({result['difficulty']})")
        print(f"  Score: {result['score']:.3f} (passed: {result['passed']})")
        print(f"  Savings Rate: {result['savings_rate']:.1%}")
        print(f"  Days On Budget: {result['days_on_budget']}/30")
        print(f"  Final Savings: ₹{result['final_savings']:.0f}")
        print(f"  Details: {result['details']}")
        print()
        total_score += result['score']
    
    avg_score = total_score / len(results) if results else 0
    print(f"Average Score (all tasks): {avg_score:.3f}")
    print(f"Total Elapsed Time: {elapsed:.1f}s")
    
    agent.print_stats()
    
    # Save results to JSON
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": args.model,
            "temperature": args.temperature,
            "seed": args.seed,
            "elapsed_seconds": elapsed,
            "results": results,
            "average_score": avg_score,
            "api_calls": agent.api_call_count,
            "estimated_cost": agent.total_api_cost
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    
    # Exit with success if all tasks passed
    if all(r['passed'] for r in results):
        print("\n✓ All tasks passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {len([r for r in results if not r['passed']])} task(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
