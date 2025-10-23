import os
import requests
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
import base64

# Load environment variables from .env file
load_dotenv()

SONAR_TOKEN = os.getenv("SONAR_TOKEN")
SONAR_HOST_URL = os.getenv("SONAR_HOST_URL")
SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY")
SONAR_ORGANIZATION = os.getenv("SONAR_ORGANIZATION")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", 5432)

# SonarQube API endpoint and metrics
SONAR_API = f"{SONAR_HOST_URL}/api/measures/component"
METRICS = "coverage,bugs"

# SonarCloud/SonarQube token authentication (token as username, empty password)
token_bytes = f"{SONAR_TOKEN}:".encode("utf-8")
token_b64 = base64.b64encode(token_bytes).decode("utf-8")
headers = {"Authorization": f"Basic {token_b64}"}

def get_latest_analysis_date():
    analysis_api = f"{SONAR_HOST_URL}/api/project_analyses/search"
    params = {
        "project": SONAR_PROJECT_KEY,
        "organization": SONAR_ORGANIZATION
    }
    response = requests.get(analysis_api, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    # Get the date of the most recent analysis
    if data['analyses']:
        return data['analyses'][0]['date']
    else:
        # fallback to now if no analysis found
        return datetime.now().isoformat()

# Get the latest analysis date from SonarCloud
analysis_date = get_latest_analysis_date()

# Fetch metrics from SonarQube API
params = {
    "component": SONAR_PROJECT_KEY,
    "metricKeys": METRICS,
    "organization": SONAR_ORGANIZATION
}
response = requests.get(SONAR_API, params=params, headers=headers)
response.raise_for_status()
data = response.json()

# Parse metrics from response
metrics = {item['metric']: item['value'] for item in data['component']['measures']}
print("Fetched metrics:", metrics)

# Prepare values for DB
coverage = float(metrics.get("coverage", 0))
bugs = int(metrics.get("bugs", 0))

# Insert or update into PostgreSQL
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS
)
cur = conn.cursor()
cur.execute("""
    INSERT INTO sonarqube_results (
        project_key, analysis_date, coverage, bugs
    )
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (project_key, analysis_date) DO UPDATE
    SET coverage = EXCLUDED.coverage,
        bugs = EXCLUDED.bugs
""", (
    SONAR_PROJECT_KEY,
    analysis_date,
    coverage,
    bugs
))
conn.commit()
cur.close()
conn.close()
print("Metrics inserted/updated in DB.")