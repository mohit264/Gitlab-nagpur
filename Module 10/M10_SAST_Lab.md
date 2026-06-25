# LAB WORKBOOK — MODULE 10
## Static Application Security Testing (SAST): Enable, Scan, Triage, Fix

---

**Duration:** 65 minutes  
**Project:** `robovision-controller` (from Day 1 labs)  
**Requires:** GitLab Ultimate access; Docker executor Runner  
**Lab file:** `07_Vulnerable_Apps/M09_M10_vulnerable_robovision_app.py`

---

## Lab Objectives

By the end of this lab you will have:
- Added SAST to a real CI/CD pipeline with one `include:` line
- Triggered a pipeline and observed SAST findings appear in the MR security widget
- Interpreted each finding: severity, CWE, file, line, remediation
- Fixed SQL Injection (CWE-89) and Hardcoded Credentials (CWE-798) vulnerabilities
- Re-run the pipeline to verify resolution
- Dismissed a false positive with a documented justification

---

## Lab Architecture

```
Developer commits          GitLab Runner                GitLab Platform
vulnerable code       →    pulls Semgrep image      →   Sidekiq ingests
to feature branch          mounts source code            gl-sast-report.json
                           runs SAST analysis            writes to PostgreSQL
                           uploads gl-sast-report.json
                                                          ↓
                                                     MR Security Widget
                                                     Security Dashboard
                                                     (findings visible to developer)
```

---

## PHASE 1 — Enable SAST and Trigger First Scan (15 minutes)

### Step 1.1 — Add the Vulnerable Application

First, ensure the vulnerable application exists in your project. From the `robovision-controller` project root, create `app/vulnerable_endpoints.py`:

> **Note:** This file intentionally contains security vulnerabilities for lab purposes. It is clearly marked in the code and must never be deployed to a real environment.

```bash
git checkout main
git pull origin main
git checkout -b feature/sast-lab-demo
```

Create `app/vulnerable_endpoints.py`:

