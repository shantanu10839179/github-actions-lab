
# Setting Up SonarCloud with GitHub Actions

This guide walks you through the steps to create a SonarCloud account, configure GitHub Actions, and set up the necessary properties and workflows.

## 1. Create a SonarCloud Account

1. Go to [https://sonarcloud.io](https://sonarcloud.io)
2. Click on **Sign up**.
3. Choose **GitHub** as your login provider.
4. Authorize SonarCloud to access your GitHub account.
5. Select your GitHub organization and install the SonarCloud GitHub App.
6. Create a new project by importing it from GitHub.

## 2. Generate a SonarCloud Token

1. In SonarCloud, click on your avatar > **My Account** > **Security**.
2. Generate a new token and copy it.
3. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**.
4. Add a new secret named `SONAR_TOKEN` and paste the token.

## 3. Add `sonar-project.properties`

Create a file named `sonar-project.properties` in the root of your repository with the following content:

```properties
sonar.projectKey=shantanu10839179_github-actions-lab
sonar.organization=shantanu10839179

```


## 4. Configure GitHub Actions Workflow

Create a file at `.github/workflows/build.yml` with the following content:

```yaml
name: Build
on:
  push:
    branches:
      - main
      - feature
  pull_request:
    types: [opened, synchronize, reopened]
jobs:
  sonarqube:
    name: SonarQube
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 
      - name: SonarQube Scan
        uses: SonarSource/sonarqube-scan-action@v6
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

## 5. Commit and Push

1. Commit the `sonar-project.properties` and workflow file.
2. Push to GitHub.
3. Check the Actions tab to see the workflow run and SonarCloud analysis.
4. Now Check the workflow in sonarqube it you will see it running.
