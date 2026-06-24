# ARCHITECTURE DIAGRAMS — MODULE 7
## Secure SDLC and DevSecOps
### Render at https://mermaid.live

---

## Diagram 1: Security Scan Placement in CI/CD Pipeline

```mermaid
graph LR
    COMMIT["git commit\n+ push"] --> MR["Merge\nRequest\nOpened"]

    subgraph COMMIT_STAGE ["Commit-time Scans (seconds)"]
        S1["🔍 SAST\nSource code analysis\nSemgrep"]
        S2["🔑 Secret Detection\nCredentials in code\nGitleaks"]
        S3["🏗️ IaC Scanning\nTerraform/K8s\nKICS"]
    end

    subgraph BUILD_STAGE ["Build-time Scans (seconds–minutes)"]
        S4["📦 Dependency Scanning\nKnown CVEs in deps\nTrivy/Gemnasium"]
        S5["🐳 Container Scanning\nDocker image CVEs\nTrivy"]
        S6["⚖️ License Compliance\nOpen source licence risk"]
    end

    subgraph RUNTIME_STAGE ["Runtime Scans (minutes)"]
        S7["🌐 DAST\nRunning app black-box\nOWASP ZAP"]
    end

    MR --> COMMIT_STAGE
    COMMIT_STAGE --> BUILD_STAGE
    BUILD_STAGE --> RUNTIME_STAGE

    COMMIT_STAGE -->|"Findings in\nMR widget"| DEV["👨‍💻 Developer\nImmediate feedback"]
    BUILD_STAGE -->|"Findings in\nSecurity Dashboard"| DEV
    RUNTIME_STAGE -->|"Findings in\nMR + Dashboard"| DEV

    style COMMIT_STAGE fill:#2ecc71,color:#000
    style BUILD_STAGE fill:#3498db,color:#fff
    style RUNTIME_STAGE fill:#9b59b6,color:#fff
    style DEV fill:#e67e22,color:#fff
```

---

## Diagram 2: GitLab Security Architecture — How Findings Reach the Dashboard

```mermaid
sequenceDiagram
    participant RUNNER as GitLab Runner
    participant SCANNER as Scanner Container\n(Semgrep/Trivy/ZAP)
    participant OBJ as Object Storage
    participant SIDEKIQ as Sidekiq\n(background jobs)
    participant PG as PostgreSQL\n(vulnerability records)
    participant UI as Developer\n(MR / Dashboard)

    RUNNER->>SCANNER: Start scanner container\nMount source code
    SCANNER->>SCANNER: Analyse code / image / running app
    SCANNER-->>RUNNER: Output: gl-sast-report.json\n(standard schema)
    RUNNER->>OBJ: Upload artifact (reports: sast:)
    RUNNER->>SIDEKIQ: Notify: security report artifact ready

    SIDEKIQ->>OBJ: Download gl-sast-report.json
    SIDEKIQ->>SIDEKIQ: Parse findings\nDeduplicate against existing
    SIDEKIQ->>PG: INSERT vulnerability records\n(file, line, severity, CWE, description)

    UI->>PG: Query: vulnerabilities for this pipeline/MR
    PG-->>UI: Vulnerability records
    UI-->>UI: Render MR security widget\n+ Security Dashboard
```

---

## Diagram 3: OWASP SAMM — GitLab Coverage Map

