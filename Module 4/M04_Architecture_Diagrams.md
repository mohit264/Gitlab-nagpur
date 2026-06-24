# ARCHITECTURE DIAGRAMS — MODULE 4
## Source Control and Governance
### Render at https://mermaid.live

---

## Diagram 1: Monorepo vs Polyrepo Trade-off

```mermaid
graph TB
    subgraph MONO ["✅ Monorepo — Single Repository"]
        direction LR
        MR[robovision-platform/]
        MR --> MA[src/api/]
        MR --> MF[firmware/]
        MR --> MC[src/auth/]
        MR --> MT[terraform/]
        MR --> MCI[.gitlab-ci.yml]

        MONO_PRO["Pros:\n+ Atomic cross-service changes\n+ Unified versioning\n+ Single pipeline\n+ One CODEOWNERS"]
        MONO_CON["Cons:\n- Slow full-pipeline\n- Large clone size\n- Merge conflicts at scale\n- Coarse RBAC"]
    end

    subgraph POLY ["Polyrepo — Multiple Repositories"]
        direction LR
        PR1[robovision-api/]
        PR2[robovision-firmware/]
        PR3[robovision-infra/]
        PR4[robovision-auth/]

        POLY_PRO["Pros:\n+ Team autonomy\n+ Fine-grained RBAC\n+ Fast CI per service"]
        POLY_CON["Cons:\n- Cross-service MRs needed\n- Dependency drift\n- Security policy overhead\n- No atomic changes"]
    end

    style MONO fill:#eafaf1,stroke:#2ecc71
    style POLY fill:#fef9e7,stroke:#f39c12
```

---

## Diagram 2: Trunk-Based Development vs Git Flow

```mermaid
gitGraph
   commit id: "Initial"
   commit id: "Feature A (direct — TBD style)"
   branch feature/b
   checkout feature/b
   commit id: "Feature B day 1"
   commit id: "Feature B day 2"
   checkout main
   merge feature/b id: "Merge Feature B (< 3 days)" tag: "MR #2"
   commit id: "Hotfix"
   branch feature/c
   checkout feature/c
   commit id: "Feature C"
   checkout main
   merge feature/c id: "Merge Feature C" tag: "MR #3"
   commit id: "Release v1.2" tag: "v1.2.0"
```

---

## Diagram 3: GitLab Merge Request — Internal Governance Flow

```mermaid
sequenceDiagram
    participant DEV as Developer
    participant GL as GitLab
    participant CI as CI Pipeline
    participant CO as CODEOWNERS Engine
    participant REV as Code Reviewer
    participant AUDIT as Audit Log

    DEV->>GL: git push feature/auth-update
    GL->>DEV: Prompt: Create Merge Request
    DEV->>GL: Create MR (source: feature, target: main)
    GL->>AUDIT: Log: MR created by @developer
    GL->>CI: Trigger pipeline automatically
    GL->>CO: Parse CODEOWNERS for modified paths
    CO-->>GL: /src/auth/ → requires @security-team
    GL->>REV: Add @security-team as required approver
    GL->>AUDIT: Log: Required approvers set

    CI-->>GL: Pipeline result (pass/fail)
    GL->>AUDIT: Log: Pipeline #123 completed

    REV->>GL: Review code — leave comment
    GL->>AUDIT: Log: Comment by @reviewer
    DEV->>GL: Push fix commit
    GL->>GL: Remove existing approvals (policy: approvals reset on new commit)
    GL->>AUDIT: Log: Approvals reset — new commit added
    GL->>CI: Re-trigger pipeline

    CI-->>GL: Pipeline passed
    REV->>GL: Approve MR
    GL->>AUDIT: Log: Approved by @reviewer (Security Review)

    GL->>GL: Check: all conditions met?
    Note over GL: ✅ Pipeline passed\n✅ All threads resolved\n✅ CODEOWNERS approved\n✅ Author not self-approved

    DEV->>GL: Click Merge
    GL->>GL: Fast-forward or merge commit to main
    GL->>AUDIT: Log: MR merged by @developer, approved by @reviewer
```

