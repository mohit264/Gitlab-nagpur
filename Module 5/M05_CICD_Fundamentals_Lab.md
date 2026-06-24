# LAB WORKBOOK — MODULE 5
## GitLab CI/CD Fundamentals: Building Your First Production Pipeline

---

**Duration:** 45 minutes  
**Requires:** GitLab project from Module 4 (`robovision-controller`) or new project  
**Runner:** GitLab.com shared Runners OR self-managed Docker executor Runner

---

## Lab Overview

```
Step 1  → Create a Python Flask application (the thing we'll build + test)
Step 2  → Write a 4-stage CI/CD pipeline in .gitlab-ci.yml
Step 3  → Commit, trigger, and watch the pipeline
Step 4  → Analyse job logs in each stage
Step 5  → Examine generated artifacts
Step 6  → Add a masked CI variable and use it
Step 7  → Introduce a test failure — observe pipeline behaviour
Step 8  → Fix the failure — verify pipeline recovery
```

---

## Step 1: Create the Sample Application (5 minutes)

In the `robovision-controller` project (from Module 4), create the following files. Use the Web IDE or git CLI.

### File: `app/main.py`

```python
#!/usr/bin/env python3
"""
RoboVision Controller API — Sample Flask Application
Used for CI/CD pipeline demonstration.
"""

from flask import Flask, jsonify, request
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint — returns 200 OK."""
    return jsonify({
        'status': 'healthy',
        'service': 'robovision-controller',
        'version': '1.0.0'
    }), 200


@app.route('/api/v1/robot/status', methods=['GET'])
def get_robot_status():
    """Return current robot status."""
    # In production, this would query hardware
    return jsonify({
        'robot_id': 'RV-001',
        'state': 'idle',
        'battery': 85,
        'last_command': None
    }), 200


@app.route('/api/v1/robot/command', methods=['POST'])
def send_command():
    """Send a command to the robot."""
    data = request.get_json()
    
    if not data or 'command' not in data:
        return jsonify({'error': 'command field required'}), 400
    
    command = data['command']
    valid_commands = ['move_forward', 'move_backward', 'turn_left', 'turn_right', 'stop']
    
    if command not in valid_commands:
        return jsonify({'error': f'invalid command. Must be one of: {valid_commands}'}), 400
    
    logger.info(f"Received command: {command}")
    
    return jsonify({
        'accepted': True,
        'command': command,
        'message': f'Command {command} queued for execution'
    }), 202


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

---

### File: `tests/test_api.py`

```python
"""
Tests for RoboVision Controller API
"""

import pytest
import json
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'version' in data


class TestRobotStatus:
    def test_status_returns_200(self, client):
        response = client.get('/api/v1/robot/status')
        assert response.status_code == 200

    def test_status_has_robot_id(self, client):
        response = client.get('/api/v1/robot/status')
        data = json.loads(response.data)
        assert 'robot_id' in data
        assert 'state' in data


