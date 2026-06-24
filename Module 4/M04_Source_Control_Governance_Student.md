# STUDENT HANDBOOK — MODULE 4
## Source Control and Governance

---

**Workshop:** GitLab Ultimate for Secure SDLC, DevSecOps, AI, Robotics & IoT  
**Day:** 1 of 2 | **Module:** 4 of 16 | **Duration:** 75 minutes

---

## Learning Objectives

- Compare monorepo and polyrepo strategies with trade-offs
- Explain Trunk-Based Development vs Git Flow
- Configure GitLab Merge Request approval rules
- Implement CODEOWNERS for file-level ownership and required reviews
- Configure protected branches to enforce governance
- Understand how these controls create a compliance-ready audit trail

---

## 1. The Governance Problem in Source Control

Source control is not just a backup system. In a governed software delivery organisation, the repository is the **chain of custody** for every change that reaches production. Consider what compliance frameworks require:

| Framework | Requirement | GitLab Control |
|---|---|---|
| SOC 2 Type II | Evidence of change review and approval | MR approvals + audit trail |
| PCI DSS 6.3.2 | Protection of bespoke software | Protected branches + MR requirement |
| NIST SSDF PS.1.1 | Protect code from unauthorized access | Branch protection + RBAC |
| ISO 26262 (Automotive) | Traceability of software changes | MR + linked issues + pipeline records |
| IEC 62443 (ICS/OT) | Change management for industrial software | Approval rules + audit events |

Without source control governance, these controls do not exist. GitLab makes them automated and auditable.

---

## 2. Repository Strategy: Monorepo vs Polyrepo

### Monorepo
All projects/services live in a single repository.

**Used by:** Google (internal Piper), Facebook (fbsource), Microsoft (Windows repo), Twitter

**Advantages:**
- Atomic cross-service changes — fix a shared library and update all consumers in one MR
- Unified CI/CD — one pipeline definition drives all services
- Simplified dependency management — one lockfile, no version drift
- Easy cross-service code search

**Disadvantages:**
- CI/CD performance — full pipeline on every commit (mitigated by `rules: changes:`)
- Repository size — slow clone time on Runners
- Merge conflicts — high-frequency teams interfere
- Access control granularity — repository-level RBAC only (CODEOWNERS mitigates at file level)

**GitLab Monorepo Features:**
```yaml
# Trigger job only when firmware code changes
build-firmware:
  rules:
    - changes:
        - firmware/**/*
        - shared-libs/**/*

# Trigger job only when cloud API changes
build-api:
  rules:
    - changes:
        - api/**/*
        - shared-libs/**/*
```
*Source: https://docs.gitlab.com/ee/ci/yaml/#ruleschanges*

### Polyrepo
Each service/component has its own repository.

**Advantages:**
- Team autonomy — independent release cycles
- Clean access control — RBAC per repository
- Smaller clone size — faster CI

**Disadvantages:**
- Cross-service changes require coordinated MRs across N repositories
- Dependency version drift — teams pin different versions of shared libraries
- Security policy overhead — enforcement needed per repository
- No atomic cross-cutting change

### Decision Framework

| Criterion | Favours Monorepo | Favours Polyrepo |
|---|---|---|
| Service coupling | High | Low |
| Release cadence | Unified | Independent |
| Team size | Large, centralised | Small, autonomous |
| Security policy | Centralised governance | Team-level governance |
| CI/CD maturity | High (path filters implemented) | Any |
| Typical IoT use | Firmware + Cloud together | Large platform with many teams |

---

## 3. Branching Strategies

### Git Flow — Brief Overview

Git Flow uses long-lived branches: `main`, `develop`, `release/*`, `hotfix/*`, `feature/*`.

**The problem at high velocity:** Feature branches that live for weeks accumulate integration debt. Big-bang merges are painful and high-risk. Git Flow was designed for **monthly release cadences** — it becomes a liability for teams deploying daily.

### Trunk-Based Development (TBD)

**Core principle:** All developers commit to `main` (trunk) at least once per day. Features are isolated by **feature flags**, not branches. Releases are tags on trunk.

**Why DORA Research endorses TBD:**
- Short branches = small batches = low integration risk
- Every commit is integrated and tested continuously
- Lead Time for Changes (DORA metric) is directly reduced

*Source: https://dora.dev/capabilities/trunk-based-development/*