```python
#!/usr/bin/env python3
"""
RoboVision — Vulnerable Endpoints (SAST Lab Only)
==================================================
INTENTIONALLY VULNERABLE — DO NOT DEPLOY
Contains: CWE-89, CWE-78, CWE-798, CWE-327, CWE-22, CWE-502

These vulnerabilities are seeded to demonstrate GitLab SAST detection.
Module 10 lab: enable SAST, observe findings, fix vulnerabilities.
"""

import hashlib
import os
import pickle
import subprocess
import sqlite3
import requests
from flask import Blueprint, request, jsonify, session

vulnerable_bp = Blueprint('vulnerable', __name__)

# ==============================================================
# CWE-798: HARDCODED CREDENTIALS
# Secret Detection AND SAST will flag these
# ==============================================================
ROBOT_API_KEY = "sk-robovision-prod-xK9mN2pQ8rT4wV6y"  # noqa — lab only
DB_PASSWORD = "RoboAdmin2024Secret!"                     # noqa — lab only


# ==============================================================
# CWE-89: SQL INJECTION
# SAST finding: python.lang.security.audit.formatted-sql-query
# ==============================================================
@vulnerable_bp.route('/api/v1/robot/find', methods=['GET'])
def find_robot():
    """Find a robot by ID — VULNERABLE to SQL Injection."""
    robot_id = request.args.get('robot_id', '')

    conn = sqlite3.connect('robovision.db')
    # ❌ CWE-89: User input concatenated directly into SQL query
    query = "SELECT id, name, state FROM robots WHERE id = '" + robot_id + "'"
    cursor = conn.execute(query)
    result = cursor.fetchall()
    conn.close()

    return jsonify({'robots': result})


@vulnerable_bp.route('/api/v1/operator/login', methods=['POST'])
def operator_login():
    """Operator login — VULNERABLE to SQL Injection."""
    username = request.json.get('username', '')
    password = request.json.get('password', '')

    # ❌ CWE-327: MD5 is not suitable for password hashing
    password_hash = hashlib.md5(password.encode()).hexdigest()

    conn = sqlite3.connect('robovision.db')
    # ❌ CWE-89: Format string SQL injection
    query = f"SELECT id FROM operators WHERE username='{username}' AND password_hash='{password_hash}'"
    cursor = conn.execute(query)
    user = cursor.fetchone()
    conn.close()

    if user:
        session['operator_id'] = user[0]
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Invalid credentials'}), 401


# ==============================================================
# CWE-78: OS COMMAND INJECTION
# SAST finding: python.lang.security.audit.subprocess-shell-true
# ==============================================================
@vulnerable_bp.route('/api/v1/diagnostic/network', methods=['POST'])
def network_diagnostic():
    """Network diagnostic — VULNERABLE to Command Injection."""
    target = request.json.get('target', '')

    # ❌ CWE-78: shell=True with user-controlled input
    result = subprocess.run(
        f"ping -c 2 {target}",
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    return jsonify({'output': result.stdout, 'error': result.stderr})


# ==============================================================
# CWE-22: PATH TRAVERSAL
# SAST finding: path-traversal detection
# ==============================================================
@vulnerable_bp.route('/api/v1/logs/fetch', methods=['GET'])
def fetch_log():
    """Fetch log file — VULNERABLE to Path Traversal."""
    log_name = request.args.get('name', '')

    # ❌ CWE-22: No validation that path stays within log directory
    log_path = os.path.join('/var/robovision/logs', log_name)
    try:
        with open(log_path, 'r') as f:
            return jsonify({'content': f.read()})
    except FileNotFoundError:
        return jsonify({'error': 'Log not found'}), 404


# ==============================================================
# CWE-502: UNSAFE DESERIALIZATION
# SAST finding: python.lang.security.audit.insecure-pickle-use
# ==============================================================
@vulnerable_bp.route('/api/v1/state/restore', methods=['POST'])
def restore_state():
    """Restore robot state — VULNERABLE to Unsafe Deserialization."""
    import base64
    state_data = request.json.get('state', '')

    # ❌ CWE-502: pickle.loads on user-supplied data = RCE
    try:
        state = pickle.loads(base64.b64decode(state_data))
        return jsonify({'restored': True, 'state': str(state)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
```

Commit the file:
```bash
git add app/vulnerable_endpoints.py
git commit -m "feat: add vulnerable endpoints for SAST lab demonstration

WARNING: This file intentionally contains security vulnerabilities.
For Module 10 SAST lab use only. DO NOT merge to main without fixing.

Vulnerabilities present:
- CWE-89: SQL Injection (find_robot, operator_login)
- CWE-78: Command Injection (network_diagnostic)
- CWE-22: Path Traversal (fetch_log)
- CWE-502: Unsafe Deserialization (restore_state)
- CWE-798: Hardcoded credentials (API key, DB password)
- CWE-327: MD5 for password hashing (operator_login)"
```

---

### Step 1.2 — Add SAST to the Pipeline

Open `.gitlab-ci.yml`. At the top of the file, add the SAST template include:

```yaml
# .gitlab-ci.yml — add SAST include at the top
include:
  - template: Jobs/SAST.gitlab-ci.yml          # ← ADD THIS LINE

# ... rest of your existing pipeline ...
stages:
  - validate
  - test
  - build
  - deploy-dev
  - deploy-qa
  - deploy-prod
```

**That's it.** One line enables SAST for all detected languages in the repository.

GitLab will:
1. Auto-detect Python in the repository
2. Inject a `semgrep-sast` job into the pipeline
3. Run Semgrep on all Python files
4. Upload `gl-sast-report.json` as a reports artifact
5. Parse findings and display in the MR security widget

