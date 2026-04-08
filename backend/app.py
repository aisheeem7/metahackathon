from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import json
from pathlib import Path

# Add env to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from env.finance_env import PersonalExpenseOptimizer
from env.models import Action, TaskInfo
from env.tasks import TaskGrader

# Configure Flask to serve static files from frontend folder
frontend_folder = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app = Flask(__name__, static_folder=frontend_folder, static_url_path='')
CORS(app)

# Initialize environment and grader
env = PersonalExpenseOptimizer()
grader = TaskGrader()
current_episode_stats = {}

@app.route('/')
def home():
    return send_from_directory(frontend_folder, 'index.html')


# ============= OpenEnv API Endpoints =============

@app.route('/api/env/info', methods=['GET'])
def env_info():
    """Get environment metadata."""
    return jsonify({
        "name": "personal-expense-optimizer",
        "version": "1.0.0",
        "description": "Real-world task: Personal expense optimization using SMS transaction simulation",
        "action_space": {
            "type": "categorical",
            "actions": ["allocate_budget", "adjust_category", "set_savings_goal", "defer_expense"]
        },
        "observation_space": {
            "type": "dict",
            "fields": {
                "day": "int (1-30)",
                "total_balance": "float",
                "category_budgets": "dict[str, float]",
                "category_spent": "dict[str, float]",
                "recent_transactions": "list[Transaction]",
                "monthly_income": "float",
                "savings_goal_percentage": "float"
            }
        },
        "reward_range": [-1.0, 1.0]
    })


@app.route('/api/env/reset', methods=['POST'])
def reset_env():
    """Reset environment to initial state."""
    global current_episode_stats
    current_episode_stats = {}
    
    try:
        reset_output = env.reset()
        
        # Convert observation to JSON-serializable dict
        obs_dict = reset_output.observation.model_dump(mode='json')
        
        return jsonify({
            "observation": obs_dict,
            "info": reset_output.info
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/env/step', methods=['POST'])
def step_env():
    """Execute one step in the environment."""
    try:
        action_data = request.json
        
        # Parse action
        action_type = action_data.get('action_type')
        
        # Create Action object based on type
        if action_type == 'allocate_budget':
            action = Action(
                action_type='allocate_budget',
                allocations=action_data.get('allocations', {})
            )
        elif action_type == 'adjust_category':
            action = Action(
                action_type='adjust_category',
                category=action_data.get('category'),
                amount=action_data.get('amount', 0)
            )
        elif action_type == 'set_savings_goal':
            action = Action(
                action_type='set_savings_goal',
                target_percentage=action_data.get('target_percentage', 0.2)
            )
        elif action_type == 'defer_expense':
            action = Action(
                action_type='defer_expense',
                defer_days=action_data.get('defer_days', 7)
            )
        else:
            return jsonify({"error": f"Unknown action type: {action_type}"}), 400
        
        # Step environment
        step_output = env.step(action)
        
        # Update stats
        obs = step_output.observation
        current_episode_stats['days_on_budget'] = obs.days_on_budget
        current_episode_stats['total_savings'] = obs.current_savings
        current_episode_stats['total_spent'] = obs.current_savings
        
        # Convert to JSON-serializable format
        obs_dict = step_output.observation.model_dump(mode='json')
        reward_dict = step_output.reward.model_dump(mode='json')
        
        return jsonify({
            "observation": obs_dict,
            "reward": reward_dict,
            "done": step_output.done,
            "info": step_output.info
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/env/state', methods=['GET'])
def get_state():
    """Get current environment state."""
    try:
        state = env.state()
        return jsonify(state)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all available tasks."""
    return jsonify({
        task_id: {
            "id": task_id,
            "difficulty": task.difficulty,
            "description": task.description,
            "success_criteria": task.success_criteria
        }
        for task_id, task in grader.TASKS.items()
    })


@app.route('/api/tasks/<task_id>/grade', methods=['POST'])
def grade_task(task_id):
    """Grade the completed task."""
    try:
        episode_stats = request.json or current_episode_stats
        
        if task_id not in grader.TASKS:
            return jsonify({"error": f"Unknown task: {task_id}"}), 400
        
        # Grade based on task type
        if "easy" in task_id:
            grade = grader.grade_easy(episode_stats)
        elif "medium" in task_id:
            grade = grader.grade_medium(episode_stats)
        elif "hard" in task_id:
            grade = grader.grade_hard(episode_stats)
        else:
            return jsonify({"error": "Unknown task difficulty"}), 400
        
        return jsonify({
            "task_id": grade.task_id,
            "score": grade.score,
            "passed": grade.passed,
            "details": grade.details,
            "criteria_scores": grade.criteria_scores
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True)
