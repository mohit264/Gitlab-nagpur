# ARCHITECTURE DIAGRAMS — MODULE 10
## Static Application Security Testing (SAST)
### Render at https://mermaid.live

---

## Diagram 1: SAST Internal Analysis Pipeline

```mermaid
graph TB
    subgraph INPUT ["Input: Source Code"]
        PY["app/vulnerable_endpoints.py\n(Python source)"]
        JS["frontend/app.js\n(JavaScript source)"]
        C["firmware/controller.c\n(C source)"]
    end

    subgraph ANALYSIS ["SAST Analysis Engine (Semgrep)"]
        direction TB
        LEX["Lexer\nTokenises source into\nkeywords, identifiers, literals"]
        PARSE["Parser\nBuilds Abstract Syntax Tree (AST)\nfrom token stream"]
        RULES["Rule Engine\nApplies security rules\nto AST node patterns"]
        TAINT["Taint Analysis\nTracks data flow:\nsource → sanitiser? → sink"]
        
        LEX --> PARSE --> RULES
        PARSE --> TAINT
    end

    subgraph OUTPUT ["Output: Findings"]
        REPORT["gl-sast-report.json\n{file, line, CWE, severity,\nsnippet, remediation}"]
    end

    PY --> LEX
    JS --> LEX
    C --> LEX
    RULES --> REPORT
    TAINT --> REPORT

    style INPUT fill:#3498db,color:#fff
    style ANALYSIS fill:#2ecc71,color:#000
    style OUTPUT fill:#e67e22,color:#fff
```

---

## Diagram 2: Taint Analysis — SQL Injection Detection

```mermaid
graph LR
    subgraph TAINT_FLOW ["Taint Flow Trace"]
        SOURCE["SOURCE\nrobot_id =\nrequest.args.get('robot_id')\n\n⚠️ User-controlled\nData marked as TAINTED"]

        ASSIGN["ASSIGNMENT\nquery = 'SELECT ... WHERE id='\n         + robot_id + \"'\"\n\n⚠️ Taint PROPAGATES\ninto query variable"]

        SANITISER_CHECK{"Sanitiser\npresent?"}

        SINK["SINK\nconn.execute(query)\n\n❌ TAINTED data reaches\nSQL execution — CWE-89"]

        SAFE_SINK["SAFE SINK\nconn.execute(\n  'SELECT ... WHERE id=?',\n  (robot_id,)\n)\n✅ Parameterised —\ntaint cannot alter SQL"]
    end

    SOURCE -->|"taint propagates"| ASSIGN
    ASSIGN --> SANITISER_CHECK
    SANITISER_CHECK -->|"NO sanitiser"| SINK
    SANITISER_CHECK -->|"Sanitiser found\n(parameterised query)"| SAFE_SINK

    style SOURCE fill:#e74c3c,color:#fff
    style ASSIGN fill:#e67e22,color:#fff
    style SINK fill:#c0392b,color:#fff
    style SAFE_SINK fill:#2ecc71,color:#000
    style SANITISER_CHECK fill:#3498db,color:#fff
```

---

## Diagram 3: GitLab SAST — From include: to MR Widget

```mermaid
sequenceDiagram
    participant DEV as Developer
    participant GL as GitLab
    participant RUNNER as GitLab Runner
    participant SEMGREP as Semgrep Container
    participant OBJ as Object Storage
    participant SIDEKIQ as Sidekiq
    participant PG as PostgreSQL
    participant MR as MR Security Widget

    DEV->>GL: git push feature/sast-lab-demo
    DEV->>GL: Create Merge Request
    GL->>RUNNER: Trigger pipeline (MR pipeline source)

    Note over RUNNER,SEMGREP: SAST stage — auto-injected by template
    RUNNER->>SEMGREP: Pull registry.gitlab.com/security-products/semgrep:latest
    RUNNER->>SEMGREP: Mount source code, start analysis
    SEMGREP->>SEMGREP: Lexer → Parser → AST → Rule engine
    SEMGREP->>SEMGREP: Taint analysis
    SEMGREP-->>RUNNER: gl-sast-report.json (7 findings)

    RUNNER->>OBJ: Upload artifact: gl-sast-report.json
    RUNNER->>GL: Job complete — SUCCESS

    GL->>SIDEKIQ: Enqueue: parse security report artifact
    SIDEKIQ->>OBJ: Download gl-sast-report.json
    SIDEKIQ->>SIDEKIQ: Parse findings, deduplicate
    SIDEKIQ->>PG: INSERT 7 vulnerability records

    DEV->>MR: Open Merge Request in browser
    MR->>PG: Query vulnerabilities for this pipeline
    MR-->>DEV: Security widget: "7 findings (Critical: 2, High: 2, Medium: 2, Low: 1)"
```

---

## Diagram 4: SAST Finding Anatomy

