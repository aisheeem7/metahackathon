# Smart Spend - Your Personal Finance Tracker

**Smart Spend** is a real-world task environment and agentic solution for optimizing personal finances via automated transaction detection and smart budget management. Built for compliance with the OpenEnv specification and optimized for Hugging Face Spaces.

## 🌟 Overview

Smart Spend combines a modern, consumer-facing finance dashboard with a robust environment for AI agents to learn optimal financial decision-making.

- **For Users**: A clean, intuitive dashboard to track expenses, manage budgets in INR, and visualize spending patterns.
- **For Agents**: An OpenEnv-compliant reinforcement learning environment where agents manage a monthly ₹50,000 budget, processing simulated SMS transactions and making strategic financial decisions.

### Key Features
- **Auto SMS Detection**: Simulated real-time detection of transactions from bank SMS notifications.
- **Gamified Experience**: Earn badges (Saver, Streak Master, Budget Hero) for meeting financial goals.
- **Smart Analytics**: Detailed breakdown of spending by category and time periods using Chart.js.
- **OpenEnv Specification**: Full support for `step()`, `reset()`, and `state()` endpoints with typed Pydantic models.
- **Graded Tasks**: Includes 3 standardized evaluation tasks (Easy, Medium, Hard) with precise 0.0-1.0 scoring.

---

## 🏗️ Architecture

- **Frontend**: Single Page Application (HTML5/Vanilla CSS/JavaScript) with Chart.js visualization.
- **Backend API**: Flask-based server providing the web dashboard and OpenEnv API endpoints.
- **Environment Logic**:
    - `env/finance_env.py`: Core logic for the expense optimization task.
    - `env/models.py`: Typed definitions for Action, Observation, and Reward.
    - `env/tasks.py`: Task definitions and deterministic graders.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- OpenAI-compatible API access (for inference)

### Local Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/aisheeem7/metahackathon.git
   cd metahackathon
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the application:
   ```bash
   python app.py
   ```
   Access the dashboard at `http://localhost:7860`.

### Using Docker
```bash
docker build -t smart-spend .
docker run -p 7860:7860 smart-spend
```

---

## 📊 Evaluation & Inference

The project includes a mandatory `inference.py` script for automated evaluation.

### Mandatory Environment Variables
- `API_BASE_URL`: The API endpoint for the LLM.
- `MODEL_NAME`: The model identifier (e.g., gpt-3.5-turbo).
- `HF_TOKEN`: Your API authentication key.

### Running the Baseline
```bash
python inference.py
```
This script will iterate through all 3 tasks, emitting structured logs in the `[START]`, `[STEP]`, and `[END]` format.

---

## ✅ Hackathon Compliance Checklist
- [x] **HF Space deploys**: Pre-configured for port 7860.
- [x] **OpenEnv spec compliance**: Validated `openenv.yaml` and typed endpoints.
- [x] **Dockerfile builds**: Fully automated builds.
- [x] **Reproduction**: Standardized `inference.py` for scoring.
- [x] **Structured Logging**: Strict adherence to the `[START]`/`[STEP]`/`[END]` format.

---

## 📄 License
MIT License - See [LICENSE](LICENSE) for more details.