```mermaid
graph TB
    subgraph SAMM ["OWASP SAMM v2.0 — GitLab Ultimate Coverage"]
        direction TB

        subgraph GOV ["GOVERNANCE"]
            G1["Strategy & Metrics\n❌ Requires org process"]
            G2["Policy & Compliance\n✅ Compliance Frameworks\n✅ Audit Events"]
            G3["Education & Guidance\n⚠️ Partial — MR templates\nsecurity guidelines"]
        end

        subgraph DESIGN ["DESIGN"]
            D1["Threat Assessment\n⚠️ Partial — STRIDE discussion\nrequires external tool"]
            D2["Security Requirements\n⚠️ Partial — via MR template"]
            D3["Security Architecture\n⚠️ Partial — CODEOWNERS\nfor security files"]
        end

        subgraph IMPL ["IMPLEMENT"]
            I1["Secure Build\n✅ SAST, SCA, Secret Detection\nContainer Scan, IaC Scan"]
            I2["Secure Deployment\n✅ Protected Environments\nApproval Gates"]
            I3["Defect Management\n✅ Vulnerability Management\nIssue creation"]
        end

        subgraph VERIFY ["VERIFY"]
            V1["Architecture Review\n✅ MR + Approval Rules\nCODEOWNERS"]
            V2["Requirements Testing\n✅ DAST"]
            V3["Security Testing\n✅ Security Dashboard\nAll scan results"]
        end

        subgraph OPS ["OPERATIONS"]
            O1["Incident Management\n⚠️ Partial — Audit Events\nExternal SIEM needed"]
            O2["Environment Management\n✅ Protected Environments\nEnvironment tracking"]
            O3["External Communications\n❌ Requires external process"]
        end
    end

    style I1 fill:#2ecc71,color:#000
    style I2 fill:#2ecc71,color:#000
    style I3 fill:#2ecc71,color:#000
    style G2 fill:#2ecc71,color:#000
    style V1 fill:#2ecc71,color:#000
    style V2 fill:#2ecc71,color:#000
    style V3 fill:#2ecc71,color:#000
    style O2 fill:#2ecc71,color:#000
    style D1 fill:#f39c12,color:#fff
    style D2 fill:#f39c12,color:#fff
    style D3 fill:#f39c12,color:#fff
    style G3 fill:#f39c12,color:#fff
    style O1 fill:#f39c12,color:#fff
    style G1 fill:#e74c3c,color:#fff
    style O3 fill:#e74c3c,color:#fff
```

---

## Diagram 4: NIST SSDF Practice Groups and GitLab Mapping

```mermaid
graph LR
    subgraph PO ["PO — Prepare Organisation"]
        PO3["PO.3 Secure tooling\n→ Docker executor isolation\nRunner security"]
        PO5["PO.5 Secure environments\n→ Protected branches\nProject RBAC"]
    end

    subgraph PS ["PS — Protect Software"]
        PS1["PS.1 Protect source code\n→ Branch protection\nCODEOWNERS\nAudit trail"]
        PS2["PS.2 Protect components\n→ Signed artifacts\nPackage Registry\nContainer Registry"]
    end

    subgraph PW ["PW — Produce Well-Secured Software"]
        PW5["PW.5 Secure coding\n→ SAST\nSecret Detection\nin MR pipeline"]
        PW7["PW.7 Code review\n→ MR + Approval Rules\nFour-eyes principle"]
        PW8["PW.8 Test vulnerabilities\n→ DAST, SCA\nContainer Scanning"]
    end

    subgraph RV ["RV — Respond to Vulnerabilities"]
        RV1["RV.1 Identify vulnerabilities\n→ Security Dashboard\nVulnerability Report"]
        RV2["RV.2 Assess + remediate\n→ Vulnerability Management\nSeverity triage\nIssue creation"]
        RV3["RV.3 Root cause analysis\n→ Linked to commit\nMR history"]
    end

    PO --> PS --> PW --> RV

    style PO fill:#3498db,color:#fff
    style PS fill:#9b59b6,color:#fff
    style PW fill:#2ecc71,color:#000
    style RV fill:#e67e22,color:#fff
```

---

## Diagram 5: Vulnerability Lifecycle in GitLab

```mermaid
stateDiagram-v2
    [*] --> Detected : Scanner finds vulnerability\nin CI/CD pipeline

    Detected --> Confirmed : Security team reviews\n— confirms real issue
    Detected --> Dismissed : Security team reviews\n— false positive or\naccepted risk\n(requires justification)

    Confirmed --> InProgress : Developer assigned\nto fix
    Confirmed --> Dismissed : Risk accepted\nwith documented reason

    InProgress --> Resolved : Next pipeline scan\nno longer detects it\n(automatic state change)
    InProgress --> Confirmed : Fix reverted\nor incomplete

    Resolved --> [*] : Vulnerability addressed

    Dismissed --> [*] : Risk accepted\nAudit record created

    note right of Dismissed
        Dismissal requires:
        • Reason selection
        • User attribution
        • Timestamp
        All stored in audit log
    end note

    note right of Resolved
        Automatic — GitLab
        detects absence in
        next clean scan
    end note
```

---

## Diagram 6: Security Gate — Warn vs. Block Decision Flow