```mermaid
graph TB
    subgraph FINDING ["SAST Finding — CWE-89 SQL Injection"]
        META["METADATA\nID: f3a9d1c2...\nCategory: sast\nScanner: Semgrep"]
        SEV["SEVERITY BLOCK\nSeverity: Critical\nConfidence: High"]
        LOC["LOCATION\nFile: app/vulnerable_endpoints.py\nLine: 38\nMethod: find_robot"]
        CODE["CODE SNIPPET\n'SELECT ... WHERE id = '\n+ robot_id + \"'\""]
        IDS["IDENTIFIERS\nCWE: CWE-89\nOWASP: A3:2021 — Injection\nSemgrep Rule ID: formatted-sql-query"]
        REM["REMEDIATION\ncursor.execute(\n  'SELECT ... WHERE id = ?',\n  (robot_id,)\n)"]
        LINKS["REFERENCES\nhttps://cwe.mitre.org/89\nhttps://owasp.org/Top10/A03"]
    end

    META --> SEV --> LOC --> CODE --> IDS --> REM --> LINKS

    style SEV fill:#e74c3c,color:#fff
    style IDS fill:#3498db,color:#fff
    style REM fill:#2ecc71,color:#000
```

---

## Diagram 5: SAST Finding Triage Decision Flow

```mermaid
flowchart TD
    FOUND["SAST Finding Detected\nSeverity: Critical\nCWE-89 SQL Injection\napp/main.py line 47"]

    Q1{"Is this code reachable\nfrom user input in\nproduction?"}

    Q2{"Is there a sanitiser\nbetween source and sink?\n(parameterised query,\n ORM, allowlist)"}

    Q3{"Is the sanitiser\neffective for this\nvulnerability class?"}

    FP_DISMISS["DISMISS: False Positive\nDocument: 'Sanitised by X\nbefore reaching execute()'\nAudit trail created ✅"]

    RISK_ACCEPT["DISMISS: Acceptable Risk\nDocument: 'Internal tool only,\nnot internet-exposed'\nAudit trail created ✅"]

    FIX["FIX: Use parameterised query\ncursor.execute('... WHERE id=?', (id,))\nPush fix → Re-run pipeline\nVerify finding resolved ✅"]

    RESCAN{"Re-scan:\nfinding still\npresent?"}

    RESOLVED["RESOLVED ✅\nFinding auto-resolved\nby GitLab on clean scan"]

    Q1 -->|"No — test/internal only"| RISK_ACCEPT
    Q1 -->|"Yes"| Q2
    Q2 -->|"Yes"| Q3
    Q2 -->|"No"| FIX
    Q3 -->|"Yes — genuinely safe"| FP_DISMISS
    Q3 -->|"No — sanitiser insufficient"| FIX
    FIX --> RESCAN
    RESCAN -->|"No — fixed"| RESOLVED
    RESCAN -->|"Yes — fix incomplete"| FIX

    style FIX fill:#e74c3c,color:#fff
    style RESOLVED fill:#2ecc71,color:#000
    style FP_DISMISS fill:#3498db,color:#fff
    style RISK_ACCEPT fill:#f39c12,color:#fff
```

---

## Diagram 6: Before and After SAST — Developer Feedback Loop

```mermaid
graph LR
    subgraph BEFORE ["❌ Before SAST — Quarterly Pen Test"]
        B1["Developer writes\nvulnerable code"]
        B2["Code merged\nto main"]
        B3["Deployed to\nproduction"]
        B4["Quarterly pen test\n(3 months later)"]
        B5["PDF report delivered\n(developer on new project)"]
        B6["COST: 100×\nTime: 3 months\nContext: lost"]
        B1 --> B2 --> B3 --> B4 --> B5 --> B6
    end

    subgraph AFTER ["✅ After SAST — Commit-time Feedback"]
        A1["Developer writes\nvulnerable code"]
        A2["git push →\nSAST runs (60s)"]
        A3["Finding in MR widget:\nfile, line, CWE, fix"]
        A4["Developer fixes\n(still has full context)"]
        A5["Re-scan confirms\nfix — merge approved"]
        A6["COST: 6×\nTime: minutes\nContext: full"]
        A1 --> A2 --> A3 --> A4 --> A5 --> A6
    end

    style BEFORE fill:#fdecea,stroke:#e74c3c
    style AFTER fill:#eafaf1,stroke:#2ecc71
    style B6 fill:#e74c3c,color:#fff
    style A6 fill:#2ecc71,color:#000
```

---

## Diagram 7: SAST Coverage Gap — What Complements It

```mermaid
graph TB
    subgraph SAST_COVERS ["✅ SAST Detects"]
        SC1["SQL/Command/Path Injection patterns"]
        SC2["Weak cryptographic algorithms"]
        SC3["Hardcoded credentials (with Secret Detection)"]
        SC4["Missing auth decorators"]
        SC5["Unsafe deserialization"]
        SC6["Buffer overflow patterns (C/C++)"]
    end

    subgraph SAST_MISSES ["❌ SAST Cannot Detect"]
        SM1["Business logic flaws\n(your domain-specific rules)"]
        SM2["Runtime-only vulnerabilities\n(race conditions, timing attacks)"]
        SM3["Vulnerabilities in dependencies\n(→ SCA fills this gap)"]
        SM4["Infrastructure misconfigurations\n(→ IaC Scanning fills this)"]
        SM5["Deployed container vulnerabilities\n(→ Container Scanning fills this)"]
        SM6["Dynamic/runtime attack vectors\n(→ DAST fills this)"]
    end

    SAST["GitLab SAST\n(Semgrep)"]

    SAST --> SAST_COVERS
    SAST -.->|"not covered\n→ use other scanners"| SAST_MISSES

    style SAST fill:#fc6d26,color:#fff
    style SAST_COVERS fill:#eafaf1,stroke:#2ecc71
    style SAST_MISSES fill:#fdecea,stroke:#e74c3c
```
