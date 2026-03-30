from flask import Flask, request, jsonify
from flask_cors import CORS
import sys

sys.path.append('../env')
from finance_env import FinanceEnv

app = Flask(__name__)
CORS(app)

env = FinanceEnv()

@app.route('/')
def home():
    return "Backend running"

@app.route('/reset', methods=['GET'])
def reset():
    return jsonify(env.reset())

@app.route('/step', methods=['POST'])
def step():
    action = request.json['action']
    state, reward, done = env.step(action)

    return jsonify({
        "state": state,
        "reward": reward,
        "done": done
    })

@app.route('/state', methods=['GET'])
def state():
    return jsonify(env.state())

if __name__ == "__main__":
    app.run(debug=True)