```mermaid
flowchart TD
    PUSH["Developer pushes code\nto feature branch"] --> SCAN["Security scan runs\nin CI/CD pipeline"]

    SCAN --> FINDINGS{Findings\ndetected?}

    FINDINGS -->|No findings| PASS["✅ Pipeline passes\nMR can be merged"]
    FINDINGS -->|Findings detected| SEVERITY{Severity\nlevel?}

    SEVERITY -->|Info / Low| WARN["⚠️ Warning only\nFindings visible in MR\nPipeline still passes\nDeveloper informed"]

    SEVERITY -->|Medium| MEDIUM_CHECK{Security Policy\nconfigured for medium?}
    MEDIUM_CHECK -->|No policy| WARN
    MEDIUM_CHECK -->|Policy active| GATE

    SEVERITY -->|High / Critical| GATE["🔴 Gate triggered\nPipeline FAILS\nor MR requires\nsecurity team approval"]

    GATE --> POLICY_CHECK{Vulnerability\nstate?}
    POLICY_CHECK -->|Newly detected| BLOCK["❌ MR blocked\nCannot merge without:\n• Security team approval\n• OR fixing the vulnerability"]
    POLICY_CHECK -->|Pre-existing\n(historical)| WARN

    WARN --> MERGE_OK["Developer can merge\nFinding tracked in\nVulnerability Dashboard"]
    BLOCK --> FIX["Developer fixes vulnerability\nor security team approves exception"]
    FIX --> RESCAN["Re-run pipeline\nVerify fix"]
    RESCAN -->|Fixed| PASS
    RESCAN -->|Still present| GATE

    style PASS fill:#2ecc71,color:#000
    style WARN fill:#f39c12,color:#fff
    style BLOCK fill:#e74c3c,color:#fff
    style GATE fill:#e74c3c,color:#fff
```

---

## Diagram 7: Shift Left Cost Model

```mermaid
xychart-beta
    title "Cost to Fix Vulnerability by Discovery Phase"
    x-axis ["Design\n(STRIDE)", "SAST\n(Commit)", "DAST\n(QA)", "Pen Test\n(Pre-release)", "Production\n(Post-breach)"]
    y-axis "Relative Fix Cost (×)" 0 --> 110
    bar [1, 6, 15, 50, 100]
```

---

## Diagram 8: DevSecOps Maturity Adoption Roadmap

```mermaid
gantt
    title DevSecOps Adoption Roadmap (12 months)
    dateFormat  YYYY-MM
    section Month 1-2 Foundation
    SAST warn-only          :2024-01, 2M
    Secret Detection warn   :2024-01, 2M
    Fix critical SAST findings :2024-02, 1M

    section Month 3-4 Blocking Gates
    SAST blocking (new critical) :2024-03, 2M
    Secret Detection blocking    :2024-03, 2M
    Add Dependency Scanning warn :2024-03, 1M

    section Month 4-6 Supply Chain
    Fix critical CVEs in deps    :2024-04, 2M
    SCA blocking CVSS 9+         :2024-06, 1M
    Container Scanning warn      :2024-05, 1M

    section Month 6-9 Infrastructure
    IaC Scanning enabled         :2024-06, 1M
    Container Scanning blocking  :2024-07, 2M
    DAST in QA pipeline          :2024-07, 3M

    section Month 9-12 Full Governance
    Security Policies defined    :2024-09, 1M
    Compliance Frameworks        :2024-10, 2M
    SBOM generation              :2024-10, 1M
    Full policy enforcement      :2024-11, 2M
```

---

## Diagram 9: STRIDE Threat Model for RoboVision (Whiteboard Reference)

```mermaid
graph TB
    subgraph SYSTEM ["RoboVision System Boundary"]
        RC["Robot Controller\n(firmware)"]
        VP["Vision Processing\nService"]
        TM["Telemetry\nService"]
        EG["Edge Gateway"]
        DM["Device Management\nAPI"]
        OTA["OTA Update\nChannel"]
    end

    subgraph THREATS ["STRIDE Threats"]
        S_T["S — Spoofing\nFake robot identity\nFake command source"]
        T_T["T — Tampering\nModify OTA firmware\nAlter telemetry data"]
        R_T["R — Repudiation\nDeny command sent\nNo audit log on device"]
        I_T["I — Info Disclosure\nTelemetry exposes position\nNetwork traffic unencrypted"]
        D_T["D — Denial of Service\nFlood command API\nBlock safety-stop"]
        E_T["E — Elevation of Privilege\nUnauthenticated admin\nBSP debug port open"]
    end

    OTA --> T_T
    EG --> S_T
    RC --> R_T
    TM --> I_T
    DM --> D_T
    RC --> E_T

    style S_T fill:#e74c3c,color:#fff
    style T_T fill:#e74c3c,color:#fff
    style R_T fill:#f39c12,color:#fff
    style I_T fill:#f39c12,color:#fff
    style D_T fill:#e74c3c,color:#fff
    style E_T fill:#e74c3c,color:#fff
```
