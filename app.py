"""
Flask backend: serves the web dashboard and all OpenEnv API endpoints.

OpenEnv-required endpoints
--------------------------
POST /api/env/reset          → { observation, info }
POST /api/env/step           → { observation, reward, done, info }
GET  /api/env/state          → current observation dict
POST /api/tasks/<id>/grade   → { task_id, score, difficulty, description }

Additional utility endpoints
-----------------------------
GET  /api/tasks              → list of all task definitions
GET  /health                 → liveness probe
GET  /                       → dashboard (HTML)
"""

import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Ensure project root is on path so `env.*` imports resolve correctly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from env.finance_env import FinanceEnv
from env.models import Action
from env.tasks import grade_task, TASKS

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder=str(PROJECT_ROOT / "frontend"), static_url_path="")
CORS(app)

# Single shared environment instance (reset per task run via /api/env/reset)
_env = FinanceEnv(seed=42)

# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def index():
    frontend_dir = PROJECT_ROOT / "frontend"
    if (frontend_dir / "index.html").exists():
        return send_from_directory(str(frontend_dir), "index.html")
    return jsonify({"name": "Smart Spend – Personal Expense Optimizer", "status": "running"}), 200

# ---------------------------------------------------------------------------
# OpenEnv core endpoints
# ---------------------------------------------------------------------------

@app.route("/api/env/reset", methods=["POST"])
def env_reset():
    """Reset the environment and return initial observation."""
    obs = _env.reset()
    return jsonify({
        "observation": obs.model_dump(),
        "info": {"day": obs.day, "monthly_income": obs.monthly_income},
    }), 200


@app.route("/api/env/step", methods=["POST"])
def env_step():
    """
    Accept an action JSON body, advance the environment one step.

    Expected body (all fields optional except action_type):
    {
        "action_type": "adjust_category",
        "category": "Food",
        "amount": 500,
        "defer_days": 0
    }
    """
    body = request.get_json(silent=True) or {}
    try:
        action = Action(**body)
    except Exception as exc:
        return jsonify({"error": f"Invalid action: {exc}"}), 400

    obs, reward, done = _env.step(action)
    return jsonify({
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": {"day": obs.day},
    }), 200


@app.route("/api/env/state", methods=["GET"])
def env_state():
    """Return current environment state without advancing it."""
    return jsonify(_env.state()), 200

# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    return jsonify({"tasks": list(TASKS.values())}), 200


@app.route("/api/tasks/<task_id>/grade", methods=["POST"])
def grade(task_id: str):
    """Grade the current environment state against the requested task."""
    result = grade_task(task_id, _env.state())
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result), 200
