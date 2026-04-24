from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

import uuid
unique_id = str(uuid.uuid4())[:8]
email = f"test_{unique_id}@pkos.dev"
username = f"user_{unique_id}"
password = "password123"

print(f"Testing with: {username} / {email}")

# 1. Register
response = client.post(
    "/auth/register",
    json={"email": email, "username": username, "password": password}
)
print("Registration response:", response.status_code, response.json())

# 2. Login
response = client.post(
    "/auth/login",
    json={"email": email, "password": password}
)
print("Login response:", response.status_code)
tokens = response.json().get("tokens", {})
token = tokens.get("access_token")
print("Token received:", "Yes" if token else "No")

# 3. Verify Protected Route
if token:
    response = client.get(
        "/aura/state",
        headers={"Authorization": f"Bearer {token}"}
    )
    print("Protected route response:", response.status_code, response.json())
