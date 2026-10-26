from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_pokemons():
    response = client.get("/pokemons?page=1&limit=20")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) <= 20