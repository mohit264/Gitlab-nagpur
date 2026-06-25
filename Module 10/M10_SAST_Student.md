# STUDENT HANDBOOK — MODULE 10
## Static Application Security Testing (SAST)

---

**Workshop:** GitLab Ultimate for Secure SDLC, DevSecOps, AI, Robotics & IoT
**Day:** 2 of 2 | **Module:** 10 of 16 | **Duration:** 90 minutes

---

## Learning Objectives

- Explain how SAST works: from source code to AST to finding
- Add GitLab SAST to a pipeline with one `include:` line
- Read and interpret a SAST finding: severity, CWE, location, remediation
- Fix SQL injection and hardcoded credential findings
- Dismiss a false positive with documented justification
- Understand when SAST is not sufficient and what complements it

---

## 1. How SAST Works

### The Core Concept

SAST (Static Application Security Testing) analyses source code **without executing it**. It looks for patterns that are known to be dangerous — or data flows where user-controlled input reaches a dangerous function without being sanitised.

### Two Analysis Approaches

**Pattern Matching**
```
Rule: flag any use of subprocess.run() where shell=True
Code: subprocess.run(f"ping {host}", shell=True)
      → MATCH → CWE-78 finding generated
```
Fast. Can have false positives (flags safe uses of the same pattern).

**Taint / Dataflow Analysis**
Tracks how data flows from user-controlled inputs (*sources*) to dangerous functions (*sinks*) without passing through a *sanitiser*.

```
Source:     robot_id = request.args.get('robot_id')   ← user-controlled (tainted)
Flow:       query = "SELECT ... WHERE id = '" + robot_id + "'"   ← taint propagates
Sink:       db.execute(query)                          ← tainted data in SQL execution
Sanitiser:  (none found between source and sink)
Result:     CWE-89 SQL Injection — finding generated
```

More accurate, fewer false positives, computationally heavier.

**GitLab uses Semgrep** — hybrid approach with AST awareness. Understands code structure, not just text patterns.

### The Internal Pipeline

```
Your Python file
      ↓
Lexer → Token stream ("SELECT", "*", "FROM", ...)
      ↓
Parser → Abstract Syntax Tree (AST)
      ↓
Semgrep rules applied to AST nodes
      ↓
Findings: {file, line, CWE, severity, snippet, remediation}
      ↓
gl-sast-report.json  (standard schema)
      ↓
Uploaded as artifact → GitLab parses → Security Dashboard
```

---

## 2. GitLab SAST — One Line to Enable

```yaml
# .gitlab-ci.yml
include:
  - template: Jobs/SAST.gitlab-ci.yml
```

**What this single line does:**
1. GitLab auto-detects all languages in your repository
2. Selects the correct analyzer for each language
3. Injects scanner jobs into your pipeline (no manual job definition needed)
4. Configures artifact upload with the `reports: sast:` key (GitLab parses this)
5. Findings appear in the MR Security Widget and Security Dashboard

Source: https://docs.gitlab.com/ee/user/application_security/sast/

### Language → Analyzer Mapping

| Language | Analyzer | Notes |
|---|---|---|
| Python | Semgrep | Primary; covers OWASP Top 10 patterns |
| JavaScript/TS | Semgrep | + ESLint security rules available |
| Java | Semgrep | + SpotBugs for bytecode analysis |
| Go | Semgrep | + Gosec |
| C / C++ | Semgrep | + Flawfinder (unsafe function detection) |
| Ruby | Semgrep | — |
| PHP | Semgrep | — |

Source: https://docs.gitlab.com/ee/user/application_security/sast/analyzers.html

---

## 3. Reading a SAST Finding

### The MR Security Widget Entry

