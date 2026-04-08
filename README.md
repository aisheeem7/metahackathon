# Smart Save - A Personal Expense Optimizer

A real-world task environment and agentic solution for optimizing personal finances via simulated transaction management. Built for the Hackathon with OpenEnv compliance.

## 🌟 Overview

The **Personal Expense Optimizer** is an interactive environment where an AI agent manages a monthly budget of ₹50,000. Each day, the agent receives realistic transaction notifications (simulated SMS alerts) and must make strategic decisions to maximize savings while ensuring all essential needs are met.

### Key Features
- **Real-world Simulation**: Uses realistic spending patterns across 5 categories (Food, Transport, Shopping, Health, Bills).
- **Dynamic Decision Making**: Agents can allocate budgets, adjust category limits, set savings goals, or defer discretionary expenses.
- **OpenEnv Compliant**: Follows the OpenEnv specification for seamless evaluation and benchmarking.
- **Interactive Dashboard**: A clean, modern frontend to visualize spending habits and agent performance.

---

## 🏗️ Architecture

- **Frontend**: A HTML/CSS/JS single-page application for real-time visualization.
- **Backend**: A Flask-based API serving the web application and the OpenEnv endpoints.
- **Logic Layer**:
    - `env/finance_env.py`: The core environment logic and state management.
    - `env/models.py`: Pydantic-typed Action, Observation, and Reward models.
    - `env/tasks.py`: Standardized tasks and graders (Easy, Medium, Hard).

---

### Prerequisites
- Python 3.10+
- Docker (optional, for containerized deployment)

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
3. Run the application:
   ```bash
   python app.py
   ```
   The dashboard will be available at `http://localhost:7860`.

### Using Docker
```bash
docker build -t expense-optimizer .
docker run -p 7860:7860 expense-optimizer
```

---

The project includes a standardized `inference.py` script for baseline reproduction and scoring.

### Mandatory Environment Variables
- `API_BASE_URL`: The API endpoint for the LLM.
- `MODEL_NAME`: The model identifier to use.
- `HF_TOKEN`: Your Hugging Face / API key.

### Running Inference
```bash
python inference.py
```
The script will execute 3 tasks and emit structured logs in the `[START]`, `[STEP]`, and `[END]` format required for evaluation.

---

## ✅ Compliance Checklist
- [x] **HF Space deploys**: Optimized for Hugging Face Spaces (Port 7860).
- [x] **OpenEnv spec compliance**: Validated `openenv.yaml` and typed Step/Reset endpoints.
- [x] **Dockerfile builds**: Automated Docker build supported.
- [x] **3+ tasks with graders**: Includes Easy, Medium, and Hard tasks with precise scoring (0.0-1.0).
- [x] **Standardized Logging**: Correct stdout log format for evaluation metrics.

---

## 📄 License
MIT License - See [LICENSE](LICENSE) for more details.
