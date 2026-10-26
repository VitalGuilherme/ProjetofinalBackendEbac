from fastapi import FastAPI, HTTPException
import requests
import redis
import os

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

@app.get("/pokemons")
def get_pokemons(
page: int = 1, limit: int = 20):

    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Page ou limit estão com valores inválidos.")

    url = f"https://pokeapi.co/api/v2/pokemon"
    response = requests.get(url)
    data = response.json()
    response = {
       "data": data["results"],
       "pagination": {
           "total": 1281,
           "limit": 20,
           "page": 1,
           "next": "pokemons?limit=20&offset=20",
           "previous": None
       }
    }
    return response

@app.get("/pokemons/{id}")
def get_pokemon(id: int):
    cache_key = f"pokemon:{id}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    url = f"https://pokeapi.co/api/v2/pokemon/{id}/"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Pokémon não encontrado.")
    
    data = response.json()
    result = {
        "name": data["name"],
        "id": data["id"],
        "height": data["height"],
        "weight": data["weight"],
        "types": [t["type"]["name"] for t in data["types"]],
        "sprite": {
            "front_default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{}.png".format(data["id"]),
            "back_default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/{}.png".format(data["id"])
        }
    }
    redis_client.setex(cache_key, json.dumps(result), 600)
    return result
    