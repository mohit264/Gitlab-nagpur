# LAB WORKBOOK — MODULE 6
## Enterprise Delivery Pipeline: Dev → QA → Production with Manual Approval

---

**Duration:** 50 minutes  
**Builds on:** Module 5 pipeline (`robovision-controller` project)

---

## Lab Overview

Extend the Module 5 pipeline into a full enterprise delivery pipeline:

```
┌──────────┐  ┌──────┐  ┌──────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐
│ validate │→ │ test │→ │    build     │→ │ deploy-dev │→ │ deploy-qa  │→ │ deploy-prod │
│ lint     │  │ unit │  │ docker-image │  │  auto      │  │  auto      │  │  MANUAL     │
└──────────┘  └──────┘  └──────────────┘  └────────────┘  └────────────┘  └─────────────┘
                                                                                  ↑
                                                                           Click to approve
```

---

## Step 1: Configure Environment-Scoped Variables (10 minutes)

### 1.1 Create Scoped Variables

Navigate to **Settings → CI/CD → Variables** and create:

| Key | Value | Environment Scope | Masked | Protected |
|---|---|---|---|---|
| `APP_ENV` | `development` | `dev` | ❌ | ❌ |
| `APP_ENV` | `qa` | `qa` | ❌ | ❌ |
| `APP_ENV` | `production` | `production` | ❌ | ✅ |
| `DATABASE_URL` | `postgresql://dev-db:5432/robovision` | `dev` | ✅ | ❌ |
| `DATABASE_URL` | `postgresql://qa-db:5432/robovision` | `qa` | ✅ | ❌ |
| `DATABASE_URL` | `postgresql://prod-db:5432/robovision` | `production` | ✅ | ✅ |
| `DEPLOY_TOKEN` | `lab-deploy-token-dev` | `dev` | ✅ | ❌ |
| `DEPLOY_TOKEN` | `lab-deploy-token-prod` | `production` | ✅ | ✅ |

**Observe:** Same variable key (`DATABASE_URL`), different values per environment scope. The job running in the `production` environment context receives the production value automatically.

### 1.2 Create Protected Production Environment

Navigate to **Settings → CI/CD → Protected Environments**:

1. Click **Protect an environment**
2. Environment: `production`
3. Allowed to deploy: `Maintainers`
4. Click **Protect**

This means only Maintainers can trigger the production deployment job.

---

## Step 2: Replace `.gitlab-ci.yml` with Enterprise Pipeline (20 minutes)

Replace the entire `.gitlab-ci.yml` from Module 5 with the enterprise version below:

