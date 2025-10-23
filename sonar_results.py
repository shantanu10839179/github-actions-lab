import os
import requests
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()
print("Environment variables loaded:")
print("SONAR_TOKEN:", "✓" if os.environ.get("SONAR_TOKEN") else "✗")
print("DB_HOST:", os.environ.get("DB_HOST"))
print("GITHUB_TOKEN:", "✓" if os.environ.get("GITHUB_TOKEN") else "✗")

# --- Configuration ---
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")

SONAR_TOKEN = os.environ.get('SONAR_TOKEN')
SONAR_HOST = "https://sonarcloud.io"
SONAR_ORGANIZATION = os.environ.get('SONAR_ORGANIZATION')

if not SONAR_ORGANIZATION:
    print("ERROR: SONAR_ORGANIZATION not set in .env file!")
else:
    print(f"Using SonarCloud organization: {SONAR_ORGANIZATION}")

SONAR_PROJECTS = [
    {
        'project_key': 'shantanu10839179_github-actions-lab',
        'repo_name': 'shantanu10839179/github-actions-lab'
    }
    # Add more projects here as needed
]

HEADERS = {
    'Authorization': f'Bearer {SONAR_TOKEN}',
    'Accept': 'application/json'
}

# --- Metrics to fetch/store ---
metrics = [
    'coverage', 'bugs', 'vulnerabilities', 'code_smells',
    'sqale_index', 'ncloc', 'duplicated_lines_density',
    'maintainability_rating', 'reliability_rating', 'security_rating',
    'alert_status', 'blocker_violations', 'critical_violations', 'major_violations',
    'minor_violations', 'info_violations', 'tests', 'test_errors', 'test_failures',
    'test_execution_time', 'test_success_density', 'lines', 'comment_lines_density',
    'complexity', 'functions', 'statements', 'classes', 'files', 'branch_coverage',
    'line_coverage', 'new_coverage', 'new_bugs', 'new_vulnerabilities', 'new_code_smells',
    'new_duplicated_lines_density', 'new_lines', 'new_maintainability_rating',
    'new_reliability_rating', 'new_security_rating', 'new_technical_debt',
    'new_lines_to_cover', 'new_uncovered_lines', 'new_violations'
]

# --- Database Functions ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.Error as error:
        print(f"Error while connecting to PostgreSQL: {error}")
        return None

