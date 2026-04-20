import requests

print("Testing AURA API properly...")

try:
    log_res = requests.post("http://localhost:8000/auth/login", json={
        "email": "test_1eb35878@example.com",
        "password": "TestPassword123!"
    })
    token = log_res.json()["tokens"]["access_token"]
    
    aura_res = requests.post(
        "http://localhost:8000/aura/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Hello AURA! Can you help me learn?"}
    )
    print("AURA Query Status:", aura_res.status_code)
    print("AURA Output:", aura_res.text)
except Exception as e:
    print("Error:", e)
