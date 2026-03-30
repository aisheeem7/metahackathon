const baseURL = "http://127.0.0.1:5000";

async function resetEnv() {
    let res = await fetch(`${baseURL}/reset`);
    let data = await res.json();
    document.getElementById("state").innerText = JSON.stringify(data, null, 2);
}

async function takeAction(action) {
    let res = await fetch(`${baseURL}/step`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ action })
    });

    let data = await res.json();

    document.getElementById("state").innerText = JSON.stringify(data.state, null, 2);
    document.getElementById("reward").innerText = "Reward: " + data.reward;
}