def setup_database(conn):
    try:
        with conn.cursor() as cursor:
            # Build dynamic SQL for all metrics columns
            metric_columns = ",\n".join([
                f"{m} VARCHAR(64) DEFAULT NULL" for m in metrics
            ])
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS sonarqube_results (
                id SERIAL PRIMARY KEY,
                repo_name VARCHAR(255) NOT NULL,
                project_key VARCHAR(255) NOT NULL,
                analysis_date TIMESTAMP WITH TIME ZONE NOT NULL,
                branch VARCHAR(100) DEFAULT 'main',
                quality_gate_status VARCHAR(20),
                {metric_columns},
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sonarqube_results_repo_date
            ON sonarqube_results(repo_name, analysis_date);
            """)
            conn.commit()
            print("Database setup complete. SonarQube results table is ready.")
    except psycopg2.Error as error:
        print(f"Error during database setup: {error}")
        if conn:
            conn.rollback()

def insert_sonar_data(conn, data):
    with conn.cursor() as cursor:
        metric_fields = ", ".join(metrics)
        placeholders = ", ".join(["%s"] * (5 + len(metrics)))
        insert_query = f"""
        INSERT INTO sonarqube_results (
            repo_name, project_key, analysis_date, branch, quality_gate_status,
            {metric_fields}
        ) VALUES ({placeholders});
        """
        cursor.executemany(insert_query, data)
        conn.commit()
        print(f" - Inserted {len(data)} SonarQube analysis records.")

# --- SonarCloud API Functions ---
def get_project_measures(project_key):
    url = f"{SONAR_HOST}/api/measures/component"
    params = {
        'component': project_key,
        'metricKeys': ','.join(metrics)
    }
    try:
        print(f" - Fetching measures from {url}")
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        print(f" - Response status code: {response.status_code}")
        if response.status_code == 401:
            print(" - Authentication failed. Please check your SONAR_TOKEN")
            return {}
        elif response.status_code == 404:
            print(f" - Project {project_key} not found in SonarCloud")
            return {}
        response.raise_for_status()
        data = response.json()
        measures = {}
        for measure in data.get('component', {}).get('measures', []):
            measures[measure['metric']] = measure.get('value')
        print(f" - Measures found: {measures}")
        return measures
    except requests.exceptions.RequestException as e:
        print(f" - ERROR: Failed to get measures for {project_key}: {e}")
        return {}
    except ValueError as e:
        print(f" - ERROR: Invalid JSON response for {project_key}: {e}")
        return {}

def get_quality_gate_status(project_key):
    url = f"{SONAR_HOST}/api/qualitygates/project_status"
    params = {'projectKey': project_key}
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get('projectStatus', {}).get('status', 'UNKNOWN')
    except requests.exceptions.RequestException as e:
        print(f" - ERROR: Failed to get quality gate for {project_key}: {e}")
        return 'ERROR'

def get_latest_analysis(project_key):
    url = f"{SONAR_HOST}/api/project_analyses/search"
    params = {
        'project': project_key,
        'ps': 1  # Get only the latest analysis
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        analyses = data.get('analyses', [])
        if analyses:
            latest = analyses[0]
            return {
                'date': latest.get('date'),
                'revision': latest.get('revision'),
                'branch': latest.get('branch', 'main')
            }
        return None
    except requests.exceptions.RequestException as e:
        print(f" - ERROR: Failed to get analysis info for {project_key}: {e}")
        return None

def verify_project_exists(project_key):
    url = f"{SONAR_HOST}/api/projects/search"
    params = {
        'projects': project_key,
        'organization': SONAR_ORGANIZATION
    }
    print(f"DEBUG: Checking project existence with URL: {url} and params: {params}")
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        print(f"DEBUG: Response status code: {response.status_code}")
        print(f"DEBUG: Response text: {response.text}")
        if response.status_code == 200:
            data = response.json()
            components = data.get('components', [])
            return len(components) > 0
        return False
    except Exception as e:
        print(f" - ERROR: Failed to verify project existence: {e}")
        return False

def process_project(project_info):
    project_key = project_info['project_key']
    repo_name = project_info['repo_name']
    print(f" - Processing project: {project_key}")
    # Verify project exists
    if not verify_project_exists(project_key):
        print(f" - Project {project_key} does not exist in SonarCloud organization {SONAR_ORGANIZATION}")
        print(" - Please make sure:")
        print(" 1. The project has been created in SonarCloud")
        print(" 2. The project key is correct")
        print(" 3. The organization name is correct")
        print(" 4. Your SonarCloud token has the necessary permissions")
        return []
    # Get latest analysis info
    analysis_info = get_latest_analysis(project_key)
    if not analysis_info:
        print(f" - No analysis found for {project_key}")
        return []
    # Get measures
    measures = get_project_measures(project_key)
    if measures is None:
        print(f" - No measures found for {project_key}")
        return []
    # Get quality gate status
    quality_gate = get_quality_gate_status(project_key)
    # Parse analysis date
    try:
        analysis_date = datetime.fromisoformat(analysis_info['date'].replace('Z', '+00:00'))
    except (ValueError, KeyError) as e:
        print(f" - Error parsing analysis date: {e}. Using current time.")
        analysis_date = datetime.now()
    # Prepare data for database
    row = [
        repo_name,
        project_key,
        analysis_date,
        analysis_info.get('branch', 'main'),
        quality_gate
    ]
    # Add all metrics in order
    for m in metrics:
        row.append(measures.get(m))
    return [tuple(row)]

def verify_sonar_access():
    validate_url = f"{SONAR_HOST}/api/authentication/validate"
    try:
        validate_response = requests.get(validate_url, headers=HEADERS, timeout=15)
        if validate_response.status_code == 401:
            print("ERROR: Invalid SonarCloud token")
            return False
        validate_data = validate_response.json()
        if not validate_data.get('valid', False):
            print("ERROR: SonarCloud token is not valid")
            return False
        org_url = f"{SONAR_HOST}/api/organizations/search"
        org_params = {'organizations': SONAR_ORGANIZATION}
        org_response = requests.get(org_url, headers=HEADERS, params=org_params, timeout=15)
        if org_response.status_code == 400:
            print(f"ERROR: Invalid organization key '{SONAR_ORGANIZATION}'")
            print("Please check your SONAR_ORGANIZATION value")
            print("Response:", org_response.text)
            return False
        elif org_response.status_code != 200:
            print(f"ERROR: Failed to verify organization. Status code: {org_response.status_code}")
            print("Response:", org_response.text)
            return False
        org_data = org_response.json()
        if not org_data.get('organizations', []):
            print(f"ERROR: Organization '{SONAR_ORGANIZATION}' not found or no access")
            print("Please verify:")
            print("1. The organization exists in SonarCloud")
            print("2. Your token has access to this organization")
            print("3. You are a member of this organization")
            return False
        print(f"Successfully verified access to SonarCloud organization: {SONAR_ORGANIZATION}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Network error while accessing SonarCloud: {e}")
        return False
    except ValueError as e:
        print(f"ERROR: Invalid response from SonarCloud: {e}")
        return False

def main():
    required_vars = {
        'SONAR_TOKEN': SONAR_TOKEN,
        'DB_HOST': DB_HOST,
        'DB_NAME': DB_NAME,
        'DB_USER': DB_USER,
        'DB_PASS': DB_PASS
    }
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f" - {var}")
        print("Please set these variables in your .env file")
        return
    if not verify_sonar_access():
        return
    print("Starting SonarQube analysis data collection...")
    db_connection = get_db_connection()
    if not db_connection:
        print("Failed to connect to database. Exiting.")
        return
    setup_database(db_connection)
    all_data = []
    for project in SONAR_PROJECTS:
        try:
            project_data = process_project(project)
            all_data.extend(project_data)
        except Exception as e:
            print(f"Error processing project {project['project_key']}: {e}")
            continue
    if all_data:
        insert_sonar_data(db_connection, all_data)
        print(f"Successfully processed {len(all_data)} SonarQube analysis records")
    else:
        print("No SonarQube data to insert")
    db_connection.close()
    print("SonarQube data collection completed.")

if __name__ == "__main__":
    main()