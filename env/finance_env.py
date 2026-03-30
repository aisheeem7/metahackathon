import random

class FinanceEnv:
    def __init__(self):
        self.limit = 1000
        self.day = 1
        self.spent = 0

    def reset(self):
        self.limit = 1000
        self.day = 1
        self.spent = 0
        return self.state()

    def state(self):
        return {
            "spent": self.spent,
            "limit": self.limit,
            "day": self.day
        }

    def step(self, action):
        """
        action:
        0 -> reduce spending
        1 -> normal spending
        2 -> increase spending
        """

        # simulate expense
        expense = random.randint(50, 150)

        if action == 0:
            expense -= 30
        elif action == 2:
            expense += 30

        self.spent += expense
        self.day += 1

        # reward logic
        if self.spent <= self.limit:
            reward = 1
        else:
            reward = -1

        done = self.day > 30

        return self.state(), reward, done

if __name__ == "__main__":
    env = FinanceEnv()
    state = env.reset()

    for _ in range(5):
        action = random.choice([0,1,2])
        state, reward, done = env.step(action)
        print(state, reward)