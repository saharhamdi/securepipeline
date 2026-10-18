# SecurePipeline — Secure DevSecOps CI/CD Pipeline

**Automated security testing, vulnerability detection and policy enforcement for Docker-based applications.**

SecurePipeline is a DevSecOps project built with GitHub Actions to integrate automated security controls into the CI/CD lifecycle of a Python Flask application.

The pipeline combines application testing, secrets detection, static application security testing (SAST), software composition analysis (SCA), container image scanning and Software Bill of Materials (SBOM) generation.

A centralized security gate evaluates the results against predefined policies and prevents the publication of the container image when a mandatory check fails.

Security findings are presented in an explanatory report in French, including their severity, location and recommended remediation steps.

## Key Features

- **Automated testing:** Python unit tests and configurable code coverage requirements.
- **Secrets detection:** Gitleaks scans the Git repository and its available history for exposed credentials.
- **Static application security testing (SAST):** Semgrep identifies potentially insecure code patterns.
- **Dependency vulnerability scanning (SCA):** pip-audit checks Python dependencies against known vulnerability data.
- **Container security:** Trivy scans container images and supported configuration files.
- **SBOM generation:** Syft generates software inventories in CycloneDX and SPDX formats.
- **SBOM vulnerability analysis:** Grype identifies known vulnerabilities affecting discovered components.
- **Security policy enforcement:** a dedicated gate evaluates the pipeline results before publication.
- **French security reports:** findings, affected locations, severity levels and remediation guidance.
- **Automated image publication:** approved container images are published to GitHub Container Registry (GHCR), subject to the configured workflow conditions.
- **Scheduled dependency analysis:** an additional OWASP Dependency-Check workflow can run on a schedule or manually.

## Architecture

```text
                         Git Push / Pull Request
                                   |
                                   v
                       +-----------------------+
                       |   GitHub Actions CI   |
                       +-----------------------+
                                   |
                  +----------------+----------------+
                  |                |                |
                  v                v                v
          +---------------+ +------------+ +----------------+
          | Build & Test  | |  Gitleaks  | |    Semgrep     |
          | pytest/cover  | |   Secrets  | |      SAST      |
          +---------------+ +------------+ +----------------+
                  |
                  v
          +----------------+
          |    Docker      |
          | Image Build    |
          +----------------+
                  |
                  v
          +----------------+
          |     Trivy      |
          | Image / Config |
          +----------------+
                  |
                  v
          +----------------+
          |      Syft      |
          |  SBOM Creation |
          +----------------+
                  |
                  v
          +----------------+
          |     Grype      |
          | SBOM Scanning  |
          +----------------+

          +----------------+   +----------------+
          |   pip-audit    |   | Dependency-    |
          | Python SCA     |   | Check (OWASP)  |
          +----------------+   +----------------+
                   \                /
                    \              /
                     v            v
                 +--------------------+
                 |   SECURITY GATE    |
                 | Evaluate CI Results|
                 +--------------------+
                           |
                    +------+------+
                    |             |
                    v             v
               All checks     Blocking check
                 passed          failed
                    |             |
                    v             v
             Publish to GHCR   Block publication
             (eligible push)   and report findings
```

The diagram represents the logical security flow. The actual execution order and parallelism are defined by the `needs` relationships and conditions in the GitHub Actions workflows.

## Security Controls

| Stage | Tool | Purpose | Blocking policy |
|---|---|---|---|
| Build & Test | pytest, pytest-cov | Validate application behavior and measure test coverage | Test failure or coverage below 70%, if enforced by the workflow |
| Secrets | Gitleaks | Detect exposed credentials in the scanned Git history and files | A detected secret, according to the configured policy |
| SAST | Semgrep | Identify insecure code patterns and potential application vulnerabilities | Findings with severity `ERROR`, according to the configured rules and report logic |
| Python SCA | pip-audit | Detect known vulnerabilities in Python dependencies | Vulnerabilities matching the configured blocking policy |
| Container scanning | Trivy | Scan the image for vulnerabilities and supported configuration issues | Qualifying `HIGH` or `CRITICAL` findings when a fix is available, if enforced |
| SBOM generation | Syft | Inventory software components in the container image | Generates the SBOM; findings are evaluated separately |
| SBOM scanning | Grype | Match discovered components against known vulnerability data | Qualifying `HIGH` or `CRITICAL` findings when a fix is available, if enforced |
| Security Gate | GitHub Actions | Evaluate the required jobs and enforce publication conditions | Publication is blocked when a required check fails |
| Image publication | GHCR | Store the approved container image | Runs only when the configured publication conditions are satisfied |

**Important:** The table describes the intended policy. Exact blocking behavior depends on the implemented workflow, scanner exit codes, report-processing logic and job conditions. A finding does not automatically block publication unless the relevant control is configured to enforce that decision.

