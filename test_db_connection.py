import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env

try:
    conn = psycopg2.connect(
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT")
    )
    print("✅ Successfully connected to the database!")
    conn.close()
except Exception as e:
    print("❌ Failed to connect to the database.")
    print(e)