class TestRobotCommand:
    def test_valid_command_accepted(self, client):
        response = client.post(
            '/api/v1/robot/command',
            data=json.dumps({'command': 'stop'}),
            content_type='application/json'
        )
        assert response.status_code == 202

    def test_invalid_command_rejected(self, client):
        response = client.post(
            '/api/v1/robot/command',
            data=json.dumps({'command': 'self_destruct'}),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_missing_command_rejected(self, client):
        response = client.post(
            '/api/v1/robot/command',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
```

---

### File: `requirements.txt`

```
flask==3.0.3
pytest==8.2.0
pytest-cov==5.0.0
flake8==7.1.0
```

---

### File: `requirements-prod.txt`

```
flask==3.0.3
gunicorn==22.0.0
```

---

### File: `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY app/ ./app/

EXPOSE 5000

# Run as non-root user (security best practice)
RUN adduser --disabled-password --gecos '' appuser
USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.main:app"]
```

---

### File: `app/__init__.py`

```python
# Package init
```

---

Commit these files:
```bash
git add app/ tests/ requirements*.txt Dockerfile
git commit -m "feat: add Flask application, tests, and Dockerfile for CI/CD lab"
git push origin main
```

*(If `main` is protected, push to a feature branch and create an MR — this is correct behaviour!)*

---

## Step 2: Write the CI/CD Pipeline (10 minutes)

Create `.gitlab-ci.yml` in the repository root:

```yaml
# ============================================================
# RoboVision Controller — CI/CD Pipeline
# GitLab CI/CD Fundamentals Lab
# ============================================================

# Global default settings — inherited by all jobs
default:
  image: python:3.11-slim
  before_script:
    - pip install --quiet -r requirements.txt

# Pipeline stages — executed left to right
# Jobs within a stage run in parallel
stages:
  - validate    # Syntax and style checking
  - test        # Unit tests with coverage
  - build       # Build Docker image
  - package     # Push to container registry

# ============================================================
# STAGE: validate
# ============================================================

lint-python:
  stage: validate
  script:
    - echo "▶ Running Python style checks (flake8)"
    - flake8 app/ tests/ --max-line-length=120 --statistics
    - echo "✅ Lint passed"
  # Only run on branches with open MRs, or on main
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'

# ============================================================
# STAGE: test
# ============================================================

unit-tests:
  stage: test
  script:
    - echo "▶ Running unit tests with coverage"
    - pytest tests/ 
        --cov=app 
        --cov-report=term-missing 
        --cov-report=xml:coverage.xml
        --junitxml=test-results.xml
        -v
    - echo "✅ Tests passed"
  coverage: '/TOTAL.*\s+(\d+%)$/'   # GitLab parses coverage % from this pattern
  artifacts:
    name: "test-results-${CI_COMMIT_SHORT_SHA}"
    paths:
      - test-results.xml
      - coverage.xml
    reports:
      junit: test-results.xml       # Displayed in MR as test summary
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    expire_in: 30 days
    when: always                    # Upload even on test failure — critical for diagnosis

# ============================================================
# STAGE: build
# ============================================================

build-image:
  stage: build
  image: docker:24.0.5              # Override default Python image with Docker
  services:
    - docker:24.0.5-dind            # Docker-in-Docker service
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
    IMAGE_TAG: "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA"
    IMAGE_TAG_LATEST: "$CI_REGISTRY_IMAGE:latest"
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - echo "▶ Building Docker image: $IMAGE_TAG"
    - docker build -t $IMAGE_TAG -t $IMAGE_TAG_LATEST .
    - echo "▶ Pushing image to GitLab Container Registry"
    - docker push $IMAGE_TAG
    - docker push $IMAGE_TAG_LATEST
    - echo "✅ Image pushed: $IMAGE_TAG"
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'  # Only build image on main branch
  tags:
    - docker                            # Requires a Runner with docker tag

# ============================================================
# STAGE: package
# ============================================================

# Generate deployment manifest (simulating what would go to Kubernetes)
generate-manifest:
  stage: package
  image: alpine:latest
  before_script: []                   # Override global before_script — no pip needed
  script:
    - echo "▶ Generating deployment manifest"
    - |
      cat > deployment-manifest.yaml << EOF
      # RoboVision Controller Deployment Manifest
      # Generated by pipeline ${CI_PIPELINE_ID}
      # Commit: ${CI_COMMIT_SHA}
      # Branch: ${CI_COMMIT_BRANCH}
      # Built by: ${GITLAB_USER_NAME}
      
      image: ${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHORT_SHA}
      environment: staging
      
      labels:
        pipeline_id: "${CI_PIPELINE_ID}"
        commit_sha: "${CI_COMMIT_SHORT_SHA}"
        built_at: "$(date -Iseconds)"
      EOF
    - cat deployment-manifest.yaml
    - echo "✅ Manifest generated"
  artifacts:
    name: "deployment-manifest-${CI_COMMIT_SHORT_SHA}"
    paths:
      - deployment-manifest.yaml
    expire_in: 90 days
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
```

Commit this file:
```bash
git add .gitlab-ci.yml
git commit -m "ci: add 4-stage CI/CD pipeline (validate → test → build → package)"
git push origin main   # or via MR if main is protected
```

---

## Step 3: Watch the Pipeline Execute (5 minutes)

1. In GitLab, navigate to: **CI/CD → Pipelines**
2. Find your pipeline — click it to open the pipeline graph
3. Observe:
   - Jobs in the same stage start simultaneously
   - `test` stage waits for `validate` to complete
   - `build` waits for `test`, etc.

**Pipeline Graph should look like:**
```
validate  →  test  →  build        →  package
────────────────────────────────────────────────
lint      →  unit  →  build-image  →  generate-manifest
           tests
```

4. Click on the `unit-tests` job to open its log

---

## Step 4: Analyse Job Logs (5 minutes)

### Reading the Job Log

In the `unit-tests` job log, find:

```
▶ Running unit tests with coverage

tests/test_api.py::TestHealthEndpoint::test_health_returns_200 PASSED   [ 14%]
tests/test_api.py::TestHealthEndpoint::test_health_returns_json PASSED   [ 28%]
tests/test_api.py::TestRobotStatus::test_status_returns_200 PASSED      [ 42%]
tests/test_api.py::TestRobotStatus::test_status_has_robot_id PASSED     [ 57%]
tests/test_api.py::TestRobotCommand::test_valid_command_accepted PASSED  [ 71%]
tests/test_api.py::TestRobotCommand::test_invalid_command_rejected PASSED[ 85%]
tests/test_api.py::TestRobotCommand::test_missing_command_rejected PASSED[100%]

---------- coverage: platform linux, python 3.11.x ----------
Name             Stmts   Miss  Cover
------------------------------------
app/main.py         42      8    81%
------------------------------------
TOTAL               42      8    81%

✅ Tests passed

Job succeeded
```

**Questions to ask (discussion):**
- Where is the Docker container for this job?
- How did `requirements.txt` get installed? (Answer: `before_script` in `default:`)
- What happened to `test-results.xml`? Where did it go? (Answer: uploaded as artifact to Object Storage)

---

## Step 5: Examine Artifacts (5 minutes)

### 5.1 Download Artifacts

In the `unit-tests` job view:
1. Click **Browse** or **Download** button on the right sidebar
2. Download `test-results.xml` — open it

```xml
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="7" errors="0" failures="0" ...>
    <testcase classname="tests.test_api.TestHealthEndpoint" 
              name="test_health_returns_200" time="0.012"/>
    ...
  </testsuite>
</testsuites>
```

### 5.2 View Test Report in MR

If your pipeline ran on a merge request:
1. Navigate to the MR
2. Scroll to the bottom
3. Find the **Test summary** widget showing passed/failed/skipped counts

### 5.3 View Coverage Percentage

In the pipeline view, the `unit-tests` job should show `81%` coverage badge. GitLab parsed this from the `coverage:` regex defined in the job.

---

## Step 6: Add a Masked CI Variable (5 minutes)

### 6.1 Create a Variable

1. Navigate to: **Settings → CI/CD → Variables**
2. Click **Add variable**
3. Configure:
   - **Key:** `ROBOVISION_API_VERSION`
   - **Value:** `v1.0.0`
   - **Type:** Variable
   - **Environment scope:** All environments
   - **Protect variable:** ✅ (only available on protected branches)
   - **Mask variable:** ✅ (value hidden in logs)
4. Click **Add variable**

### 6.2 Use the Variable in the Pipeline

Update the `generate-manifest` job in `.gitlab-ci.yml`:

```yaml
generate-manifest:
  stage: package
  image: alpine:latest
  before_script: []
  script:
    - echo "▶ Generating deployment manifest for API version: $ROBOVISION_API_VERSION"
    - |
      cat > deployment-manifest.yaml << EOF
      image: ${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHORT_SHA}
      api_version: ${ROBOVISION_API_VERSION}
      environment: staging
      EOF
```

Commit and push. In the job log you will see `v1.0.0` but if you change the variable to a credential (e.g., set **Mask** = true with value like `sk-abc123xyz`), the log will show `[MASKED]` instead.

---

## Step 7: Introduce a Test Failure (5 minutes)

### 7.1 Break a Test

Edit `app/main.py` — change the health response to return 500:

```python
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint — intentionally broken for lab."""
    return jsonify({
        'status': 'healthy',
        'service': 'robovision-controller',
        'version': '1.0.0'
    }), 500   # ← Changed from 200 to 500 (intentional failure)
```

Commit and push:
```bash
git add app/main.py
git commit -m "bug: break health endpoint (lab demo)"
git push origin main
```

### 7.2 Observe Pipeline Failure

In the pipeline view:
- `validate` stage: ✅ Passes (lint doesn't care about logic)
- `test` stage: ❌ `unit-tests` FAILS
- `build` stage: ⏩ Skipped (because test stage failed)
- `package` stage: ⏩ Skipped

**Key Observation:**
> The pipeline stopped at the `test` stage. Nothing in `build` or `package` ran. The broken code cannot be packaged or deployed. **This is the pipeline gate working correctly.**

Observe that `test-results.xml` was still uploaded as an artifact (because `when: always` is set). This lets you see *which* test failed even when the pipeline is broken.

```
tests/test_api.py::TestHealthEndpoint::test_health_returns_200 FAILED   [ 14%]

FAILED tests/test_api.py::TestHealthEndpoint::test_health_returns_200
  AssertionError: assert 500 == 200
```

---

## Step 8: Fix the Failure (5 minutes)

### 8.1 Fix the Code

```python
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint — fixed."""
    return jsonify({
        'status': 'healthy',
        'service': 'robovision-controller',
        'version': '1.0.0'
    }), 200   # ← Restored to 200
```

```bash
git add app/main.py
git commit -m "fix: restore health endpoint to return 200"
git push origin main
```

### 8.2 Watch Recovery

In the Pipelines view you can now see:
- Previous commit: ❌ Failed (broken health check)
- Current commit: ✅ Passed (all stages green)

**GitLab Pipeline Graph across commits:**
```
Commit abc123 (broken):  validate ✅ → test ❌ → build ⏩ → package ⏩
Commit def456 (fixed):   validate ✅ → test ✅ → build ✅ → package ✅
```

---

## Lab Verification Checklist

- [ ] `.gitlab-ci.yml` committed and pipeline triggered
- [ ] All 4 stages visible in pipeline graph
- [ ] `unit-tests` job log shows individual test results
- [ ] `test-results.xml` artifact available for download
- [ ] Coverage percentage visible in job sidebar
- [ ] CI variable `ROBOVISION_API_VERSION` created and masked
- [ ] Variable appears in `generate-manifest` job output
- [ ] Intentional failure: pipeline stopped at test stage
- [ ] Build and package stages were skipped on failure
- [ ] Fix committed: pipeline recovered to full green

---

## Extension: Pipeline Efficiency with `rules:`

Add this to the `build-image` job and observe:

```yaml
build-image:
  # Only build image when:
  # 1. Merging to main branch, OR
  # 2. A pipeline was manually triggered, OR
  # 3. A tag was created (release)
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
    - if: '$CI_PIPELINE_SOURCE == "web"'        # Manual trigger
    - if: '$CI_COMMIT_TAG'                       # Tag pipeline
    - when: never                                # Skip for everything else
```

Push a commit to a feature branch — observe that `build-image` is **skipped** (feature branches don't need a Docker build). Push to `main` — observe it **runs**.

---

## CI/CD YAML Reference Card

```yaml
# Pipeline-level keys
stages: [list]              # Defines stage order
default: {}                 # Defaults inherited by all jobs
variables: {}               # Pipeline-level variables
include: []                 # Import external YAML files
workflow: {}                # Controls when pipeline runs

# Job-level keys
stage: string               # Which stage this job belongs to
image: string               # Docker image for Docker executor
services: [list]            # Docker services (e.g., database, DinD)
script: [list]              # Main commands (required)
before_script: [list]       # Setup commands (runs before script)
after_script: [list]        # Cleanup (runs even on failure)
variables: {}               # Job-specific variables
artifacts: {}               # Files to preserve
rules: [list]               # Conditions for running
needs: [list]               # DAG dependencies (skip stage ordering)
tags: [list]                # Runner tag selection
when: string                # on_success|on_failure|always|manual|delayed
allow_failure: bool         # Don't fail pipeline if job fails
timeout: duration           # Job timeout
retry: int|{}               # Retry on failure
environment: string|{}      # Deployment environment
```

---

## Troubleshooting Guide

| Error | Cause | Fix |
|---|---|---|
| `yaml: invalid character` | YAML syntax error | Use CI Lint tool: CI/CD → Pipelines → CI Lint |
| `ERROR: Job failed: exit code 1` | Script command failed | Check job log for which command failed |
| `ERROR: Could not pull image` | Docker image not found | Verify image name and tag |
| `WARNING: No matching runner` | No Runner with required tags | Check Runner tags match job `tags:` |
| `This job is stuck, isn't running` | No available Runners | Register a Runner; check Runner status |
| `Artifacts not found` | Path doesn't match actual output | Check `artifacts: paths:` matches real file location |
| `coverage: value not found` | Regex doesn't match output format | Test coverage regex in CI Lint or locally |
| `Permission denied: /var/run/docker.sock` | Runner not in docker group | Use Docker-in-Docker (`services: docker:dind`) |