```yaml
# ============================================================
# RoboVision Controller — Enterprise Delivery Pipeline
# Module 6: Environment Promotion + Manual Approval Gate
#
# Pipeline Flow:
#   validate → test → build → deploy-dev → deploy-qa → deploy-prod
#
# deploy-prod requires MANUAL approval (Maintainers only)
# Environment-scoped variables provide per-env configuration
# ============================================================

default:
  image: python:3.11-slim
  before_script:
    - pip install --quiet -r requirements.txt
  retry:
    max: 1
    when:
      - runner_system_failure

stages:
  - validate
  - test
  - build
  - deploy-dev
  - deploy-qa
  - deploy-prod

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  PYTHONPATH: "."
  IMAGE_TAG: "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA"

# ─── STAGE: validate ─────────────────────────────────────────

lint:
  stage: validate
  script:
    - flake8 app/ tests/ --max-line-length=120
  cache:
    key: pip-cache
    paths:
      - .cache/pip
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH =~ /^(main|develop)$/'

# ─── STAGE: test ─────────────────────────────────────────────

unit-tests:
  stage: test
  script:
    - pytest tests/ --cov=app --cov-report=xml:coverage.xml --junitxml=test-results.xml -v
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      junit: test-results.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    paths:
      - test-results.xml
      - coverage.xml
    expire_in: 30 days
    when: always
  cache:
    key: pip-cache
    paths:
      - .cache/pip

# ─── STAGE: build ────────────────────────────────────────────

build-image:
  stage: build
  image: docker:24.0.5
  services:
    - docker:24.0.5-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - echo "▶ Building $IMAGE_TAG"
    - docker build -t $IMAGE_TAG .
    - docker push $IMAGE_TAG
    - echo "✅ Image pushed"
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
    - if: '$CI_COMMIT_TAG'
  tags:
    - docker

# ─── STAGE: deploy-dev ───────────────────────────────────────
# Automatic deployment to development environment

deploy-dev:
  stage: deploy-dev
  image: alpine:latest
  before_script: []
  script:
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  DEPLOYING TO DEVELOPMENT ENVIRONMENT"
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  App Environment : $APP_ENV"
    - echo "  Image Tag       : $IMAGE_TAG"
    - echo "  Database URL    : $DATABASE_URL"
    - echo "  Commit SHA      : $CI_COMMIT_SHA"
    - echo "  Deployed By     : $GITLAB_USER_NAME"
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    # In a real deployment, this would be:
    # - kubectl set image deployment/robovision-controller app=$IMAGE_TAG -n development
    # - kubectl rollout status deployment/robovision-controller -n development
    - echo "✅ Deployed to development"
  environment:
    name: dev
    url: https://dev.robovision.lab
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'

# ─── STAGE: deploy-qa ────────────────────────────────────────
# Automatic deployment to QA after dev succeeds

deploy-qa:
  stage: deploy-qa
  image: alpine:latest
  before_script: []
  script:
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  DEPLOYING TO QA ENVIRONMENT"
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  App Environment : $APP_ENV"
    - echo "  Image Tag       : $IMAGE_TAG"
    - echo "  Database URL    : $DATABASE_URL"
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "▶ Running smoke tests against QA environment..."
    - sleep 2   # Simulating smoke test execution
    - echo "✅ Smoke tests passed"
    - echo "✅ Deployed to QA"
  environment:
    name: qa
    url: https://qa.robovision.lab
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'

# ─── Approval Check Job (informational) ──────────────────────
# This job runs automatically after QA and provides a summary
# before the manual production gate

pre-production-checklist:
  stage: deploy-prod
  image: alpine:latest
  before_script: []
  script:
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  PRE-PRODUCTION DEPLOYMENT CHECKLIST"
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  ✅ Lint passed"
    - echo "  ✅ Unit tests passed"
    - echo "  ✅ Docker image built and pushed"
    - echo "  ✅ Development deployment successful"
    - echo "  ✅ QA deployment successful"
    - echo "  ✅ Smoke tests passed"
    - echo ""
    - echo "  Commit     : $CI_COMMIT_SHA"
    - echo "  Branch     : $CI_COMMIT_BRANCH"  
    - echo "  Image      : $IMAGE_TAG"
    - echo "  Pipeline   : $CI_PIPELINE_URL"
    - echo ""
    - echo "  ⚠️  Production deployment requires Maintainer approval."
    - echo "  ⚠️  See deploy-production job below (manual trigger)."
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'

# ─── STAGE: deploy-prod ──────────────────────────────────────
# MANUAL GATE — requires human approval before production deployment
# Only users with Maintainer role (on protected environment) can trigger

deploy-production:
  stage: deploy-prod
  image: alpine:latest
  before_script: []
  # KEY: when: manual pauses the pipeline here
  # The job sits in the UI as a clickable Play button
  # Only users with deployment access to 'production' environment can click it
  when: manual
  script:
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  DEPLOYING TO PRODUCTION"
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  ⚠️  PRODUCTION DEPLOYMENT INITIATED"
    - echo "  Approved By     : $GITLAB_USER_NAME"
    - echo "  Image Tag       : $IMAGE_TAG"
    - echo "  App Environment : $APP_ENV"
    - echo "  Database URL    : $DATABASE_URL"
    - echo "  Timestamp       : $(date -Iseconds)"
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    # In production this would be:
    # - kubectl set image deployment/robovision-controller app=$IMAGE_TAG -n production
    # - kubectl rollout status deployment/robovision-controller -n production --timeout=300s
    - echo "▶ Verifying production deployment health..."
    - sleep 3
    - echo "✅ Production deployment successful"
    - echo "✅ Health check passed"
  environment:
    name: production
    url: https://api.robovision.io
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      # Note: manual jobs are never auto-triggered even without this rule
      # The rule here controls whether the job APPEARS in the pipeline

# ─── Rollback Job (manual, emergency use only) ───────────────
rollback-production:
  stage: deploy-prod
  image: alpine:latest
  before_script: []
  when: manual
  script:
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  ⚠️  PRODUCTION ROLLBACK INITIATED"
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    - echo "  Initiated By    : $GITLAB_USER_NAME"
    - echo "  Timestamp       : $(date -Iseconds)"
    - echo ""
    - echo "  ROLLBACK PROCEDURE:"
    - echo "  1. Identify last stable deployment in Deployments page"
    - echo "  2. Re-run that pipeline's deploy-production job"
    - echo "  OR"
    - echo "  2. kubectl rollout undo deployment/robovision -n production"
    - echo ""
    - echo "  NOTE: This job is a placeholder. In production,"
    - echo "  rollback should re-deploy the previous stable image."
    - echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  environment:
    name: production
    action: rollback
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
```

Commit:
```bash
git add .gitlab-ci.yml
git commit -m "ci: extend to full enterprise pipeline with environment promotion and manual gate"
git push origin main
```

---

## Step 3: Watch the Pipeline Execute (10 minutes)

### 3.1 Observe Stage Progression

Navigate to **CI/CD → Pipelines → [your pipeline]**

You should see the pipeline progress automatically through:
```
validate ✅ → test ✅ → build ✅ → deploy-dev ✅ → deploy-qa ✅ → deploy-prod ⏸️
```

At `deploy-prod`, the pipeline pauses. You'll see:
- `pre-production-checklist` — runs automatically ✅
- `deploy-production` — shows a **▶️ Play** button (waiting for manual trigger)
- `rollback-production` — also shows a ▶️ Play button