## Project Structure

```text
securepipeline/
├── app/
│   └── main.py
├── tests/
│   └── test_app.py
├── scripts/
│   └── report.py
├── demo/
│   └── run_scenario.sh
├── .github/
│   └── workflows/
│       ├── secure-pipeline.yml
│       └── dependency-check.yml
├── .semgrep/
│   └── custom-rules.yml
├── .gitleaks.toml
├── .dockerignore
├── .gitignore
├── Dockerfile
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

### Main Components

- `app/main.py`: Flask demonstration API exposing the `/health` and `/users` endpoints.
- `tests/test_app.py`: automated tests for the application endpoints.
- `Dockerfile`: defines the container image, including a non-root runtime user, a slim base image, a health check and Gunicorn.
- `requirements.txt`: production Python dependencies.
- `requirements-dev.txt`: additional development and testing dependencies.
- `scripts/report.py`: processes scanner results, generates explanatory security reports and evaluates configured blocking rules.
- `.gitleaks.toml`: configures secrets scanning and approved exclusions.
- `.semgrep/custom-rules.yml`: contains project-specific rules for insecure Flask debug settings and SQL queries constructed with f-strings.
- `demo/run_scenario.sh`: prepares demonstration branches containing intentionally introduced security issues.
- `.github/workflows/secure-pipeline.yml`: defines the main CI/CD pipeline and its seven jobs.
- `.github/workflows/dependency-check.yml`: defines the additional OWASP Dependency-Check workflow.

## Getting Started

### Prerequisites

- A GitHub account and Git.
- Python 3.12 for local development.
- Docker for local container builds.
- A GitHub repository with Actions enabled.

### 1. Clone or initialize the repository

If you already have the project locally:

```bash
git init -b main
git add -A
git commit -m "feat: initialize SecurePipeline"
git remote add origin git@github.com:<YOUR_USERNAME>/securepipeline.git
git push -u origin main
```

Replace `<YOUR_USERNAME>` with your GitHub username.

If the repository is already initialized or connected to a remote, do not repeat the corresponding initialization commands.

### 2. Install dependencies and run the tests

```bash
python -m venv .venv
```

Activate the virtual environment.

On Linux or macOS:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the development dependencies and run the tests:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

If the project enforces a minimum coverage threshold, verify that the local test command uses the same coverage settings as the CI workflow.

### 3. Verify the pipeline

Open the repository on GitHub and navigate to **Actions**.

Verify that:

- The workflow starts on the expected events.
- The security jobs execute successfully.
- The security reports are generated.
- The Security Gate evaluates the required jobs correctly.
- Image publication occurs only when the configured conditions are met.

A clean pipeline should pass all mandatory checks, provided that the dependencies, base image, scanner databases and security policies are compatible with the current environment.

### 4. Configure branch protection

In GitHub, open **Settings → Rules → Rulesets** or the applicable branch protection settings.

For the `main` branch, configure:

- Pull requests before merging.
- Required status checks corresponding to the actual workflow jobs.
- The Security Gate as a required check, using its exact name as displayed by GitHub.
- Restrictions on direct pushes where appropriate.

Branch protection and the Security Gate serve different purposes: the workflow evaluates security conditions, while branch protection prevents unauthorized or non-compliant changes from being merged.

### 5. Configure OWASP Dependency-Check (optional)

If the additional workflow requires an NVD API key, create a repository Actions secret named:

`NVD_API_KEY`

Configure it under **Settings → Secrets and variables → Actions**.

The workflow can then use the key to access the National Vulnerability Database API, subject to the implemented configuration and API limits.

## Security Reports and Artifacts

The reporting script processes scanner outputs and produces an explanatory Markdown summary in French.

Depending on the available scanner output, reports can include:

- Finding type and description.
- Affected file and line number.
- Severity and vulnerability identifiers.
- Recommended remediation steps.
- The reason a finding does or does not block publication under the configured policy.

JSON reports and SBOM files can also be uploaded as GitHub Actions artifacts when artifact-upload steps are configured in the workflow.

**Note:** Artifact retention depends on the workflow settings and repository policies. Reports and SBOMs should be reviewed before sharing publicly because they may reveal internal file paths, component versions or security weaknesses.

## Demonstration Scenarios

The demonstration script prepares branches with intentionally introduced security issues. Use a disposable test repository and review the generated changes before pushing them.

Run one scenario at a time:

```bash
bash demo/run_scenario.sh secret
bash demo/run_scenario.sh image
bash demo/run_scenario.sh dependency
bash demo/run_scenario.sh sast
```

Push the generated branch and open a Pull Request:

```bash
git push -u origin demo/<SCENARIO>
```

Replace `<SCENARIO>` with the branch name actually created by the script.

### Scenario 1 — Exposed Secret

**Objective:** demonstrate secrets detection with Gitleaks.

Expected result: the scanner identifies the test token, and the configured policy blocks publication.

### Scenario 2 — Outdated Container Base Image

**Objective:** demonstrate image vulnerability scanning.

Expected result: Trivy or Grype reports applicable vulnerabilities in the image. Blocking occurs only if the findings satisfy the configured severity, fix-availability and exit-code conditions.

An outdated image is not automatically vulnerable to every CVE; the result depends on its actual components and the scanner databases.

### Scenario 3 — Vulnerable Python Dependency

**Objective:** demonstrate SCA with pip-audit.

Expected result: the scanner reports known vulnerabilities affecting the selected dependency version, if any match the available vulnerability data and the applicable package configuration.

### Scenario 4 — Insecure SQL Query

**Objective:** demonstrate custom SAST rules with Semgrep.

Expected result: Semgrep identifies the SQL query pattern if the code matches the configured rule, and the Security Gate blocks publication if the finding meets the blocking policy.

### What to verify during the demonstration

For each scenario:

1. Inspect the generated branch and confirm the intended change.
2. Push the branch and open a Pull Request.
3. Review the corresponding GitHub Actions run.
4. Identify the scanner responsible for the finding.
5. Open the `Summary` section and review the remediation guidance.
6. Confirm that the Security Gate and publication job behave according to the configured policy.

For a portfolio presentation, capture a successful run on `main`, a blocked run for the secret scenario, and a Pull Request prevented from merging by branch protection.

### Important: GitHub Secret Scanning

GitHub secret scanning or push protection may reject a test token before it reaches the repository.

Use a disposable repository and follow GitHub's documented test procedure or approved bypass mechanism, if available. Never disable protections on a production repository merely to demonstrate a detection rule.

The demonstration token must be synthetic and must not grant access to any real resource.

If a real credential is exposed, revoke or rotate it immediately. Deleting the file or commit does not invalidate the credential.

## Security Design Considerations

### Container hardening

The Docker image uses a slim Python base image and a non-root runtime user to reduce unnecessary components and privileges.

The image also defines a health check and runs the application through Gunicorn.

These controls reduce certain risks but do not guarantee that the image or application is secure. Base images and dependencies must be updated and rescanned regularly.

### Dependency management

Pinning dependency versions improves reproducibility, but it does not guarantee that dependencies are free of vulnerabilities.

Review vulnerability advisories, compatible fixed versions and transitive dependencies. Update and retest affected packages as part of the remediation process.

### Security policy

Blocking policies should be explicit, version-controlled and regularly reviewed.

In particular:

- Define which severities block publication.
- Distinguish fixable and currently unfixable vulnerabilities.
- Document accepted exceptions, including their justification and expiry.
- Review false positives instead of silently suppressing findings.
- Ensure that failed or skipped mandatory jobs cannot accidentally permit publication.

### Image versioning

Avoid relying exclusively on the mutable `latest` tag for production releases.

Prefer immutable image digests or unique version tags tied to a commit or release. This improves traceability and helps ensure that the artifact tested is the artifact deployed.

## Current Scope and Future Improvements

SecurePipeline focuses on CI/CD security checks, report generation, policy enforcement and container image publication.

The following capabilities are potential extensions, not part of the current scope unless implemented separately.

### Supply Chain Security

- Sign container images with Cosign.
- Attach SBOMs and provenance attestations to published images.
- Verify image signatures and provenance before deployment.

### Additional Application Security Testing

- Integrate OWASP ZAP for DAST against a dedicated test environment.
- Add integration tests and security regression tests.
- Introduce a documented vulnerability exception and VEX management process.

### Deployment and Runtime Security

- Introduce GitOps deployment with Argo CD.
- Deploy to Kubernetes with admission policies enforced by OPA or an equivalent policy engine.
- Use Vault or an equivalent secrets management solution.
- Add runtime detection with Falco.
- Monitor security and application metrics using Prometheus and Grafana.

### Continuous Improvement

- Track vulnerability remediation time.
- Measure pipeline execution time and scanner reliability.
- Reduce false positives through reviewed and documented rules.
- Define SLAs for critical and high-severity vulnerabilities.
- Regularly validate the Security Gate with automated negative test scenarios.

## Project Objectives

SecurePipeline demonstrates how DevSecOps practices can be integrated into a practical CI/CD workflow.

Its main objectives are to:

- Detect security issues earlier in the software lifecycle.
- Automate repeatable security checks.
- Improve vulnerability visibility and remediation.
- Enforce security policies before image publication.
- Improve container supply chain transparency through SBOM generation.
- Provide actionable reports for developers and security teams.

**SecurePipeline — Security checks automated, risks identified early, and publication controlled by policy.**
