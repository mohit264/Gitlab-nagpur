# STUDENT HANDBOOK — MODULE 2
## GitLab Ultimate Overview: The Single Application Platform

---

**Workshop:** GitLab Ultimate for Secure SDLC, DevSecOps, AI, Robotics & IoT  
**Day:** 1 of 2 | **Module:** 2 of 16 | **Duration:** 60 minutes

---

## Learning Objectives

- Describe GitLab's architecture as a single-application platform
- Differentiate GitLab Free, Premium, and Ultimate tiers (security focus)
- Understand why organisations consolidate multi-tool toolchains
- Identify core GitLab components and their roles
- Explain the three GitLab deployment models

---

## 1. GitLab — Company and Platform Context

GitLab was founded in 2011 by Dmitriy Zaporozhets and Sytse "Sid" Sijbrandij. It is built as **open-core** — the core platform (SCM, basic CI/CD) is open source (MIT); enterprise features are proprietary.

**Scale (2024):**
- ~30 million registered users
- Used by more than 50% of Fortune 100 companies
- GitLab's own source code is publicly visible at gitlab.com/gitlab-org/gitlab

**Three Deployment Models:**

| Model | Description | Best For |
|---|---|---|
| GitLab.com (SaaS) | Hosted by GitLab Inc., multi-tenant | Fast adoption, no infra overhead |
| GitLab Self-Managed | Your infrastructure | Air-gapped, data residency, max control |
| GitLab Dedicated | Single-tenant SaaS by GitLab | Compliance + managed operations |

*Source: https://about.gitlab.com/install/*

---

## 2. The Single Application Concept

**The Problem It Solves:**

A typical enterprise software delivery toolchain in 2024:

```
GitHub            → Source Control
Jenkins           → CI/CD Pipelines
SonarQube         → SAST
Snyk              → Dependency Scanning
JFrog Artifactory → Artifact Registry
HashiCorp Vault   → Secrets Management
ArgoCD            → GitOps Deployment
Jira              → Issue Tracking
Confluence        → Documentation
Checkmarx         → Advanced SAST
Datadog           → Monitoring
```

**The Integration Tax:**
Each integration requires:
- Separate authentication and user provisioning
- Webhook maintenance (breaks on API version updates)
- Custom audit log aggregation
- Separate failure monitoring

**GitLab's Architectural Claim:**

> "GitLab is a single application for the entire software development lifecycle."
> — https://about.gitlab.com/platform/

**What "Single Application" Means Mechanically:**

| Property | Fragmented Toolchain | GitLab Single Application |
|---|---|---|
| Authentication | 8-15 separate RBAC systems | One RBAC system |
| Audit Trail | Aggregation required from 8+ sources | One audit log, one query |
| Data Correlation | Custom integration per tool pair | Native correlation in one database |
| API | 8-15 separate versioned APIs | One unified API |
| Policy Enforcement | Implemented separately in each tool | One policy engine |
| Security Dashboard | Manual aggregation | Built-in, real-time |

---

## 3. GitLab Tier Comparison — Security Focus

GitLab has three commercial tiers. This workshop operates at **Ultimate tier** because all advanced DevSecOps capabilities are Ultimate features.

| Capability | Free | Premium | Ultimate |
|---|:---:|:---:|:---:|
| Git SCM | ✅ | ✅ | ✅ |
| CI/CD Pipelines | ✅ | ✅ | ✅ |
| Container Registry | ✅ | ✅ | ✅ |
| SAST (basic, Semgrep) | ✅ | ✅ | ✅ |
| Secret Detection (basic) | ✅ | ✅ | ✅ |
| Dependency Scanning (SCA) | ❌ | ❌ | ✅ |
| DAST | ❌ | ❌ | ✅ |
| Container Scanning | ❌ | ❌ | ✅ |
| IaC Security Scanning | ❌ | ❌ | ✅ |
| License Compliance | ❌ | ❌ | ✅ |
| Security Dashboard | ❌ | ❌ | ✅ |
| Vulnerability Management | ❌ | ❌ | ✅ |
| Security Policies | ❌ | ❌ | ✅ |
| SBOM / Dependency List | ❌ | ❌ | ✅ |
| Compliance Frameworks | ❌ | ❌ | ✅ |
| Multi-level MR Approvals | ❌ | ✅ | ✅ |
| SAML / SSO | ❌ | ✅ | ✅ |
| Extended Audit Events | ❌ | ✅ | ✅ |