```
┌─────────────────────────────────────────────────────────┐
│ SQL Injection                           Severity: CRITICAL│
├─────────────────────────────────────────────────────────┤
│ File:       app/vulnerable_endpoints.py                  │
│ Line:       38                                           │
│ CWE:        CWE-89                                       │
│ Confidence: High                                         │
│                                                          │
│ Code:  query = "SELECT ... WHERE id = '" + robot_id + "'"│
│                                                          │
│ Remediation:                                             │
│ Use parameterised queries:                               │
│   cursor.execute("SELECT ... WHERE id = ?", (robot_id,)) │
│                                                          │
│ [View in file]  [Dismiss]  [Create issue]               │
└─────────────────────────────────────────────────────────┘
```

### Field Meanings

| Field | What It Tells You |
|---|---|
| **Severity** | Critical / High / Medium / Low / Info — maps to Security Policy thresholds |
| **Confidence** | High / Medium / Low — likelihood of being a real issue (not false positive) |
| **File + Line** | Exact location — clickable, opens the diff at that line |
| **CWE** | The specific weakness type — links to MITRE CWE database definition |
| **Code snippet** | The flagged code in context |
| **Remediation** | The recommended fix pattern |

### The gl-sast-report.json Structure (Key Fields)

```json
{
  "vulnerabilities": [{
    "severity":    "Critical",
    "confidence":  "High",
    "location": {
      "file":       "app/vulnerable_endpoints.py",
      "start_line": 38,
      "method":     "find_robot"
    },
    "identifiers": [
      {"type": "cwe",  "value": "89"},
      {"type": "owasp","value": "A3:2021"}
    ],
    "description": "User-controlled data reaches SQL execution sink..."
  }]
}
```

---

## 4. Triage Workflow

Every SAST finding should be triaged — not left in "Detected" state indefinitely.

### Decision Tree

```
Finding detected
      ↓
Is this code actually reachable from user input?
  NO  → Low risk. Confirm in code review. Consider dismissing as "acceptable risk".
  YES ↓
Is user input sanitised before it reaches the dangerous call?
  YES → Investigate the sanitisation. If genuinely safe, dismiss as "False positive"
        with documented explanation.
  NO  ↓
Fix the vulnerability.
      ↓
Push the fix → re-run pipeline → verify finding resolved.
```

### GitLab Vulnerability States

| State | When to Use |
|---|---|
| **Detected** | Initial state — awaiting triage |
| **Confirmed** | Human verified: real vulnerability, not yet fixed |
| **Dismissed** | False positive or accepted risk — requires justification |
| **In Progress** | Fix is being developed |
| **Resolved** | Fixed — GitLab auto-sets when next clean scan runs |

### Dismissal Reasons

| Reason | When to Use |
|---|---|
| False positive | Scanner flagged something that is provably safe |
| Acceptable risk | Real vulnerability but risk is accepted (e.g., internal tool, temporary) |
| Used in tests | Only present in test code, not reachable in production |
| Not applicable | Finding is for a language feature not used in this context |

**Audit requirement:** Every dismissal is permanently logged — who, when, why.

---

## 5. Fixing Common SAST Findings

### Fix Pattern: SQL Injection (CWE-89)

```python
# ❌ VULNERABLE (SAST flags: string concatenation in db.execute())
query = "SELECT * FROM robots WHERE id = '" + robot_id + "'"
cursor.execute(query)

# ✅ FIXED (parameterised — user input is DATA, not SQL syntax)
cursor.execute("SELECT * FROM robots WHERE id = ?", (robot_id,))
```

### Fix Pattern: Hardcoded Credential (CWE-798)

```python
# ❌ VULNERABLE (SAST + Secret Detection flags: hardcoded string looks like key)
API_KEY = "sk-robovision-prod-xK9mN2pQ8rT4wV6y"

# ✅ FIXED (read from environment variable)
API_KEY = os.environ['ROBOT_API_KEY']  # Set in GitLab CI/CD Variables (masked)
```

### Fix Pattern: Command Injection (CWE-78)