Commit the pipeline change:
```bash
git add .gitlab-ci.yml
git commit -m "ci: enable GitLab SAST scanning

Adds GitLab managed SAST template. Semgrep will scan all Python files
and report findings via gl-sast-report.json artifact.

Reference: https://docs.gitlab.com/ee/user/application_security/sast/"
```

---

### Step 1.3 — Open a Merge Request

```bash
git push origin feature/sast-lab-demo
```

In GitLab:
1. Navigate to **Merge Requests → New merge request**
2. Source: `feature/sast-lab-demo` → Target: `main`
3. Title: `feat: SAST lab — vulnerable endpoints`
4. Description: `Module 10 SAST lab. Contains intentional vulnerabilities.`
5. Click **Create merge request**

> **Why MR?** SAST findings appear in the **MR Security Widget** — the in-context feedback that developers see during code review. If you push directly to `main`, findings still appear in the Security Dashboard but not in the MR workflow. The MR experience is what we want to demonstrate.

---

### Step 1.4 — Watch the SAST Pipeline Run

In the MR view, click the pipeline link. In the pipeline graph you should see:

```
validate  →  test  →  sast     →  build  →  deploy-dev  →  ...
             lint     semgrep  
             unit     (auto-
             tests    injected)
```

The `semgrep-sast` job was **automatically injected** by the template — you did not define it explicitly.

Click `semgrep-sast` to watch the job log:

```
[INFO] [Semgrep] Pulling analyzer image...
       registry.gitlab.com/security-products/semgrep:latest

[INFO] Scanning Python files...
       Found: app/vulnerable_endpoints.py
       Found: app/main.py
       Found: tests/test_api.py

[INFO] Applying security ruleset: p/default p/python

[INFO] Analysis complete.
       Files scanned: 3
       Rules applied: 284
       Findings: 7

[INFO] Writing gl-sast-report.json
[INFO] Uploading artifact: gl-sast-report.json

Job succeeded
```

> **Pipeline timing:** On first run, pulling the Semgrep Docker image takes 2–4 minutes. Subsequent runs use the cached image and take under 60 seconds for this codebase.

**First run complete time budget: approximately 5–8 minutes.**

---

## PHASE 2 — Read the Findings (15 minutes)

### Step 2.1 — Open the MR Security Widget

Navigate back to the **Merge Request** view. Scroll down past the diff. You should see:

```
╔═══════════════════════════════════════════════════════════════╗
║  Security scanning detected 7 potential vulnerabilities       ║
║                                                               ║
║  ● Critical  2   ● High  2   ● Medium  2   ● Low  1          ║
║                                                               ║
║  [Expand]                                                     ║
╚═══════════════════════════════════════════════════════════════╝
```

Click **Expand** to see the findings list.

---

### Step 2.2 — Examine Each Finding

Click on the **first critical finding**. The finding detail panel shows:

```
╔═══════════════════════════════════════════════════════════╗
║  SQL Injection                              Severity: CRITICAL
║  ─────────────────────────────────────────────────────────
║  File:    app/vulnerable_endpoints.py
║  Line:    38
║  CWE:     CWE-89 — Improper Neutralisation of Special
║           Elements used in an SQL Command
║  Scanner: Semgrep
║  Rule:    python.lang.security.audit.
║           formatted-sql-query.formatted-sql-query
║
║  Code:    query = "SELECT id, name, state FROM robots
║                    WHERE id = '" + robot_id + "'"
║
║  Description:
║  User input concatenated into an SQL query string. An attacker
║  can manipulate the query to access unauthorised data, modify
║  data, or execute database commands.
║
║  Remediation:
║  Use parameterised queries or an ORM to separate SQL code
║  from data. Example:
║    cursor.execute("SELECT ... WHERE id = ?", (robot_id,))
║
║  References:
║  • https://cwe.mitre.org/data/definitions/89.html
║  • https://owasp.org/Top10/A03_2021-Injection/
╚═══════════════════════════════════════════════════════════╝
```