---

## Diagram 4: Governance Control Stack

```mermaid
graph TB
    subgraph GOVERNANCE ["GitLab Governance Control Stack"]
        direction TB
        
        L7["🔒 Audit Layer\nAudit Events — immutable log of all platform actions\nWho did what, when, from where"]
        
        L6["📋 Process Layer\nMR Templates — security review checklist\nForces reviewers to consider security implications"]
        
        L5["🔬 CI Gate\nPipelines must succeed before merge\nSecurity scans block merge on new vulnerabilities (Ultimate)"]
        
        L4["👥 MR Approval Layer\nApproval rules — N approvals required\nAuthor cannot self-approve\nApprovals reset on new commit"]
        
        L3["📂 CODEOWNERS Layer\nFile-level ownership\nSecurity-critical paths require owner review\nSections: separate approval gates per domain"]
        
        L2["🌿 Branch Protection Layer\nNo direct push to main\nForce push prevented\nCode owner approval required on merge"]
        
        L1["🔑 RBAC Layer\nRepository access control\nRole-based (Guest/Reporter/Developer/Maintainer/Owner)"]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7

    style L7 fill:#1a5276,color:#fff
    style L6 fill:#154360,color:#fff
    style L5 fill:#e74c3c,color:#fff
    style L4 fill:#922b21,color:#fff
    style L3 fill:#784212,color:#fff
    style L2 fill:#7d6608,color:#fff
    style L1 fill:#1e8449,color:#fff
```

---

## Diagram 5: CODEOWNERS — How It Works

```mermaid
graph LR
    subgraph MR_TRIGGER ["MR Created: modifies /src/auth/login.py and /firmware/safety/limits.h"]
        direction TB
        PUSH[Developer pushes to feature branch]
        MR[Opens Merge Request]
        PUSH --> MR
    end

    subgraph CO_ENGINE ["CODEOWNERS Engine"]
        direction TB
        PARSE[Parse .gitlab/CODEOWNERS]
        MATCH1["Match: /src/auth/ → @security-team"]
        MATCH2["Match: /firmware/safety/ → @safety-engineers"]
        PARSE --> MATCH1
        PARSE --> MATCH2
    end

    subgraph APPROVALS ["MR Approval Requirements (auto-populated)"]
        direction TB
        SEC_GATE["[Security Review] section\nRequired: @security-team\nStatus: ⏳ Pending"]
        SAF_GATE["[Safety Critical Review] section\nRequired: @safety-engineers\nStatus: ⏳ Pending"]
    end

    MR --> CO_ENGINE
    MATCH1 --> SEC_GATE
    MATCH2 --> SAF_GATE

    SEC_GATE -->|approved| MERGE_CHECK["Merge eligibility check"]
    SAF_GATE -->|approved| MERGE_CHECK
    MERGE_CHECK -->|all approved + CI pass| MERGE[Merge permitted]
    MERGE_CHECK -->|any pending| BLOCK[Merge blocked]

    style SEC_GATE fill:#e74c3c,color:#fff
    style SAF_GATE fill:#e74c3c,color:#fff
    style MERGE fill:#2ecc71,color:#000
    style BLOCK fill:#c0392b,color:#fff
```

---

## Diagram 6: Protected Branch Flow

