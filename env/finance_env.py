import random
from pydantic import BaseModel

# ── Typed Models ──────────────────────────────────────────
class Observation(BaseModel):
    spent: float
    limit: float
    day: int
    ratio: float
    days_remaining: int

class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict

# ── Task Profiles ─────────────────────────────────────────
TASK_PROFILES = {
    "easy":   {"limit": 2000, "max_days": 30},
    "medium": {"limit": 1000, "max_days": 30},
    "hard":   {"limit": 500,  "max_days": 30},
}

# ── Environment ───────────────────────────────────────────
class FinanceEnv:
    def __init__(self, task: str = "medium"):
        profile = TASK_PROFILES[task]
        self.limit    = profile["limit"]
        self.max_days = profile["max_days"]
        self.day      = 1
        self.spent    = 0.0

    def reset(self) -> Observation:
        self.day   = 1
        self.spent = 0.0
        return self._get_obs()

    def state(self) -> Observation:
        return self._get_obs()

    def step(self, action: int) -> StepResult:
        """
        action 0 → reduce spending  (-30 from random expense)
        action 1 → normal spending
        action 2 → increase spending (+30 to random expense)
        """
        expense = random.randint(50, 150)
        if action == 0:   expense -= 30
        elif action == 2: expense += 30

        self.spent += max(expense, 0)   # expense can't go negative
        self.day   += 1

        reward = self._compute_reward()
        done   = self.day > self.max_days

        return StepResult(
            observation=self._get_obs(),
            reward=reward,
            done=done,
            info={"expense_this_step": expense}
        )

    def _get_obs(self) -> Observation:
        return Observation(
            spent=self.spent,
            limit=self.limit,
            day=self.day,
            ratio=round(self.spent / self.limit, 3),
            days_remaining=self.max_days - self.day
        )

    def _compute_reward(self) -> float:
        ratio = self.spent / self.limit
        if ratio <= 0.5:  return +2.0
        if ratio <= 0.75: return +1.0
        if ratio <= 0.90: return -0.5
        if ratio <= 1.0:  return -1.5
        return -5.0


# ── Quick Test ────────────────────────────────────────────
if __name__ == "__main__":
    for task in ["easy", "medium", "hard"]:
        env = FinanceEnv(task=task)
        state = env.reset()
        print(f"\n── Task: {task} (limit={env.limit}) ──")
        for _ in range(5):
            result = env.step(random.choice([0, 1, 2]))
            print(f"  Day {result.observation.day} | "
                  f"Spent: {result.observation.spent} | "
                  f"Ratio: {result.observation.ratio} | "
                  f"Reward: {result.reward}")