**This is what GitLab delivers to the developer:** exact file, exact line, CWE ID, description, AND remediation guidance — before code review even begins.

### Step 2.3 — Map All Findings to CWEs

Complete this table as you review each finding in the MR:

| Finding # | Severity | File | Line | CWE | Vulnerability | Scanner Rule |
|---|---|---|---|---|---|---|
| 1 | Critical | vulnerable_endpoints.py | 38 | CWE-89 | SQL Injection (find_robot) | formatted-sql-query |
| 2 | Critical | vulnerable_endpoints.py | 50 | CWE-89 | SQL Injection (operator_login) | formatted-sql-query |
| 3 | High | vulnerable_endpoints.py | 15 | CWE-798 | Hardcoded API Key | secrets-detection |
| 4 | High | vulnerable_endpoints.py | 67 | CWE-78 | Command Injection | subprocess-shell-true |
| 5 | Medium | vulnerable_endpoints.py | 45 | CWE-327 | MD5 for password | insecure-hash-function |
| 6 | Medium | vulnerable_endpoints.py | 80 | CWE-22 | Path Traversal | path-traversal |
| 7 | Low | vulnerable_endpoints.py | 95 | CWE-502 | Unsafe Deserialization | insecure-pickle-use |

> **Note:** Exact line numbers may differ slightly depending on your editor/formatting. This is expected.

### Step 2.4 — Navigate Directly to the Vulnerable Line

Click the **file link** in the finding (e.g., `app/vulnerable_endpoints.py:38`). GitLab opens the file diff view, scrolled to the flagged line, with the finding highlighted in context.

**Observation:** You can see the vulnerability in context — the surrounding code, the function it's in, what data flows into the vulnerable call. This is the developer experience that makes SAST actionable.

---

### Step 2.5 — View in the Security Dashboard

Navigate to: **Security → Security Dashboard** (in the project or group).

The Security Dashboard shows:
- All vulnerabilities across all scans, aggregated
- Filter by: severity, scanner type, status, file
- Trend over time (once multiple pipeline runs exist)

Navigate to: **Security → Vulnerability Report**

This shows the full list with status controls. Note each finding is `Detected` state — awaiting triage.

---

## PHASE 3 — Fix the Vulnerabilities (25 minutes)

We will fix the two most critical findings: SQL Injection and Hardcoded Credentials.

### Fix 1: SQL Injection (CWE-89) — 10 minutes

Open `app/vulnerable_endpoints.py`. Find the two SQL injection vulnerabilities and fix them:

#### Fix `find_robot()`:

```python
@vulnerable_bp.route('/api/v1/robot/find', methods=['GET'])
def find_robot():
    """Find a robot by ID — FIXED: parameterised query."""
    robot_id = request.args.get('robot_id', '')

    # Validate input type before querying
    try:
        robot_id = int(robot_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'robot_id must be an integer'}), 400

    conn = sqlite3.connect('robovision.db')
    # ✅ FIXED CWE-89: Parameterised query — user input treated as DATA
    query = "SELECT id, name, state FROM robots WHERE id = ?"
    cursor = conn.execute(query, (robot_id,))    # Note: tuple argument
    result = cursor.fetchall()
    conn.close()

    return jsonify({'robots': result})
```

#### Fix `operator_login()`:

```python
@vulnerable_bp.route('/api/v1/operator/login', methods=['POST'])
def operator_login():
    """Operator login — FIXED: parameterised query + bcrypt."""
    username = request.json.get('username', '')
    password = request.json.get('password', '')

    # ✅ FIXED CWE-327: Use bcrypt instead of MD5
    # Note: For existing MD5 hashed passwords in DB, a migration is required.
    # New passwords should use bcrypt from this point forward.
    import bcrypt

    conn = sqlite3.connect('robovision.db')
    # ✅ FIXED CWE-89: Parameterised query for username lookup
    query = "SELECT id, password_hash FROM operators WHERE username = ?"
    cursor = conn.execute(query, (username,))    # Tuple required
    user = cursor.fetchone()
    conn.close()

    if user:
        stored_hash = user[1].encode('utf-8') if isinstance(user[1], str) else user[1]
        # ✅ bcrypt.checkpw handles timing-safe comparison
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            session['operator_id'] = user[0]
            return jsonify({'status': 'ok'})

    # Same error message for invalid username AND invalid password (prevent enumeration)
    return jsonify({'error': 'Invalid credentials'}), 401
```

