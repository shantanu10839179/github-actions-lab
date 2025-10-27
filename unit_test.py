- name: Run tests with coverage
  run: |
    pip install pytest pytest-cov
    pytest --cov=your_module --cov-report=xml

- name: SonarCloud Scan
  uses: SonarSource/sonarcloud-github-action@master
  with:
    args: >
      -Dsonar.organization=shantanu10839179
      -Dsonar.projectKey=shantanu10839179_github-actions-lab
      -Dsonar.python.coverage.reportPaths=coverage.xml
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}