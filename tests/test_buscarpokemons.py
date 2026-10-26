from fastapi.testclient import TestClient
from main import app
import json
import fakeredis
import main
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr(main, "redis_client", fake)
    return fake

def test_buscar_pokemon():
    response = client.get("/pokemons/1")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "id" in data
    assert "height" in data
    assert "weight" in data
    assert "types" in data
    assert "sprite" in data