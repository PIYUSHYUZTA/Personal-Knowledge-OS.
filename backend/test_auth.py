from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

response = client.post(
    "/auth/register",
    json={"email": "test@test.com", "username": "testuser", "password": "password123"}
)
print("Registration response:", response.status_code, response.json())

response = client.post(
    "/auth/login",
    json={"email": "test@test.com", "password": "password123"}
)
print("Login response:", response.status_code, response.json())
