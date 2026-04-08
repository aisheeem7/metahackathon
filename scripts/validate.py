import os
import sys
from pathlib import Path
import yaml
import re

# Ensure UTF-8 output for emojis in Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def check_file(path):
    exists = Path(path).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {path}")
    return exists

def validate_submission():
    print("🚀 Running Pre-Submission Validation...\n")
    
    # 1. Mandatory Files
    files = ["app.py", "inference.py", "Dockerfile", "openenv.yaml", "requirements.txt", "backend/app.py", "env/tasks.py"]
    all_files_exist = all([check_file(f) for f in files])
    
    # 2. OpenEnv Spec
    print("\n🔍 Validating openenv.yaml...")
    if Path("openenv.yaml").exists():
        try:
            with open("openenv.yaml", "r") as f:
                spec = yaml.safe_load(f)
                tasks = spec.get("tasks", [])
                if len(tasks) >= 3:
                    print(f"✅ Found {len(tasks)} tasks in openenv.yaml")
                else:
                    print(f"❌ Need at least 3 tasks (found {len(tasks)})")
        except Exception as e:
            print(f"❌ Error parsing openenv.yaml: {e}")
    
    # 3. Inference Script Analysis
    print("\n🔍 Validating inference.py...")
    if Path("inference.py").exists():
        content = Path("inference.py").read_text()
        
        # Check OpenAI Client
        if "OpenAI(" in content:
            print("✅ Uses OpenAI Client")
        else:
            print("❌ OpenAI Client usage not detected")
            
        # Check Log Tags
        tags = ["[START]", "[STEP]", "[END]"]
        missing_tags = [t for t in tags if t not in content]
        if not missing_tags:
            print("✅ Structured log tags found ([START], [STEP], [END])")
        else:
            print(f"❌ Missing log tags: {missing_tags}")
            
        # Check Env Vars
        vars = ["API_BASE_URL", "MODEL_NAME", "HF_TOKEN"]
        missing_vars = [v for v in vars if v not in content]
        if not missing_vars:
            print("✅ Required environment variables detected")
        else:
            print(f"❌ Missing env var usage: {missing_vars}")

    # 4. Tasks and Graders
    print("\n🔍 Validating Tasks and Graders...")
    if Path("env/tasks.py").exists():
        content = Path("env/tasks.py").read_text()
        # Count tasks in TASKS dict
        task_count = content.count('task_id="')
        if task_count >= 3:
            print(f"✅ Found {task_count} task definitions")
        else:
            print(f"❌ Found only {task_count} tasks (need 3+)")

    # 5. HF Space Entry Point
    print("\n🔍 Validating HF Space entry point...")
    if Path("app.py").exists():
        content = Path("app.py").read_text()
        if "7860" in content:
            print("✅ Port 7860 detected in app.py")
        else:
            print("❌ Port 7860 not explicitly set in root app.py")

    print("\n--- Validation Complete ---")

if __name__ == "__main__":
    validate_submission()
