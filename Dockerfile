FROM python:3.10-bullseye

# Install Java and utilities
RUN apt-get update && \
    apt-get install -y default-jre curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Install SonarScanner
RUN curl -sSLo sonar-scanner.zip https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip \
    && unzip sonar-scanner.zip -d /opt \
    && rm sonar-scanner.zip
ENV PATH="/opt/sonar-scanner-5.0.1.3006-linux/bin:${PATH}"

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy source code
COPY . .

# Run tests with coverage and SonarQube analysis
CMD pytest --cov=. --cov-report=xml:coverage.xml --junitxml=test-results.xml && \
    echo "Tests completed successfully!" && \
    echo "SonarQube URL: ${SONAR_HOST_URL:-http://host.docker.internal:9000}" && \
    echo "Project Key: ${SONAR_PROJECT_KEY:-python-demo-project}" && \
    sonar-scanner \
      -Dsonar.projectKey=${SONAR_PROJECT_KEY:-python-demo-project} \
      -Dsonar.host.url=${SONAR_HOST_URL:-http://host.docker.internal:9000} \
      -Dsonar.login=${SONAR_TOKEN:-admin} || \
    echo "SonarQube analysis failed - this is expected if SonarQube server is not running"