```python
# ❌ VULNERABLE (SAST flags: shell=True with f-string)
subprocess.run(f"ping -c 2 {target}", shell=True)

# ✅ FIXED (list args, validated input, shell=False)
import re
if not re.match(r'^[a-zA-Z0-9.\-]{1,253}$', target):
    raise ValueError("Invalid target")
subprocess.run(["ping", "-c", "2", target], shell=False, timeout=5)
```

### Fix Pattern: MD5 for Passwords (CWE-327)

```python
# ❌ VULNERABLE (SAST flags: hashlib.md5 in password context)
password_hash = hashlib.md5(password.encode()).hexdigest()

# ✅ FIXED (bcrypt — designed for passwords, salted, slow by design)
import bcrypt
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

---

## 6. False Positives — Handling Them Correctly

### What Causes False Positives

SAST tools match patterns. Some patterns can be dangerous in one context but safe in another:

```python
# SAST flags: subprocess with shell=True
# Context 1 — DANGEROUS:
subprocess.run(f"ping {user_input}", shell=True)    # User controls command

# Context 2 — FALSE POSITIVE:
subprocess.run(["ping", "-c", "1", "8.8.8.8"], shell=True)  # Hardcoded, list args
# shell=True with a list is unusual but safe in this form
```

### Suppression Options

**Per-line suppression (use sparingly):**
```python
result = subprocess.run(["ping", "-c", "1", "8.8.8.8"], shell=True)  # nosemgrep
```

**Pipeline-level exclusion:**
```yaml
variables:
  SAST_EXCLUDED_PATHS: "spec, test, tests"    # Don't scan test directories
```

**Dashboard dismissal (preferred — auditable):**
Navigate to finding → Dismiss → Select reason → Add comment → Confirm.

### The False Positive Rate Matters

| False Positive Rate | Developer Behaviour |
|---|---|
| < 5% | Developers trust findings; act on them |
| 5–20% | Developers verify before acting |
| > 20% | Alert fatigue; findings ignored or scanner disabled |

---

## 7. SAST Limitations

SAST is powerful but has clear limits:

| What SAST Finds | What SAST Cannot Find |
|---|---|
| Known vulnerability patterns | Business logic flaws specific to your app |
| Dangerous function calls | Runtime-only vulnerabilities |
| Weak algorithms, missing controls | Vulnerabilities in external APIs |
| Hardcoded secrets | Misconfigurations in deployment environment |
| Tainted data reaching sinks | Race conditions, timing attacks |

**What complements SAST:**
- **DAST** — tests the running application; finds what SAST misses at runtime
- **SCA** — finds vulnerabilities in *dependencies*, not your code
- **Code review** — understands business logic; the human element
- **Penetration testing** — targeted, creative; finds complex multi-step attacks

---

## Lab Reference Card

```
Step 1: git checkout -b feature/sast-lab-demo
Step 2: Create app/vulnerable_endpoints.py (from lab workbook)
Step 3: Add to .gitlab-ci.yml:
          include:
            - template: Jobs/SAST.gitlab-ci.yml
Step 4: Commit and push
Step 5: Create MR → watch pipeline → semgrep-sast job runs
Step 6: Open MR → Security widget → expand findings
Step 7: Record: file, line, CWE, severity for each finding
Step 8: Fix SQL injection (parameterised queries)
Step 9: Fix hardcoded credentials (environment variables)
Step 10: Push fixes → pipeline re-runs → findings resolved
Step 11: Dismiss false positive with documented justification
```

---

## References

1. GitLab SAST — https://docs.gitlab.com/ee/user/application_security/sast/
2. GitLab SAST Analyzers — https://docs.gitlab.com/ee/user/application_security/sast/analyzers.html
3. GitLab SAST Variables — https://docs.gitlab.com/ee/user/application_security/sast/#available-cicd-variables
4. GitLab Vulnerability Report — https://docs.gitlab.com/ee/user/application_security/vulnerability_report/
5. Semgrep Rules — https://semgrep.dev/explore
6. GitLab Security Report Schema — https://gitlab.com/gitlab-org/security-products/security-report-schemas