### Fix 2: Hardcoded Credentials (CWE-798) — 5 minutes

Replace the hardcoded credentials with environment variable references:

```python
# ✅ FIXED CWE-798: Read from environment — set in GitLab CI/CD Variables (masked)
ROBOT_API_KEY = os.environ.get('ROBOT_API_KEY')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

if not ROBOT_API_KEY:
    raise RuntimeError("ROBOT_API_KEY environment variable not set")
if not DB_PASSWORD:
    raise RuntimeError("DB_PASSWORD environment variable not set")
```

> **Then in GitLab:** Settings → CI/CD → Variables → Add `ROBOT_API_KEY` (masked, protected) and `DB_PASSWORD` (masked, protected).

### Fix 3: Command Injection (CWE-78) — 5 minutes

```python
@vulnerable_bp.route('/api/v1/diagnostic/network', methods=['POST'])
def network_diagnostic():
    """Network diagnostic — FIXED: list args, validated input, no shell."""
    import re
    target = request.json.get('target', '')

    # ✅ Input validation: only allow valid hostnames/IPs
    if not re.match(r'^[a-zA-Z0-9.\-]{1,253}$', target):
        return jsonify({'error': 'Invalid target format'}), 400

    # ✅ FIXED CWE-78: List args (no shell), shell=False, validated input
    result = subprocess.run(
        ["ping", "-c", "2", target],    # List — shell never invoked
        shell=False,                     # Explicit: no shell
        capture_output=True,
        text=True,
        timeout=5                        # Timeout prevents DoS
    )
    return jsonify({'output': result.stdout})
```

### Fix 4: Path Traversal (CWE-22) — 5 minutes

```python
@vulnerable_bp.route('/api/v1/logs/fetch', methods=['GET'])
def fetch_log():
    """Fetch log file — FIXED: path validation."""
    log_name = request.args.get('name', '')

    LOG_BASE_DIR = '/var/robovision/logs'

    # ✅ FIXED CWE-22: Resolve full path and verify it stays within LOG_BASE_DIR
    requested_path = os.path.realpath(os.path.join(LOG_BASE_DIR, log_name))

    # Reject if resolved path escapes the log directory
    if not requested_path.startswith(LOG_BASE_DIR + os.sep):
        return jsonify({'error': 'Access denied'}), 403

    # Additional validation: only allow .log files
    if not requested_path.endswith('.log'):
        return jsonify({'error': 'Only .log files are accessible'}), 403

    try:
        with open(requested_path, 'r') as f:
            return jsonify({'content': f.read()})
    except FileNotFoundError:
        return jsonify({'error': 'Log not found'}), 404
```

### Fix 5: Unsafe Deserialization (CWE-502) — optional if time allows

```python
@vulnerable_bp.route('/api/v1/state/restore', methods=['POST'])
def restore_state():
    """Restore robot state — FIXED: JSON instead of pickle."""
    import json

    state_data = request.json.get('state', '')

    # ✅ FIXED CWE-502: JSON deserialization — no code execution possible
    try:
        state = json.loads(state_data)

        # Validate schema — never trust structure of deserialized data
        required_fields = {'robot_id', 'position', 'last_command', 'timestamp'}
        if not required_fields.issubset(state.keys()):
            return jsonify({'error': 'Invalid state format'}), 400

        # Type-validate each field
        if not isinstance(state['robot_id'], str):
            return jsonify({'error': 'Invalid robot_id type'}), 400

        return jsonify({'restored': True, 'robot_id': state['robot_id']})

    except (json.JSONDecodeError, KeyError) as e:
        return jsonify({'error': f'Invalid state data: {e}'}), 400
```