> **Note:** Basic SAST and Secret Detection are available in Free tier. Advanced SAST with custom rulesets and the full security scanner suite requires Ultimate.

*Source: https://about.gitlab.com/pricing/feature-comparison/*

---

## 4. GitLab Architecture — Component Overview

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                         │
│        Browser   │   Git CLI   │   API Clients         │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                  INGESTION LAYER                        │
│   GitLab Workhorse (large files, LFS, artifact I/O)    │
│   GitLab Shell (SSH operations)                        │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                APPLICATION LAYER                        │
│   Puma (Rails web app — UI, API, business logic)        │
│   Sidekiq (background jobs — pipelines, webhooks,       │
│            security report processing)                  │
└──────────┬─────────────────────────────────────────────┘
           │                   │
┌──────────▼──────┐   ┌────────▼────────────────────────┐
│  DATA LAYER     │   │  GIT STORAGE LAYER              │
│  PostgreSQL     │   │  Gitaly (gRPC git operations)   │
│  (all platform  │   │  Gitaly Cluster (HA mode)       │
│   data)         │   │  Praefect (coordinator)         │
│  Redis          │   └─────────────────────────────────┘
│  (cache, queue) │
└──────────┬──────┘
           │
┌──────────▼────────────────────────────────────────────┐
│  STORAGE LAYER                                        │
│  Object Storage (S3/GCS/Azure Blob/MinIO)            │
│  — CI/CD Artifacts, LFS, Container Registry images   │
└───────────────────────────────────────────────────────┘
```

### GitLab Runner — Execution Layer

```
┌─────────────────────────────────────────────────────────┐
│              GITLAB RUNNER (Separate Process)           │
│                                                         │
│  Polls GitLab API for pending jobs                      │
│                                                         │
│  Executors:                                             │
│    Shell     — runs directly on Runner host             │
│    Docker    — runs in Docker containers               │
│    Kubernetes — runs in K8s pods                       │
│    VirtualBox — runs in VMs                            │
│    Custom    — user-defined executor                   │
│                                                         │
│  Can be deployed on: Cloud VM, bare metal, K8s,        │
│  air-gapped networks, edge devices                     │
└─────────────────────────────────────────────────────────┘
```

*Source: https://docs.gitlab.com/runner/*

### Component Role Summary

| Component | Responsibility | Key Technical Detail |
|---|---|---|
| Puma | Rails HTTP server — serves UI and API | Multi-threaded; handles all web requests |
| Sidekiq | Background job processing | Consumes jobs from Redis queues |
| PostgreSQL | Primary database | All platform data: users, projects, pipelines, findings |
| Redis | Cache + job queue | Session storage; Sidekiq job queue |
| Gitaly | Git repository access layer | gRPC service; wraps native git |
| GitLab Shell | SSH git operations | Calls Gitaly for git operations |
| Workhorse | Large object proxy | Intercepts large uploads before Puma |
| GitLab Runner | CI/CD job execution | Separate binary; registers with GitLab API |
| Object Storage | Artifact storage | S3-compatible; stores build artifacts, logs, container images |

*Source: https://docs.gitlab.com/ee/development/architecture.html*

---

## 5. Request Flow — Developer Commit to Pipeline Execution

Understanding the internal flow helps diagnose CI/CD failures:

```
1. Developer runs: git push origin feature-branch
         ↓
2. SSH connection → GitLab Shell → Gitaly (stores commit)
         ↓
3. GitLab Shell notifies Puma (HTTP callback)
         ↓
4. Puma creates Pipeline record in PostgreSQL
   Puma enqueues pipeline trigger job to Sidekiq via Redis
         ↓
5. Sidekiq processes job → selects a registered Runner
         ↓
6. Runner polls GitLab API → picks up pending job
         ↓
7. Runner executes job (Docker/Shell/K8s executor)
         ↓
8. Job produces artifacts → uploaded to Object Storage via Workhorse
         ↓