```
Traditional Git Flow:
main ─────────────────────────────────────────── (merge after 3 weeks)
             \                                 /
feature/x     ──────────────────────────────

TBD:
main ─── C1 ─── C2 ─── C3 ─── C4 ─── C5 ─── (daily commits)
         ↑       ↑       ↑       ↑       ↑
       (small) (small) (small) (small) (small)
       Integration risk per commit is minimal.
```

### Practical Recommendation for Most Teams

For teams not yet ready for full TBD:

```
main          ← Production. Protected. No direct push. Only MR.
  └── feature/ISSUE-123-auth-fix    ← Short-lived (< 3 days)
  └── feature/ISSUE-456-firmware    ← Short-lived
  └── hotfix/CVE-2024-xxxxx        ← Emergency fix path
```

Rules:
- Feature branches must be created from latest `main`
- Branches must not live longer than 3 working days
- Every merge to `main` requires: passing CI, 1+ approval, CODEOWNERS sign-off

---

## 4. Merge Requests — The Governance Engine

### What a Merge Request Is (Mechanically)

A GitLab Merge Request is not just a diff viewer. It is:
- A **database record** linking source branch to target branch
- A **pipeline trigger** — CI runs automatically on each commit to the MR
- An **enforcement point** — cannot merge unless all conditions met
- An **audit record** — every approval, comment, and commit permanently logged

*Source: https://docs.gitlab.com/ee/user/project/merge_requests/*

### Merge Request Pipeline Integration

When a developer pushes to a feature branch with an open MR:
1. GitLab automatically triggers the pipeline
2. Security scans run (SAST, Secret Detection, etc. if configured)
3. Test results and security findings appear inside the MR view
4. Status checks block or allow merging based on results

### Critical MR Settings

| Setting | Where | Effect |
|---|---|---|
| Pipelines must succeed | Project → Settings → Merge Requests | Cannot merge with failing CI |
| All threads must be resolved | Project → Settings → Merge Requests | Review comments must be addressed |
| Require code owner approval | Branch protection settings | CODEOWNERS rules enforced |
| Prevent approval by author | Project → Settings → Merge Requests | Four-eyes principle enforced |
| Remove approvals on new commits | Project → Settings → Merge Requests | Re-review required after code change |

---

## 5. Approval Rules

### Purpose
Approval rules define *who* must approve an MR and *how many* approvals are required before merging is permitted.

*Source: https://docs.gitlab.com/ee/user/project/merge_requests/approvals/*

### Rule Types

**Project-level rules (apply to all MRs):**
- "Require 2 approvals from group `senior-engineers`"
- "Require 1 approval from group `security-team` when security findings are introduced"

**Security Approval Policies (Ultimate):**
When a new critical/high vulnerability is detected in an MR, a security policy can automatically require security team approval before the MR can merge.

### Key Settings

```
✅  Prevent approval by merge request author
    → Author cannot approve their own MR

✅  Prevent approvals by users who add commits  
    → Contributors cannot approve after pushing to the MR

✅  Remove all approvals when commits are added to the source branch
    → Reviewers must re-approve after any code change

✅  Require user password to approve
    → Adds authentication step to approval
```

**The Four-Eyes Combination:**
Enabling ALL four settings above creates a strong four-eyes control:
- At least one other person must review AND approve
- Approval cannot be given by anyone who touched the code
- Any change invalidates previous approvals

This satisfies PCI DSS, SOC 2, and ISO 27001 change management requirements.

---

## 6. CODEOWNERS

### What It Does
CODEOWNERS maps file paths (using glob patterns) to GitLab users or groups. When those files are modified in an MR, their owners become **required approvers**.

*Source: https://docs.gitlab.com/ee/user/project/codeowners/*

### File Location
`.gitlab/CODEOWNERS` (recommended) or `CODEOWNERS` in repo root, or `docs/CODEOWNERS`.

### Syntax Examples

```
# Security team must approve all authentication code changes
/src/auth/                    @security-team

# DevOps team must approve all CI/CD pipeline changes  
/.gitlab-ci.yml               @devops-team
/ci/                          @devops-team

# Two owners required for cryptographic code
/src/crypto/                  @security-team @cryptography-lead

# IoT device configuration: both firmware and cloud teams
/device-configs/              @firmware-team @cloud-team

# Firmware safety limits: safety engineers only
/firmware/safety/             @safety-engineers

# Default: tech leads own everything not otherwise specified
*                             @tech-leads
```