### 3.2 Inspect Deploy-Dev Job Log

Click `deploy-dev` job. Observe that:
- `$APP_ENV` = `development` (environment-scoped variable)
- `$DATABASE_URL` = the development database URL

### 3.3 Inspect Deploy-QA Job Log

Click `deploy-qa` job. Observe that:
- `$APP_ENV` = `qa` (different value, same variable name)
- `$DATABASE_URL` = the QA database URL

**Key Teaching Point:** The pipeline YAML is identical for dev and qa deploy jobs — the same script runs. But the environment context causes GitLab to inject different variable values. This is how configuration-as-code and environment separation work together.

---

## Step 4: Approve the Production Deployment (5 minutes)

### 4.1 Review the Checklist

Click `pre-production-checklist` job — read the output. All checks passed.

### 4.2 Trigger Production Deployment

1. In the pipeline view, click the **▶️ Play** button next to `deploy-production`
2. A confirmation dialog appears: "Are you sure you want to run deploy-production?"
3. Click **OK**

### 4.3 Watch Production Deploy

The `deploy-production` job starts and logs:
```
DEPLOYING TO PRODUCTION
  Approved By: <your GitLab username>
  Image Tag: registry.../robovision-controller:abc12345
  App Environment: production
  Database URL: postgresql://prod-db:5432/robovision
  Timestamp: 2024-11-15T14:32:17+00:00

✅ Production deployment successful
```

**Critical Observation:** Note that `$GITLAB_USER_NAME` in the production log shows YOUR username. This is the audit record — who approved and executed the production deployment.

---

## Step 5: Explore the Deployments View (5 minutes)

Navigate to **Operate → Environments** (or **Deployments → Environments**):

You should see three environments:
```
┌─────────────────┬────────────────────────┬─────────────────────┐
│ Environment     │ Current Deployment     │ Last Deployed       │
├─────────────────┼────────────────────────┼─────────────────────┤
│ dev             │ abc12345 (running)     │ 2 minutes ago       │
│ qa              │ abc12345 (running)     │ 1 minute ago        │
│ production      │ abc12345 (running)     │ Just now            │
└─────────────────┴────────────────────────┴─────────────────────┘
```

Click on `production` → **Deployment history** shows every production deployment with:
- Commit SHA
- Who deployed
- When
- Pipeline link

This is the **deployment audit trail**.

---

## Step 6: Simulate a Bad Deployment and Rollback (5 minutes)

### 6.1 Deploy a Breaking Change

Edit `app/main.py` — return an error from all endpoints:

```python
# Simulate a bad deployment
@app.route('/health', methods=['GET'])
def health_check():
    # BUG: This crashes every request (simulating bad deployment)
    raise Exception("Simulated production bug")
```

```bash
git add app/main.py
git commit -m "bug: simulated bad deployment"
git push origin main
```

Wait for the pipeline to reach `deploy-production` (or skip to it).

### 6.2 Trigger Rollback

In the Environments view:
1. Navigate to **production** environment
2. Click **▶️ Re-deploy** on the **previous** deployment (not the current broken one)

OR in the pipeline for the *previous* good commit:
1. Find it in CI/CD → Pipelines
2. Click the `deploy-production` ▶️ button

**Teaching Point:** GitLab Environments make rollback trivial — you re-run the deployment job from any previous pipeline. In a real Kubernetes deployment, this re-deploys the old image tag.

### 6.3 Revert the Code

```bash
git revert HEAD --no-edit
git push origin main
```

---

## Step 7: Review the Audit Trail (5 minutes)

Navigate to **Group/Project → Compliance → Audit Events** (requires Maintainer+):

Find events:
```
deploy_production_triggered    actor: @your-username    environment: production
deploy_production_triggered    actor: @your-username    environment: production (rollback)
```

The audit log provides:
- Who triggered each production deployment
- Timestamp
- Pipeline reference
- Whether it was a new deployment or rollback

**This is the evidence** for: SOC 2 (change management), PCI DSS (production access control), internal audit.

---

## Lab Verification Checklist

- [ ] Environment-scoped variables created for dev, qa, production
- [ ] Protected environment configured for production (Maintainers only)
- [ ] Multi-stage pipeline: validate → test → build → deploy-dev → deploy-qa → deploy-prod
- [ ] Pipeline ran automatically through QA
- [ ] Pipeline paused at production manual gate
- [ ] Production deployment triggered manually
- [ ] Different `$DATABASE_URL` visible in dev vs production job logs
- [ ] Environments view shows deployment history
- [ ] Rollback procedure understood

---

## Key Pipeline YAML Patterns Learned

```yaml
# Manual gate
when: manual

# Environment tracking
environment:
  name: production
  url: https://api.example.com

# Rollback action
environment:
  name: production
  action: rollback

# Environment-scoped variable access
# (GitLab injects correct value based on 'environment: name:')

# Stage dependency: deploy-qa only runs after all deploy-dev jobs pass
stages:
  - deploy-dev
  - deploy-qa
  - deploy-prod
```
