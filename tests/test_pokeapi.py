import requests

def test_get_pokemon():
    response = requests.get("https://pokeapi.co/api/v2/pokemon/25/")
    assert response.status_code == 200
    data = response.json()
    print({
         "id": data["id"],
        "name": data["name"],
        "height": data["height"],
        "weight": data["weight"],
        "types": [t["type"]["name"] for t in data["types"]],
        "sprite": data["sprites"]["front_default"]
    })