---

### Step 3.5 — Commit All Fixes

```bash
git add app/vulnerable_endpoints.py
git commit -m "fix: remediate SAST findings in vulnerable_endpoints.py

Fixes identified by GitLab SAST (Semgrep) scan:

CWE-89 (Critical) — SQL Injection:
  - find_robot(): parameterised query with integer validation
  - operator_login(): parameterised query with bcrypt password check

CWE-798 (High) — Hardcoded Credentials:
  - ROBOT_API_KEY and DB_PASSWORD moved to environment variables
  - Fail-fast on missing variables at startup

CWE-78 (High) — Command Injection:
  - network_diagnostic(): list args, shell=False, regex input validation

CWE-22 (Medium) — Path Traversal:
  - fetch_log(): realpath resolution + directory boundary check

CWE-327 (Medium) — Weak Cryptography:
  - operator_login(): bcrypt replaces MD5 for password hashing

CWE-502 (Low) — Unsafe Deserialization:
  - restore_state(): JSON replaces pickle; explicit schema validation

Security scan re-run will verify all findings resolved.
Refs: https://docs.gitlab.com/ee/user/application_security/sast/"

git push origin feature/sast-lab-demo
```

> **Critical observation:** After pushing the fix commit, **notice in the MR that existing approvals are removed** (because "remove approvals on new commits" is enabled from Module 4). The security fix requires re-review. This is the governance model working correctly.

---

### Step 3.6 — Watch the Re-Scan

The pipeline auto-triggers on the new commit. Watch the `semgrep-sast` job:

```
[INFO] Analysis complete.
       Files scanned: 3
       Rules applied: 284
       Findings: 1     ←  was 7, now 1!
```

Navigate back to the MR. The security widget now shows:

```
╔══════════════════════════════════════════════════════════╗
║  Security scanning detected 1 potential vulnerability    ║
║                                                          ║
║  ● Info  1  (was: Critical 2, High 2, Medium 2, Low 1)  ║
╚══════════════════════════════════════════════════════════╝
```

**What happened to the original 7 findings?**
- 6 findings: now show as **Resolved** — Semgrep no longer detects them in this MR
- 1 remaining: an `Info`-severity finding (possibly from a test file or a low-risk pattern) — examine it in Phase 4

---

## PHASE 4 — Triage a False Positive (10 minutes)

### Step 4.1 — Examine the Remaining Finding

Click on the remaining finding. It may look like:

```
Name:     Avoid using assert statements in production code
Severity: Info
File:     tests/test_api.py
Line:     12
CWE:      N/A
Rule:     python.lang.correctness.use-assert

Code:     assert response.status_code == 200
```

This is a **false positive** in the context of security scanning. `assert` in a test file is the correct usage of assert. SAST rules that flag `assert` are targeting production code where `assert` can be disabled with Python's `-O` flag. In test files, it is correct and expected.

### Step 4.2 — Dismiss the Finding

In the MR security widget, next to this finding:
1. Click **Dismiss**
2. Dismiss reason: Select **"False positive"**
3. Comment: `"Assert statements in test files are expected Python test patterns. This rule targets production code where assert can be disabled with -O flag. Not applicable in test context."`
4. Click **Confirm dismissal**

**Observe:** The finding disappears from the active finding count. The security widget now shows:

```
Security scanning detected 0 new vulnerabilities
```

### Step 4.3 — Verify the Audit Trail

Navigate to **Security → Vulnerability Report**. Filter by **Status: Dismissed**.

Find your dismissed finding. Click on it. Observe the audit record:

```
Status:    Dismissed
Dismissed by:   @your-username
Dismissed at:   [timestamp]
Reason:    False positive
Comment:   "Assert statements in test files are expected..."
```