```mermaid
stateDiagram-v2
    [*] --> CodeOnFeatureBranch : Developer creates feature branch

    CodeOnFeatureBranch --> OpenMR : git push + Create MR
    
    OpenMR --> PipelineRunning : CI triggers automatically

    PipelineRunning --> PipelinePassed : All jobs succeed
    PipelineRunning --> PipelineFailed : Any job fails

    PipelineFailed --> FixCode : Developer fixes issue
    FixCode --> PipelineRunning : Pushes fix commit (approvals reset)

    PipelinePassed --> WaitingApprovals : Meets CI requirement

    WaitingApprovals --> AllApproved : Required approvers approve
    WaitingApprovals --> ReviewComment : Reviewer requests changes
    ReviewComment --> FixCode : Developer addresses comments

    AllApproved --> MergeEligible : All conditions met

    MergeEligible --> Merged : Maintainer clicks Merge
    Merged --> [*] : Source branch deleted; audit trail complete

    note right of MergeEligible
        Conditions checked:
        ✅ Pipeline passed
        ✅ All threads resolved
        ✅ CODEOWNERS sections approved
        ✅ Approval rules satisfied
        ✅ Author did not self-approve
    end note
```

---

## Diagram 7: Compliance Audit Trail — What GitLab Records

```mermaid
graph LR
    subgraph EVENTS ["Events Recorded in GitLab Audit Log"]
        E1["🔵 MR Created\nActor: developer\nTimestamp: T+0"]
        E2["🟡 Pipeline Started\nPipeline: #123\nTimestamp: T+1min"]
        E3["🟢 Pipeline Passed\nJobs: build, test, sast\nTimestamp: T+8min"]
        E4["💬 Review Comment\nActor: reviewer\nTimestamp: T+15min"]
        E5["🔄 New Commit\nApprovals Reset\nTimestamp: T+20min"]
        E6["🟢 Re-Pipeline Passed\nTimestamp: T+28min"]
        E7["✅ MR Approved\nActor: reviewer\nSection: Security\nTimestamp: T+30min"]
        E8["✅ MR Approved\nActor: safety-eng\nSection: Safety\nTimestamp: T+35min"]
        E9["🔀 MR Merged\nActor: developer\nTarget: main\nTimestamp: T+36min"]
    end

    E1 --> E2 --> E3 --> E4 --> E5 --> E6 --> E7 --> E8 --> E9

    subgraph COMPLIANCE ["Compliance Evidence"]
        C1["SOC 2: Change was reviewed\n(E4, E7, E8)"]
        C2["PCI DSS: Only approved changes deployed\n(E7, E8, E9)"]
        C3["ISO 26262: Traceability\n(E1→E9 chain)"]
    end

    E9 --> C1
    E9 --> C2
    E9 --> C3

    style C1 fill:#2ecc71,color:#000
    style C2 fill:#2ecc71,color:#000
    style C3 fill:#2ecc71,color:#000
```

---

## Diagram 8: Branching Strategy for IoT/Firmware Teams

```mermaid
gitGraph
   commit id: "v1.0.0 — firmware baseline" tag: "v1.0.0"
   
   branch feature/ota-v2-protocol
   checkout feature/ota-v2-protocol
   commit id: "OTA protocol update"
   commit id: "Security hardening"
   
   checkout main
   branch hotfix/CVE-2024-safety-fix
   checkout hotfix/CVE-2024-safety-fix
   commit id: "Emergency safety limit fix" tag: "v1.0.1-hotfix"
   
   checkout main
   merge hotfix/CVE-2024-safety-fix id: "Hotfix merged" tag: "v1.0.1"
   
   merge feature/ota-v2-protocol id: "OTA v2 merged (MR #47)" tag: "v1.1.0"
   
   commit id: "Release candidate" tag: "v1.1.0-rc1"
   commit id: "v1.1.0 production release" tag: "v1.1.0-prod"
```

---

## Usage Notes

- Diagram 3 (MR Governance Flow) is the primary teaching diagram — walk through in detail
- Diagram 4 (Governance Stack) use as a summary after covering all sections
- Diagram 5 (CODEOWNERS mechanics) draw on whiteboard first, then show diagram
- Diagram 7 (Compliance audit trail) use when discussing SOC 2 / PCI DSS in business context
- Diagram 8 (IoT branching) specific to IoT/firmware audience in Module 15 discussion
