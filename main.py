from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import requests
import redis
import os
import json
import logging

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pokemons.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def session_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Projeto final curso Backend Python Ebac",
    description="API para gerenciar catálogos de pokémons via requisições HTTP na API PokéAPI.",
    version="1.0.0",
    contact={
        "name":"Guilherme Vital",
        "email":"guilhermev.j.santos@gmail.com"
    }
)

#REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
#REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class PokemonDB(Base):
    __tablename__ = "pokemons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    height = Column(Integer)
    weight = Column(Integer)
    types = Column(String)  # Armazena os tipos como uma string separada por vírgulas
    sprite_front_default = Column(String)
    sprite_back_default = Column(String)

class Pokemon(BaseModel):
    name: str
    height: int
    weight: int
    types: list[str]
    sprite_front_default: str
    sprite_back_default: str

Base.metadata.create_all(bind=engine)

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

    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except redis.exceptions.RedisError as e:
        logger.warning(f"Redis indisponível ao ler o cache: {e}")

    url = f"https://pokeapi.co/api/v2/pokemon/{id}/"
    response = requests.get(url, timeout=10)
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
            "front_default": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{data['id']}.png",
            "back_default": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/{data['id']}.png",
        },
    }

    try:
        redis_client.setex(cache_key, 60, json.dumps(result))
    except redis.exceptions.RedisError as e:
        logger.warning(f"Redis indisponível ao salvar o cache: {e}")

    return result


@app.post("/adicionar_pokemons")
def create_pokemon(pokemon: Pokemon, db: Session = Depends(session_db)):
    db_pokemon = db.query(PokemonDB).filter(PokemonDB.id == pokemon.id).first()
    if db_pokemon:
        raise HTTPException(status_code=400, detail="Pokémon já existe no banco de dados.")

    novo_pokemon = PokemonDB(
        id=pokemon.id,
        name=pokemon.name,
        height=pokemon.height,
        weight=pokemon.weight,
        types=",".join(pokemon.types),
        sprite_front_default=pokemon.sprite_front_default,
        sprite_back_default=pokemon.sprite_back_default
    )
    db.add(novo_pokemon)
    db.commit()
    db.refresh(novo_pokemon)
    return novo_pokemon

@app.put("/atualizar_pokemons/{id}")
def update_pokemon(id: int, pokemon: Pokemon, db: Session = Depends(session_db)):
    db_pokemon = db.query(PokemonDB).filter(PokemonDB.id == id).first()
    if not db_pokemon:
        raise HTTPException(status_code=404, detail="Pokémon não encontrado no banco de dados.")

    db_pokemon.name = pokemon.name
    db_pokemon.height = pokemon.height
    db_pokemon.weight = pokemon.weight
    db_pokemon.types = ",".join(pokemon.types)

    db.commit()
    db.refresh(db_pokemon)
    return db_pokemon

@app.delete("/deletar_pokemons/{id}")
def delete_pokemon(id: int, db: Session = Depends(session_db)):
    db_pokemon = db.query(PokemonDB).filter(PokemonDB.id == id).first()
    if not db_pokemon:
        raise HTTPException(status_code=404, detail="Pokémon não encontrado no banco de dados.")

    db.delete(db_pokemon)
    db.commit()
    return {"message": "Pokémon deletado com sucesso."}