### CODEOWNERS Sections (GitLab Ultimate)

Sections create **separate approval gates** — each section must be independently approved:

```
[Security Review]
/src/auth/            @security-team
/src/crypto/          @security-team
/ota-update/          @security-team

[Infrastructure Review]
/.gitlab-ci.yml       @devops-team
/terraform/           @devops-team
/k8s/                 @devops-team

[Firmware Review]
/firmware/            @embedded-team
/drivers/             @embedded-team

^[Optional Legal Review]
/LICENSE              @legal-team
```

The `^` prefix makes a section optional (not blocking).

---

## 7. Protected Branches

### What They Enforce
*Source: https://docs.gitlab.com/ee/user/project/protected_branches.html*

| Rule | Recommended Setting | Why |
|---|---|---|
| Allowed to push | `No one` | Forces all changes through MR process |
| Allowed to merge | `Maintainers` | Privileged role controls final merge |
| Allow force push | `OFF` | Prevents history rewriting; audit trail intact |
| Code owner approval required | `ON` | CODEOWNERS rules enforced on merge |

### Configuration Path
`Project → Settings → Repository → Protected branches`

### Recommended `main` Branch Configuration:
```
Branch: main
  Allowed to push and merge: No one (push), Maintainers (merge)
  Allowed to force push:     No
  Require code owner approval: Yes
  Require a pull request:    Yes (enforced by push restriction)
```

---

## 8. Putting It All Together — Governance Stack

```
Governance Layer        Control                   Prevents
─────────────────────────────────────────────────────────────
Repository level        RBAC (Roles)              Unauthorized repository access
File level              CODEOWNERS                Critical files changed without owner sign-off
Branch level            Protected branches        Direct push bypassing review
MR level                Approval rules            Unreviewed code merging
CI level                Pipeline requirements     Failing tests or security scans merging
Process level           MR templates              Security checklist skipped in review
Audit level             GitLab audit events       Evidence destruction or tampering
```

---

## 9. Hands-On Lab Preview

In the lab you will:
1. Create a GitLab project with a sample Python application
2. Protect the `main` branch (no direct push, Maintainers can merge)
3. Create a `.gitlab/CODEOWNERS` file with ownership rules
4. Configure approval rules (2 approvals, prevent self-approval)
5. Create a feature branch and modify a CODEOWNERS-covered file
6. Open a Merge Request and observe approval requirements
7. Perform a code review (pair with another participant)
8. Approve and merge — review the audit trail

> **Lab Guide:** See `M04_Lab_Workbook.md` for step-by-step instructions.

---

## Key Terminology

| Term | Definition |
|---|---|
| Monorepo | All services/components in one repository |
| Polyrepo | Each service/component in its own repository |
| Trunk-Based Development | All developers commit to main at least daily; no long-lived branches |
| Feature Flag | Runtime toggle for in-progress features — enables TBD without shipping incomplete code |
| Merge Request | GitLab's interface for proposing, reviewing, approving, and merging code changes |
| CODEOWNERS | File mapping path patterns to required approvers |
| Protected Branch | Branch configuration preventing direct push and requiring MR |
| Approval Rule | Defines who must approve an MR and how many approvals are needed |
| Four-Eyes Principle | At least two people must verify any change before it proceeds |
| Audit Trail | Immutable log of who did what and when |

---

## Personal Notes

_Branching strategy I want to propose for my team:_

_CODEOWNERS patterns relevant to my project:_

_Compliance controls my organisation needs to satisfy:_

---

## References

1. GitLab Merge Requests — https://docs.gitlab.com/ee/user/project/merge_requests/
2. GitLab Approval Rules — https://docs.gitlab.com/ee/user/project/merge_requests/approvals/
3. GitLab CODEOWNERS — https://docs.gitlab.com/ee/user/project/codeowners/
4. GitLab Protected Branches — https://docs.gitlab.com/ee/user/project/protected_branches.html
5. DORA: Trunk-Based Development — https://dora.dev/capabilities/trunk-based-development/
6. GitLab CI rules:changes — https://docs.gitlab.com/ee/ci/yaml/#ruleschanges
7. NIST SSDF — https://csrc.nist.gov/Projects/ssdf
