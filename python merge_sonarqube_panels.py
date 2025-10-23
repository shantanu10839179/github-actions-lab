import json

# Load your existing dashboard JSON
with open("Final DevOps Grafana Dashboard.json", "r", encoding="utf-8") as f:
    dashboard = json.load(f)

# SonarQube panels to add
sonarqube_panels = [
    {
        "id": 200,
        "title": "SonarQube Coverage Over Time",
        "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
        "fieldConfig": { "defaults": {}, "overrides": [] },
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 100 },
        "options": {
            "legend": { "displayMode": "list", "placement": "bottom", "showLegend": True },
            "tooltip": { "mode": "single" }
        },
        "pluginVersion": "12.0.0",
        "targets": [
            {
                "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
                "editorMode": "code",
                "format": "time_series",
                "rawQuery": True,
                "rawSql": "SELECT analysis_date AS \"time\", project_key, coverage::float FROM sonarqube_results WHERE $__timeFilter(analysis_date) AND project_key = 'shantanu10839179_github-actions-lab' ORDER BY analysis_date ASC;",
                "refId": "A"
            }
        ],
        "type": "timeseries"
    },
    {
        "id": 201,
        "title": "SonarQube Bugs, Vulnerabilities, Code Smells",
        "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
        "fieldConfig": { "defaults": {}, "overrides": [] },
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 100 },
        "options": {
            "orientation": "auto",
            "showValue": "auto",
            "legend": { "displayMode": "list", "placement": "bottom", "showLegend": True }
        },
        "pluginVersion": "12.0.0",
        "targets": [
            {
                "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
                "editorMode": "code",
                "format": "table",
                "rawQuery": True,
                "rawSql": "SELECT analysis_date AS \"time\", bugs::int, vulnerabilities::int, code_smells::int FROM sonarqube_results WHERE $__timeFilter(analysis_date) AND project_key = 'shantanu10839179_github-actions-lab' ORDER BY analysis_date ASC;",
                "refId": "A"
            }
        ],
        "type": "barchart"
    },
    {
        "id": 202,
        "title": "SonarQube Reliability Rating",
        "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
        "fieldConfig": { "defaults": {}, "overrides": [] },
        "gridPos": { "h": 4, "w": 4, "x": 0, "y": 108 },
        "options": { "colorMode": "value", "graphMode": "none", "justifyMode": "auto", "orientation": "auto" },
        "pluginVersion": "12.0.0",
        "targets": [
            {
                "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
                "editorMode": "code",
                "format": "table",
                "rawQuery": True,
                "rawSql": "SELECT reliability_rating::float FROM sonarqube_results WHERE project_key = 'shantanu10839179_github-actions-lab' ORDER BY analysis_date DESC LIMIT 1;",
                "refId": "A"
            }
        ],
        "type": "stat"
    },
    {
        "id": 203,
        "title": "SonarQube Security Rating",
        "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
        "fieldConfig": { "defaults": {}, "overrides": [] },
        "gridPos": { "h": 4, "w": 4, "x": 4, "y": 108 },
        "options": { "colorMode": "value", "graphMode": "none", "justifyMode": "auto", "orientation": "auto" },
        "pluginVersion": "12.0.0",
        "targets": [
            {
                "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
                "editorMode": "code",
                "format": "table",
                "rawQuery": True,
                "rawSql": "SELECT security_rating::float FROM sonarqube_results WHERE project_key = 'shantanu10839179_github-actions-lab' ORDER BY analysis_date DESC LIMIT 1;",
                "refId": "A"
            }
        ],
        "type": "stat"
    },
    {
        "id": 204,
        "title": "SonarQube Maintainability Rating",
        "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
        "fieldConfig": { "defaults": {}, "overrides": [] },
        "gridPos": { "h": 4, "w": 4, "x": 8, "y": 108 },
        "options": { "colorMode": "value", "graphMode": "none", "justifyMode": "auto", "orientation": "auto" },
        "pluginVersion": "12.0.0",
        "targets": [
            {
                "datasource": { "type": "grafana-postgresql-datasource", "uid": "cf1wcvvbfak8wd" },
                "editorMode": "code",
                "format": "table",
                "rawQuery": True,
                "rawSql": "SELECT maintainability_rating::float FROM sonarqube_results WHERE project_key = 'shantanu10839179_github-actions-lab' ORDER BY analysis_date DESC LIMIT 1;",
                "refId": "A"
            }
        ],
        "type": "stat"
    }
]

# Remove any SonarQube panels from inside targets arrays (if any were accidentally placed there)
for panel in dashboard.get("panels", []):
    if "targets" in panel and isinstance(panel["targets"], list):
        panel["targets"] = [t for t in panel["targets"] if not isinstance(t, dict) or "rawSql" not in t or "sonarqube_results" not in t["rawSql"]]

# Append SonarQube panels as new objects at the end of the panels array
dashboard["panels"].extend(sonarqube_panels)

# Write the corrected JSON to a new file
with open("Final DevOps Grafana Dashboard - Merged.json", "w", encoding="utf-8") as f:
    json.dump(dashboard, f, indent=2)