9. Job result (pass/fail) → stored in PostgreSQL via API
         ↓
10. Developer sees results in GitLab UI (Puma queries PostgreSQL)
```

**Why This Matters for Security:**  
Security scanning (SAST, Dependency Scanning, Container Scan) runs as **GitLab Runner jobs** — not as part of the GitLab application. This means:
- Security jobs can be isolated to dedicated Runner infrastructure
- Security jobs run in sandboxed Docker containers
- Security findings are uploaded as artifacts and ingested by the security parser

---

## 6. Why Organisations Consolidate

**Five Consolidation Drivers:**

1. **Security Posture**  
   One security dashboard across all scanners. No findings falling through integration gaps. Security policies enforced at the platform level, not per-pipeline.

2. **Compliance Auditability**  
   Single audit trail. "Who approved deployment X?" is one query. Compliance frameworks (SOC 2, ISO 27001, PCI DSS) map to GitLab compliance features directly.

3. **Developer Experience**  
   One login. One UI. One CLI. Merge Request shows code review, test results, and security findings in one view.

4. **Operational Cost**  
   Fewer integration contracts. Fewer webhook maintenance tasks. Single support vendor for the delivery platform.

5. **Governance Velocity**  
   Security policies defined once at the Group level and inherited by all sub-groups and projects. No manual per-project security configuration.

**The Honest Trade-Off:**

| Trade-Off | Reality |
|---|---|
| Platform depth vs breadth | Jira has deeper PM features; Checkmarx has more SAST language rules. GitLab wins on integration. |
| Vendor dependency | Every platform creates dependency. The question is: one integration point or 15? |
| Migration effort | Moving from GitHub + Jenkins + Jira + Snyk to GitLab is non-trivial. Plan 6-12 months for large orgs. |
| Feature gap | GitLab DAST and SAST are good; they are not the deepest point tools in the market. |

---

## 7. GitLab for AI / Robotics / IoT Teams — Specific Relevance

| Audience | Current Pain | GitLab Solution |
|---|---|---|
| AI Engineers | Model training CI separate from inference deployment | Unified pipeline for training job CI and model registry |
| Robotics Engineers | Firmware build pipeline separate from cloud API CI | Single platform for firmware + cloud service delivery |
| IoT Developers | OTA update pipeline has no security scanning | Container/artifact scanning integrated into OTA pipeline |
| Embedded Engineers | No dependency tracking for firmware libraries | Dependency scanning + SBOM for embedded dependencies |

We will address these specific use cases in Module 15.

---

## Key Terminology

| Term | Definition |
|---|---|
| Puma | Ruby on Rails application server used by GitLab — handles all HTTP traffic |
| Sidekiq | Background job processor — handles asynchronous tasks (pipeline triggers, webhooks) |
| Gitaly | gRPC service providing all git repository operations — abstracts git from the application |
| GitLab Runner | Separate binary that executes CI/CD pipeline jobs on registered infrastructure |
| Executor | The environment type a Runner uses to run jobs (Shell, Docker, Kubernetes) |
| Workhorse | Reverse proxy handling large file transfers before they reach Puma |
| Object Storage | S3-compatible storage for artifacts, LFS, container images |
| Group | GitLab organisational unit — contains sub-groups and projects; policies cascade down |
| Project | A GitLab repository — has its own CI/CD, issues, MRs, security settings |

---

## Personal Notes

_Questions about your organisation's current toolchain:_

Current SCM: _______________________________________________

Current CI/CD: _______________________________________________

Security tools currently used: ___________________________________

Biggest integration pain point: __________________________________

---

## References

1. GitLab Architecture — https://docs.gitlab.com/ee/development/architecture.html
2. GitLab Runner — https://docs.gitlab.com/runner/
3. GitLab Gitaly — https://docs.gitlab.com/ee/administration/gitaly/
4. GitLab Pricing — https://about.gitlab.com/pricing/feature-comparison/
5. GitLab Security Dashboard — https://docs.gitlab.com/ee/user/application_security/security_dashboard/
6. GitLab Audit Events — https://docs.gitlab.com/ee/administration/audit_events.html
7. GitLab SAST — https://docs.gitlab.com/ee/user/application_security/sast/
