import os
import json
import time
import requests
from openai import OpenAI

# Environment configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Local environment endpoint (where the Flask app is running)
# By default, we assume it's running locally for the inference script to talk to
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)

def log_start(task_id):
    print(f"\n[START] Task: {task_id}")

def log_step(step, observation, action, reward):
    log_entry = {
        "step": step,
        "observation": observation,
        "action": action,
        "reward": reward
    }
    print(f"[STEP] {json.dumps(log_entry)}")

def log_end(task_id, final_score, metrics):
    summary = {
        "task_id": task_id,
        "score": final_score,
        "metrics": metrics
    }
    print(f"[END] {json.dumps(summary)}")

def get_llm_action(observation):
    """Ask LLM to decide on an action based on observation."""
    prompt = f"""
    You are a personal finance assistant. Optimize the user's spending.
    Current Day: {observation['day']}
    Total Balance: {observation['total_balance']}
    Monthly Income: {observation['monthly_income']}
    Savings Goal: {observation['savings_goal_percentage']*100}%
    
    Category Budgets: {json.dumps(observation['category_budgets'])}
    Category Spent: {json.dumps(observation['category_spent'])}
    
    Pending Transaction: {json.dumps(observation['pending_transaction'])}
    
    Choose an action from: allocate_budget, adjust_category, set_savings_goal, defer_expense.
    Respond with JSON: {{"action_type": "...", "category": "...", "amount": 0, "defer_days": 0}}
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        # Fallback action
        return {"action_type": "adjust_category", "category": "Bills", "amount": 1000}

def run_task(task_id):
    log_start(task_id)
    
    # 1. Reset
    res = requests.post(f"{ENV_URL}/api/env/reset")
    data = res.json()
    observation = data['observation']
    
    done = False
    step = 0
    total_reward = 0
    
    while not done and step < 30:
        # 2. Get LLM decision
        action = get_llm_action(observation)
        
        # 3. Step
        res = requests.post(f"{ENV_URL}/api/env/step", json=action)
        step_data = res.json()
        
        observation = step_data['observation']
        reward = step_data['reward']
        done = step_data['done']
        total_reward += reward['total']
        
        log_step(step, observation, action, reward)
        step += 1
        
    # 4. Grade
    grade_res = requests.post(f"{ENV_URL}/api/tasks/{task_id}/grade")
    grade_data = grade_res.json()
    
    log_end(task_id, grade_data.get('score', 0), grade_data)
    return grade_data.get('score', 0)

if __name__ == "__main__":
    tasks = ["budget_adherence_easy", "category_optimization_medium", "predictive_budgeting_hard"]
    scores = []
    
    for task_id in tasks:
        score = run_task(task_id)
        scores.append(score)
        
    print(f"\nFinal Baseline Cumulative Score: {sum(scores)/len(scores):.4f}")
