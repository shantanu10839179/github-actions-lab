import os
import time
import requests
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
SONAR_TOKEN = os.environ.get('SONAR_TOKEN')
SONAR_HOST = os.environ.get('SONAR_HOST', 'http://localhost:9000')
SONAR_ORGANIZATION = os.environ.get('SONAR_ORGANIZATION', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'youruser/yourrepo')

HEADERS_SONAR = {'Authorization': f'Bearer {SONAR_TOKEN}', 'Accept': 'application/json'}
HEADERS_GITHUB = {'Authorization': f'token {GITHUB_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
        )
        return conn
    except Exception as error:
        print(f"Error while connecting to PostgreSQL: {error}")
        return None

# --- SonarQube Collector ---
def collect_sonar_metrics(conn, project_key, repo_name):
    metrics = [
        'coverage', 'bugs', 'vulnerabilities', 'code_smells',
        'sqale_index', 'ncloc', 'duplicated_lines_density',
        'maintainability_rating', 'reliability_rating', 'security_rating'
    ]
    url = f"{SONAR_HOST}/api/measures/component"
    params = {'component': project_key, 'metricKeys': ','.join(metrics)}
    for attempt in range(1, 6):
        try:
            response = requests.get(url, headers=HEADERS_SONAR, params=params)
            if response.status_code == 404:
                print(f"Attempt {attempt}: 404 Not Found for project '{project_key}'. Retrying in 10 seconds...")
                time.sleep(10)
                continue
            response.raise_for_status()
            data = response.json()
            measures = {m['metric']: m.get('value') for m in data.get('component', {}).get('measures', [])}
            break
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}: Error fetching measures for '{project_key}': {e}")
            time.sleep(10)
    else:
        print(f"Failed to retrieve measures for project '{project_key}' after 5 attempts.")
        return
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO sonarqube_results (
                repo_name, project_key, analysis_date, branch, quality_gate_status,
                coverage, bugs, vulnerabilities, code_smells, technical_debt_minutes,
                lines_of_code, duplicated_lines, maintainability_rating,
                reliability_rating, security_rating
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (
            repo_name, project_key, datetime.now(), 'main', 'N/A',
            measures.get('coverage'), measures.get('bugs'), measures.get('vulnerabilities'),
            measures.get('code_smells'), measures.get('sqale_index'), measures.get('ncloc'),
            measures.get('duplicated_lines_density'), measures.get('maintainability_rating'),
            measures.get('reliability_rating'), measures.get('security_rating')
        ))
        conn.commit()
    print(f"Inserted SonarQube data for {project_key}")

# --- DORA Metrics Collector (Lead Time, MTTR, CFR, Deployment Frequency) ---
# You can copy the relevant functions from your LeadTimeToChange.py, MTTR & CFR.py, etc.
# For example:
def collect_lead_time_metrics(conn, repo):
    # ... logic from LeadTimeToChange.py ...
    pass

def collect_mttr_cfr_metrics(conn, repo):
    # ... logic from MTTR & CFR.py ...
    pass

def collect_build_metrics(conn, repo):
    # ... logic from Build failure, pipeline frequency, avg build duration number of builds and successful builds.py ...
    pass

def collect_github_metrics(conn, repo):
    # ... logic from import postgres.py ...
    pass

def main():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database. Exiting.")
        return

    # Collect SonarQube metrics
    collect_sonar_metrics(conn, 'shantanu10839179_github-actions-lab', 'shantanu10839179/github-actions-lab')

    # Collect DORA and GitHub metrics
    collect_lead_time_metrics(conn, GITHUB_REPO)
    collect_mttr_cfr_metrics(conn, GITHUB_REPO)
    collect_build_metrics(conn, GITHUB_REPO)
    collect_github_metrics(conn, GITHUB_REPO)

    conn.close()
    print("Unified data collection completed.")

if __name__ == "__main__":
    main()