**This audit record is permanent.** It proves that a human with GitLab credentials reviewed this specific finding and made a documented decision. This is the evidence a compliance auditor needs.

---

## Step 5 — Final Merge (if time allows)

With all critical/high findings fixed and the false positive dismissed:

1. Request review from a classmate
2. Classmate reviews the diff — confirms the parameterised queries, the environment variable pattern, the bcrypt usage
3. Classmate approves the MR
4. Merge to `main`

The merged MR audit trail now shows:
- All SAST findings from the original commit
- The fix commit resolving each finding
- The false positive dismissal with justification
- Code review approval
- Merge event

**This is a complete, auditable security-aware development workflow.**

---

## Lab Verification Checklist

- [ ] `app/vulnerable_endpoints.py` committed with intentional vulnerabilities
- [ ] `include: template: Jobs/SAST.gitlab-ci.yml` added to `.gitlab-ci.yml`
- [ ] MR created from feature branch to `main`
- [ ] SAST job (`semgrep-sast`) appeared in pipeline (auto-injected)
- [ ] Security widget appeared in MR with findings count
- [ ] At least 5 findings identified and mapped to CWE IDs
- [ ] SQL Injection finding: file, line, CWE-89, remediation note recorded
- [ ] SQL Injection fixed with parameterised query — finding resolved in re-scan
- [ ] Hardcoded credentials fixed with environment variables
- [ ] Re-scan shows reduced finding count
- [ ] False positive identified and dismissed with documented justification
- [ ] Dismissal visible in Vulnerability Report with audit trail

---

## Common Issues and Solutions

| Problem | Cause | Solution |
|---|---|---|
| `semgrep-sast` job not appearing | SAST template include missing or syntax error | Validate `.gitlab-ci.yml` with CI Lint tool |
| SAST job fails: `ERROR: image not found` | Runner cannot pull scanner image (air-gapped) | Set `SAST_ANALYZER_IMAGE_TAG` to local registry mirror |
| No findings after adding vulnerable code | File not committed; wrong branch; file excluded | Check `SAST_EXCLUDED_PATHS`; verify file is staged and committed |
| Findings don't appear in MR widget | Pipeline triggered as branch pipeline (not MR pipeline) | Ensure MR exists before pushing; check MR pipeline triggers |
| `semgrep-sast` times out | Large repository; insufficient Runner memory | Set `SAST_ANALYZER_IMAGE_PULL_POLICY: never` for cached image; increase Runner memory |
| Findings still showing after fix | Cached pipeline result; new commit needed | Push a new commit to trigger re-scan |

---

## Extension: Custom Semgrep Rules (if time allows)

GitLab SAST allows adding custom Semgrep rules specific to your application.

Create `.semgrep/custom-rules.yml`:

```yaml
rules:
  - id: robovision-hardcoded-robot-id
    patterns:
      - pattern: robot_id = "RV-$X"
    message: >
      Hardcoded robot ID detected. Robot IDs should come from
      configuration or runtime discovery, not source code.
    severity: WARNING
    languages: [python]
    metadata:
      category: security
      cwe: "CWE-798"
```

Add to pipeline:
```yaml
variables:
  SEMGREP_RULES: ".semgrep/"    # Point to custom rules directory
```

Commit a file containing `robot_id = "RV-001"` — your custom rule will fire.

---

## Key Takeaways

```
Before SAST:    Vulnerable code committed → reviewed → merged → deployed → 
                found by penetration tester 3 months later → expensive fix

After SAST:     Vulnerable code committed → SAST runs (60 seconds) →
                finding in MR widget (before review) → developer fixes →
                re-scan confirms fix → reviewed → merged → safe deployment
                
Time to detect: 3 months → 60 seconds
Cost to fix:    100× → 6×
Developer UX:   PDF report with no context → exact file/line in code review
```
