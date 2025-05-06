import os
from dotenv import load_dotenv

# Carica il file .env.local, se esiste; altrimenti, carica .env.production
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv(".env.production")

# Verifica che le variabili siano caricate correttamente
print(f"DB_NAME: {os.getenv('DB_NAME')}")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD')}")
print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_PORT: {os.getenv('DB_PORT')}")
