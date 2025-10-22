import os
import requests
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
import time

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---

# Database Connection Details
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")

# SonarCloud Configuration
SONAR_TOKEN = os.environ.get('SONAR_TOKEN')
SONAR_HOST = "https://sonarcloud.io"
SONAR_ORGANIZATION = os.environ.get('SONAR_ORGANIZATION', 'shantanu10839179-1')

# SonarCloud Projects to analyze
SONAR_PROJECTS = [
    {
        'project_key': 'shantanu10839179_github-actions-lab',
        'repo_name': 'shantanu10839179/github-actions-lab'
    }
    # Add more projects here as needed
]

# SonarCloud API Headers
HEADERS = {
    'Authorization': f'Bearer {SONAR_TOKEN}',
    'Accept': 'application/json'
}

# --- Database Functions ---

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except (Exception, psycopg2.Error) as error:
        print(f"Error while connecting to PostgreSQL: {error}")
        return None

def setup_database(conn):
    """Creates the sonarqube_results table if it doesn't exist."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sonarqube_results (
                id SERIAL PRIMARY KEY,
                repo_name VARCHAR(255) NOT NULL,
                project_key VARCHAR(255) NOT NULL,
                analysis_date TIMESTAMP WITH TIME ZONE NOT NULL,
                branch VARCHAR(100) DEFAULT 'main',
                quality_gate_status VARCHAR(20),
                coverage DECIMAL(5,2),
                bugs INTEGER DEFAULT 0,
                vulnerabilities INTEGER DEFAULT 0,
                code_smells INTEGER DEFAULT 0,
                technical_debt_minutes INTEGER DEFAULT 0,
                lines_of_code INTEGER DEFAULT 0,
                duplicated_lines DECIMAL(5,2),
                maintainability_rating INTEGER,
                reliability_rating INTEGER,
                security_rating INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sonarqube_results_repo_date 
            ON sonarqube_results(repo_name, analysis_date);
            """)
        conn.commit()
        print("Database setup complete. SonarQube results table is ready.")
    except (Exception, psycopg2.Error) as error:
        print(f"Error during database setup: {error}")

def insert_sonar_data(conn, data):
    """Insert SonarQube analysis data into the database."""
    with conn.cursor() as cursor:
        insert_query = """
            INSERT INTO sonarqube_results (
                repo_name, project_key, analysis_date, branch, quality_gate_status,
                coverage, bugs, vulnerabilities, code_smells, technical_debt_minutes,
                lines_of_code, duplicated_lines, maintainability_rating,
                reliability_rating, security_rating
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.executemany(insert_query, data)
        conn.commit()
    print(f"  - Inserted {len(data)} SonarQube analysis records.")

# --- SonarCloud API Functions ---

def get_project_measures_with_retry(project_key, metrics, max_retries=5, delay=10):
    """Get key measures from SonarCloud for a project with retry logic."""
    url = f"{SONAR_HOST}/api/measures/component"
    params = {
        'component': project_key,
        'metricKeys': ','.join(metrics)
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, params=params)
            if response.status_code == 404:
                print(f"Attempt {attempt}: 404 Not Found for project '{project_key}'. Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            response.raise_for_status()
            data = response.json()
            measures = {
                measure['metric']: measure.get('value')
                for measure in data.get('component', {}).get('measures', [])
            }
            return measures
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}: Error fetching measures for '{project_key}': {e}")
            time.sleep(delay)

    print(f"Failed to retrieve measures for project '{project_key}' after {max_retries} attempts.")
    return {}

def get_quality_gate_status(project_key):
    """Get quality gate status for a project."""
    url = f"{SONAR_HOST}/api/qualitygates/project_status"
    params = {'projectKey': project_key}
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('projectStatus', {}).get('status', 'UNKNOWN')
    except requests.exceptions.RequestException as e:
        print(f"  - ERROR: Failed to get quality gate for {project_key}: {e}")
        return 'ERROR'

def get_latest_analysis(project_key):
    """Get the latest analysis information for a project."""
    url = f"{SONAR_HOST}/api/project_analyses/search"
    params = {
        'project': project_key,
        'ps': 1  # Get only the latest analysis
    }
    try:
        response = requests.get(url, headers=HEADERS, params=params)
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
        print(f"  - ERROR: Failed to get analysis info for {project_key}: {e}")
        return None

def safe_float(value, default=None):
    """Safely convert value to float."""
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Safely convert value to int."""
    if value is None or value == '':
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default

def process_project(project_info):
    """Process a single SonarCloud project and return data for database."""
    project_key = project_info['project_key']
    repo_name = project_info['repo_name']
    print(f"  - Processing project: {project_key}")

    # Get latest analysis info
    analysis_info = get_latest_analysis(project_key)
    if not analysis_info:
        print(f"  - No analysis found for {project_key}")
        return []

    # Get measures with retry logic
    metrics = [
        'coverage', 'bugs', 'vulnerabilities', 'code_smells',
        'sqale_index', 'ncloc', 'duplicated_lines_density',
        'maintainability_rating', 'reliability_rating', 'security_rating'
    ]
    measures = get_project_measures_with_retry(project_key, metrics)
    if not measures:
        print(f"  - No measures found for {project_key}")
        return []

    # Get quality gate status
    quality_gate = get_quality_gate_status(project_key)

    # Parse analysis date
    try:
        analysis_date = datetime.fromisoformat(analysis_info['date'].replace('Z', '+00:00'))
    except:
        analysis_date = datetime.now()

    # Prepare data for database
    data = (
        repo_name,
        project_key,
        analysis_date,
        analysis_info.get('branch', 'main'),
        quality_gate,
        safe_float(measures.get('coverage')),
        safe_int(measures.get('bugs')),
        safe_int(measures.get('vulnerabilities')),
        safe_int(measures.get('code_smells')),
        safe_int(measures.get('sqale_index')),  # Technical debt in minutes
        safe_int(measures.get('ncloc')),  # Lines of code
        safe_float(measures.get('duplicated_lines_density')),
        safe_int(measures.get('maintainability_rating')),
        safe_int(measures.get('reliability_rating')),
        safe_int(measures.get('security_rating'))
    )

    return [data]

def main():
    """Main function to fetch SonarCloud data and store in database."""
    if not SONAR_TOKEN:
        print("ERROR: SONAR_TOKEN environment variable not set")
        print("Please set your SonarCloud token in the environment variables")
        return

    print("Starting SonarQube analysis data collection...")

    # Connect to database
    db_connection = get_db_connection()
    if not db_connection:
        print("Failed to connect to database. Exiting.")
        return

    # Setup database table
    setup_database(db_connection)

    # Process each project
    all_data = []
    for project in SONAR_PROJECTS:
        try:
            project_data = process_project(project)
            all_data.extend(project_data)
        except Exception as e:
            print(f"Error processing project {project['project_key']}: {e}")
            continue

    # Insert data into database
    if all_data:
        insert_sonar_data(db_connection, all_data)
        print(f"Successfully processed {len(all_data)} SonarQube analysis records")
    else:
        print("No SonarQube data to insert")

    # Close database connection
    db_connection.close()
    print("SonarQube data collection completed.")

if __name__ == "__main__":
    main()