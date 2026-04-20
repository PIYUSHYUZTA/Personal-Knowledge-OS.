from fastapi.testclient import TestClient
from app.main import app
import time

client = TestClient(app)

ts = str(int(time.time()))
email = f"user_{ts}@test.com"
username = f"user_{ts}"
password = "password123"

# Register
resp1 = client.post(
    "/auth/register",
    json={"email": email, "username": username, "password": password}
)
print("Register:", resp1.status_code, resp1.text)

# Login
resp2 = client.post(
    "/auth/login",
    json={"email": email, "password": password}
)
print("Login:", resp2.status_code, resp2.text)

# Verify
if resp2.status_code == 200:
    token = resp2.json()["tokens"]["access_token"]
    resp3 = client.get("/auth/verify", params={"token": token})
    print("Verify Token directly:", resp3.status_code, resp3.text)
