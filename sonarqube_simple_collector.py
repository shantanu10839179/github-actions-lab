import os
import requests
import psycopg2
from dotenv import load_dotenv

from datetime import datetime
# Load environment variables from .env file
load_dotenv()


# this block to verify .env loading
print("Environment variables loaded:")
print("SONAR_TOKEN:", "✓" if os.environ.get("SONAR_TOKEN") else "✗")
print("DB_HOST:", os.environ.get("DB_HOST"))
print("GITHUB_TOKEN:", "✓" if os.environ.get("GITHUB_TOKEN") else "✗")


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

# SonarCloud Projects to analyze
SONAR_PROJECTS = [
    {
        'project_key': 'shantanu10839179_github-actions-lab',  # Exact project key from SonarCloud
        'repo_name': 'shantanu10839179/github-actions-lab'
    }
    # Add more projects here as needed
]

# Set organization explicitly based on your SonarCloud setup
SONAR_ORGANIZATION = os.environ.get('SONAR_ORGANIZATION')
if not SONAR_ORGANIZATION:
    print("ERROR: SONAR_ORGANIZATION not set in .env file!")
else:
    print(f"Using SonarCloud organization: {SONAR_ORGANIZATION}")
SONAR_PROJECTS = [
    {
        'project_key': 'shantanu10839179_github-actions-lab',  # Use dashes instead of underscores
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
    except psycopg2.Error as error:
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
    except psycopg2.Error as error:
        print(f"Error during database setup: {error}")
        if conn:
            conn.rollback()

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

def get_project_measures(project_key):
    """Get key measures from SonarCloud for a project."""
    metrics = [
        'coverage', 'bugs', 'vulnerabilities', 'code_smells',
        'sqale_index', 'ncloc', 'duplicated_lines_density',
        'maintainability_rating', 'reliability_rating', 'security_rating'
    ]
    
    url = f"{SONAR_HOST}/api/measures/component"
    params = {
        'component': project_key,
        'metricKeys': ','.join(metrics)
    }
    
    try:
        print(f"  - Fetching measures from {url}")
        response = requests.get(url, headers=HEADERS, params=params)
        print(f"  - Response status code: {response.status_code}")
        
        if response.status_code == 401:
            print("  - Authentication failed. Please check your SONAR_TOKEN")
            return {}
        elif response.status_code == 404:
            print(f"  - Project {project_key} not found in SonarCloud")
            return {}
        
        response.raise_for_status()
        data = response.json()
        
        if 'errors' in data:
            print(f"  - API returned errors: {data['errors']}")
            return {}
            
        measures = {}
        for measure in data.get('component', {}).get('measures', []):
            measures[measure['metric']] = measure.get('value')
        
        if not measures:
            print(f"  - No measures found in response for {project_key}")
            print(f"  - Response content: {data}")
            
        return measures
    except requests.exceptions.RequestException as e:
        print(f"  - ERROR: Failed to get measures for {project_key}: {e}")
        return {}
    except ValueError as e:
        print(f"  - ERROR: Invalid JSON response for {project_key}: {e}")
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

def verify_project_exists(project_key):
    """Verify if a project exists in SonarCloud."""
    url = f"{SONAR_HOST}/api/projects/search"
    params = {
        'projects': project_key,
        'organization': SONAR_ORGANIZATION
    }
    print(f"DEBUG: Checking project existence with URL: {url} and params: {params}")
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        print(f"DEBUG: Response status code: {response.status_code}")
        print(f"DEBUG: Response text: {response.text}")
        if response.status_code == 200:
            data = response.json()
            components = data.get('components', [])
            return len(components) > 0
        return False
    except Exception as e:
        print(f"  - ERROR: Failed to verify project existence: {e}")
        return False

def process_project(project_info):
    """Process a single SonarCloud project and return data for database."""
    project_key = project_info['project_key']
    repo_name = project_info['repo_name']
    
    print(f"  - Processing project: {project_key}")
    
    # Verify project exists
    if not verify_project_exists(project_key):
        print(f"  - Project {project_key} does not exist in SonarCloud organization {SONAR_ORGANIZATION}")
        print("  - Please make sure:")
        print("    1. The project has been created in SonarCloud")
        print("    2. The project key is correct")
        print("    3. The organization name is correct")
        print("    4. Your SonarCloud token has the necessary permissions")
        return []
    
    # Get latest analysis info
    analysis_info = get_latest_analysis(project_key)
    if not analysis_info:
        print(f"  - No analysis found for {project_key}")
        return []
    
    # Get measures
    measures = get_project_measures(project_key)
    if not measures:
        print(f"  - No measures found for {project_key}")
        return []
    
    # Get quality gate status
    quality_gate = get_quality_gate_status(project_key)
    
    # Parse analysis date
    try:
        analysis_date = datetime.fromisoformat(analysis_info['date'].replace('Z', '+00:00'))
    except (ValueError, KeyError) as e:
        print(f"  - Error parsing analysis date: {e}. Using current time.")
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

def verify_sonar_access():
    """Verify SonarCloud token and organization access."""
    # First verify the token with a simpler API endpoint
    validate_url = f"{SONAR_HOST}/api/authentication/validate"
    try:
        validate_response = requests.get(validate_url, headers=HEADERS)
        if validate_response.status_code == 401:
            print("ERROR: Invalid SonarCloud token")
            return False
        
        # Check if the token is valid
        validate_data = validate_response.json()
        if not validate_data.get('valid', False):
            print("ERROR: SonarCloud token is not valid")
            return False
            
        # Now check organization access
        org_url = f"{SONAR_HOST}/api/organizations/search"
        org_params = {'organizations': SONAR_ORGANIZATION}
        org_response = requests.get(org_url, headers=HEADERS, params=org_params)
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
    """Main function to fetch SonarCloud data and store in database."""
    # Validate required environment variables
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
            print(f"  - {var}")
        print("Please set these variables in your .env file")
        return
        
    # Verify SonarCloud access
    if not verify_sonar_access():
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