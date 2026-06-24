# LAB WORKBOOK — MODULE 4
## Source Control and Governance: Hands-On Lab

---

**Duration:** 40 minutes  
**Difficulty:** Beginner–Intermediate  
**Requires:** GitLab account (Ultimate trial or self-managed instance)

---

## Lab Overview

You will build a governed repository with enterprise-grade source control controls:

```
Lab Flow:
Step 1  → Create project with sample application
Step 2  → Create initial code structure
Step 3  → Protect main branch
Step 4  → Create CODEOWNERS file
Step 5  → Configure approval rules
Step 6  → Create feature branch with code change
Step 7  → Open Merge Request
Step 8  → Code review and approve (pair exercise)
Step 9  → Merge and review audit trail
```

---

## Prerequisites

- GitLab account with access to a group or namespace where you can create projects
- If using self-managed GitLab: Maintainer role on the project
- A second GitLab user account OR a classmate to act as reviewer (for approval exercise)

---

## Step 1: Create the Project (5 minutes)

### 1.1 Create a New Project

1. Navigate to GitLab (gitlab.com or your instance)
2. Click **"New project"** → **"Create blank project"**
3. Fill in:
   - **Project name:** `robovision-controller`
   - **Project slug:** `robovision-controller`
   - **Visibility Level:** Private
   - **Initialize repository with a README:** ✅ Checked

4. Click **Create project**

---

## Step 2: Create Initial Application Structure (5 minutes)

### 2.1 Add Sample Application Files

Use the GitLab Web IDE (or git CLI) to create the following structure.

**Option A — Web IDE:**
1. In your project, click the **"."** key (or click **"Edit"** → **"Web IDE"**)
2. Create the following files

**Option B — Git CLI:**
```bash
git clone https://gitlab.com/<your-namespace>/robovision-controller.git
cd robovision-controller
```

---

### File: `src/auth/login.py`

```python
# RoboVision Authentication Module
# This file handles user authentication for the robot controller API

import hashlib
import os

def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate a user against stored credentials.
    
    Args:
        username: The username to authenticate
        password: The plaintext password
    
    Returns:
        bool: True if authentication succeeds
    """
    # Hash the provided password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # In production, this would query the database
    # For this lab, we use a simple comparison
    stored_hash = get_stored_hash(username)
    
    return password_hash == stored_hash


def get_stored_hash(username: str) -> str:
    """Retrieve stored password hash for user."""
    # Placeholder - would normally query PostgreSQL
    users = {
        "admin": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
        "operator": "1f40fc92da241694750979ee6cf582f2d5d7d28e18335de05abc54d0560e0f53"
    }
    return users.get(username, "")
```

---

### File: `src/api/robot_controller.py`

```python
# RoboVision Robot Controller API
# Core movement and sensor interface

from typing import Dict, Optional

class RobotController:
    """Main controller class for RoboVision robotic platform."""
    
    def __init__(self, robot_id: str, config: Dict):
        self.robot_id = robot_id
        self.config = config
        self.is_active = False
    
    def initialise(self) -> bool:
        """Initialise the robot controller with safety checks."""
        # Verify safety limits are configured
        if 'max_velocity' not in self.config:
            raise ValueError("Safety limit 'max_velocity' not configured")
        
        if 'max_torque' not in self.config:
            raise ValueError("Safety limit 'max_torque' not configured")
        
        self.is_active = True
        return True
    
    def move(self, direction: str, velocity: float) -> bool:
        """
        Move the robot in the specified direction.
        
        Args:
            direction: 'forward', 'backward', 'left', 'right'
            velocity: Speed in m/s
        """
        if not self.is_active:
            return False
        
        # Enforce safety velocity limit
        max_velocity = self.config.get('max_velocity', 1.0)
        if velocity > max_velocity:
            velocity = max_velocity
        
        print(f"Robot {self.robot_id}: Moving {direction} at {velocity} m/s")
        return True
    
    def stop(self) -> bool:
        """Emergency stop — always succeeds."""
        print(f"Robot {self.robot_id}: EMERGENCY STOP")
        return True
```

---

### File: `firmware/safety/limits.h`

```c
/*
 * RoboVision Safety Limits Configuration
 * 
 * CRITICAL: Changes to this file require Safety Review approval.
 * See CODEOWNERS for approval requirements.
 */

#ifndef ROBOVISION_SAFETY_LIMITS_H
#define ROBOVISION_SAFETY_LIMITS_H

/* Maximum joint velocity limits (rad/s) */
#define MAX_JOINT_VELOCITY      3.14159f   /* π rad/s */
#define MAX_JOINT_ACCELERATION  6.28318f   /* 2π rad/s² */

/* Force/torque limits (Nm) */
#define MAX_JOINT_TORQUE        50.0f
#define COLLISION_FORCE_LIMIT   20.0f

/* Emergency stop thresholds */
#define ESTOP_FORCE_THRESHOLD   25.0f
#define ESTOP_VELOCITY_THRESHOLD 4.0f

#endif /* ROBOVISION_SAFETY_LIMITS_H */
```

---

### File: `terraform/main.tf`

```hcl
# RoboVision Cloud Infrastructure
# Terraform configuration for device management backend

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for deployment"
  default     = "us-east-1"
}

# Device Management Database
resource "aws_db_instance" "device_management" {
  identifier     = "robovision-device-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  
  # Note: In production, this should use aws_secretsmanager_secret
  username       = "robovision_admin"
  password       = var.db_password
  
  # IMPORTANT: This should be false in production
  publicly_accessible = false
  
  tags = {
    Environment = "production"
    Project     = "robovision"
  }
}

variable "db_password" {
  description = "Database password"
  sensitive   = true
}
```

---

### File: `README.md`

```markdown
# RoboVision Controller

Core software platform for the RoboVision robotic system.

## Repository Structure

```
src/
  auth/          — Authentication and authorisation module
  api/           — Robot controller API
firmware/
  safety/        — Safety limit configurations (SAFETY CRITICAL)
  drivers/       — Hardware driver implementations
terraform/       — Cloud infrastructure as code
ci/              — CI/CD pipeline templates
```

## Change Management

All changes to this repository require a Merge Request.
Critical paths require additional approvals — see `.gitlab/CODEOWNERS`.

## Safety Notice

Changes to `firmware/safety/` require approval from the Safety Engineering team.
Unauthorised changes to safety limits may cause physical harm.
```

**Commit message:** `feat: initial RoboVision application structure`

---

## Step 3: Protect the Main Branch (5 minutes)

### 3.1 Configure Branch Protection

1. Navigate to: **Settings → Repository → Protected branches**
2. Find the `main` branch entry (GitLab auto-protects it on project creation)
3. Click **Expand** next to `main`

Configure the following:

| Setting | Value |
|---|---|
| Allowed to merge | Maintainers |
| Allowed to push | No one |
| Allowed to force push | ❌ (off) |
| Code owner approval | ✅ (on) — requires Ultimate |

4. Click **Save changes**

### 3.2 Verify Protection

Try to push directly to `main`:
```bash
# This should FAIL
echo "test" >> README.md
git add README.md
git commit -m "direct push test"
git push origin main
```

Expected error:
```
remote: GitLab: You are not allowed to push code to protected branches on this project.
```

✅ **Verification:** Direct push is blocked. All changes must go through Merge Requests.

---

## Step 4: Create the CODEOWNERS File (5 minutes)

### 4.1 Create CODEOWNERS on a Branch

Create a new branch:
```bash
git checkout -b setup/governance-controls
```

Create `.gitlab/CODEOWNERS`:

```
# RoboVision CODEOWNERS
# Format: [path pattern] @user_or_group
# 
# Replace @username with actual GitLab usernames or group paths.
# For this lab, use your own username and your classmate's username.

####################################################################
# SECTION: Security Review
# Changes to authentication or cryptographic code require security review
####################################################################

[Security Review]
/src/auth/             @<your-username> @<classmate-username>
/src/crypto/           @<your-username>

####################################################################
# SECTION: Infrastructure Review  
# CI/CD and cloud infrastructure changes require devops approval
####################################################################

[Infrastructure Review]
/.gitlab-ci.yml        @<your-username>
/ci/                   @<your-username>
/terraform/            @<your-username> @<classmate-username>

####################################################################
# SECTION: Safety Critical Review
# Safety limit changes require safety engineering sign-off
# This section is MANDATORY — cannot be merged without approval
####################################################################

[Safety Critical Review]
/firmware/safety/      @<your-username> @<classmate-username>
/firmware/limits/      @<your-username>

####################################################################
# SECTION: Firmware Review
# All firmware changes require embedded team review
####################################################################

[Firmware Review]
/firmware/             @<your-username>
/drivers/              @<your-username>

####################################################################
# Default ownership — tech leads review everything else
####################################################################

*                      @<your-username>
```

> **Lab Note:** Replace `<your-username>` and `<classmate-username>` with actual GitLab usernames. For solo practice, use the same username for both — but note this means you will be the required approver on your own MRs (less realistic; ideally pair with a classmate).

Commit and push:
```bash
git add .gitlab/CODEOWNERS
git commit -m "feat: add CODEOWNERS governance configuration

- Security team review required for auth and crypto code
- Infrastructure team review required for CI/CD and Terraform
- Safety engineering MANDATORY approval for safety-critical firmware
- Firmware team review for all embedded code"

git push origin setup/governance-controls
```

### 4.2 Create and Merge CODEOWNERS MR

1. In GitLab, navigate to **Merge Requests → New merge request**
2. Source: `setup/governance-controls` → Target: `main`
3. Title: `feat: add source control governance controls`
4. Click **Create merge request**
5. If you have no approval rules yet, merge this MR directly (we'll add rules next)

---

## Step 5: Configure Approval Rules (5 minutes)

### 5.1 Set Up Project Approval Rules

Navigate to: **Settings → Merge Requests → Approval rules**

#### Rule 1: Standard Review
- Click **Add approval rule**
- Name: `Standard Code Review`
- Approvals required: `1`
- Eligible approvers: Add your classmate's user or a group

#### Rule 2: Security Review (Optional for lab — show configuration)
- Name: `Security Team Review`
- Approvals required: `1`
- Eligible approvers: Add `@security-team` group (or your classmate)

### 5.2 Configure Approval Settings

In the same **Settings → Merge Requests** page, scroll to **Approval settings**:

Enable the following:
- ✅ **Prevent approval by merge request author**
- ✅ **Prevent approvals by users who add commits to the MR**
- ✅ **Remove all approvals when commits are added to the source branch**

Click **Save changes**

---

## Step 6: Create a Feature Branch with Code Change (5 minutes)

### 6.1 Simulate a Security-Relevant Code Change

Create a branch that touches CODEOWNERS-covered paths:

```bash
git checkout main
git pull origin main
git checkout -b feature/update-auth-module
```

Modify `src/auth/login.py` — add a new function:

```python
# Add this function to src/auth/login.py

def generate_session_token(user_id: int) -> str:
    """
    Generate a secure session token for authenticated user.
    
    Args:
        user_id: The authenticated user's ID
    
    Returns:
        str: A cryptographically secure session token
    """
    import secrets
    import time
    
    # Generate a 32-byte random token
    token = secrets.token_hex(32)
    timestamp = int(time.time())
    
    return f"{user_id}:{timestamp}:{token}"
```

Also modify `firmware/safety/limits.h` — change a comment:
```c
/* Updated: Added documentation for safety limit justification */
/* Maximum joint velocity limits (rad/s) — based on ISO 10218-1 Table 3 */
#define MAX_JOINT_VELOCITY      3.14159f   /* π rad/s per ISO 10218-1 */
```

Commit and push:
```bash
git add src/auth/login.py firmware/safety/limits.h
git commit -m "feat: add session token generation; update safety limit documentation

- Add generate_session_token() with cryptographically secure token
- Update safety limit comments with ISO standard reference
- Refs: ISSUE-42"

git push origin feature/update-auth-module
```

---

## Step 7: Open and Review the Merge Request (5 minutes)

### 7.1 Create the Merge Request

1. GitLab will show a banner: **"You pushed to feature/update-auth-module. Create merge request"** — click it
   OR navigate to **Merge Requests → New merge request**

2. Configure the MR:
   - **Title:** `feat: add session token generation and update safety documentation`
   - **Description:**
     ```
     ## What
     - Add `generate_session_token()` function using `secrets.token_hex()`
     - Update safety limit comments with ISO 10218-1 references
     
     ## Why
     - Current session management uses predictable tokens (security concern)
     - Safety documentation was missing normative reference
     
     ## Security Considerations
     - Uses Python `secrets` module (cryptographically secure random)
     - Token includes user_id and timestamp for server-side validation
     - No sensitive data in token body
     
     ## Testing
     - [ ] Unit test: token uniqueness verified
     - [ ] Integration test: session lifecycle tested
     ```
   - **Assignee:** Yourself
   - **Reviewer:** Your classmate (or another user)

3. Click **Create merge request**

### 7.2 Observe CODEOWNERS in Action

In the MR view, scroll to the **Approvals** section. You should see:

```
Required approvals:
  ┌─────────────────────────────────────┐
  │ Security Review                      │
  │ ✗ Pending: @your-classmate          │
  │   (src/auth/login.py modified)      │
  └─────────────────────────────────────┘
  ┌─────────────────────────────────────┐
  │ Safety Critical Review               │
  │ ✗ Pending: @your-classmate          │  
  │   (firmware/safety/limits.h modified)│
  └─────────────────────────────────────┘
```

✅ **Observation:** GitLab automatically detected which CODEOWNERS-covered paths were modified and added the required approvers. You did not configure these approvers manually per MR — it happened automatically from the CODEOWNERS file.

---

## Step 8: Code Review and Approval (5 minutes)

### 8.1 Reviewer Actions (your classmate performs these steps)

1. Classmate opens the MR URL
2. Reviews the **Changes** tab — examine the diff
3. Leaves a comment on `login.py`:
   ```
   The token format includes user_id which might allow token enumeration.
   Consider using an opaque random token and storing the user_id server-side.
   ```
4. **Does NOT approve yet** — waiting for your response

### 8.2 Author Responds to Review

1. You (the author) reply to the comment:
   ```
   Good catch. For this implementation the user_id:timestamp is stored 
   server-side and validated on each request. The token itself is 32 bytes 
   of crypto-random so enumeration requires breaking 256-bit entropy.
   Will add a comment to document this.
   ```
2. Add a clarifying comment to the code:
   ```python
   # Token format: user_id:timestamp:random_hex
   # user_id and timestamp are validated server-side.
   # The random portion provides 256-bit entropy (32 bytes).
   # Opaque tokens considered and rejected: server-side lookup overhead.
   token = secrets.token_hex(32)
   ```
3. Commit and push the change
4. **Notice:** The existing approvals are automatically removed (because `Remove approvals on new commits` is enabled)

### 8.3 Final Approval

After reviewing the updated code:
1. Classmate resolves the thread
2. Classmate clicks **Approve**
3. Classmate selects the **Security Review** approval section ✅
4. Classmate selects the **Safety Critical Review** approval section ✅

---

## Step 9: Merge and Verify Audit Trail (5 minutes)

### 9.1 Merge the MR

1. With all approvals given and all threads resolved, the **Merge** button becomes active
2. Configure merge:
   - ✅ Delete source branch
   - ✅ Squash commits (optional for clean history)
3. Click **Merge**

### 9.2 Review the Audit Trail

**MR Audit Trail (in MR activity log):**
Navigate to the MR and scroll through the activity — you should see:
```
[timestamp] @your-username created merge request
[timestamp] Pipeline #xxx started
[timestamp] Pipeline #xxx passed
[timestamp] @classmate-username approved (Security Review)
[timestamp] @classmate-username approved (Safety Critical Review)
[timestamp] @your-username merged
```

**GitLab Audit Events (Admin/Group level):**
Navigate to **Group → Compliance → Audit Events** (or Admin → Audit Events):
```
Action: merge_request_merged
Actor: @your-username
Target: robovision-controller!1
Metadata: approved_by: @classmate-username, branch: main
```

✅ **This audit trail is the evidence** a compliance auditor needs to verify change management controls.

---

## Lab Verification Checklist

At the end of the lab, verify:

- [ ] `main` branch is protected (no direct push possible)
- [ ] CODEOWNERS file is committed to `.gitlab/CODEOWNERS`
- [ ] At least two CODEOWNERS sections created (Security + Safety)
- [ ] Approval rules configured with author-approval prevention
- [ ] MR was created from feature branch (not direct push to main)
- [ ] CODEOWNERS auto-populated approval requirements in MR
- [ ] Review comment was made and responded to
- [ ] Approval invalidated after code change (new commit)
- [ ] MR merged only after all sections approved
- [ ] Audit trail shows approval evidence

---

## Extension Exercises (If Time Allows)

### Extension 1: MR Template
Create `.gitlab/merge_request_templates/Default.md`:

```markdown
## Change Description
<!-- What does this MR do? -->

## Motivation
<!-- Why is this change needed? -->

## Security Considerations
<!-- Were any security-sensitive areas modified? -->
<!-- Auth, crypto, input validation, dependencies, infrastructure? -->

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Security scan results reviewed

## Compliance
- [ ] CODEOWNERS approvals obtained
- [ ] No hardcoded credentials introduced
- [ ] No new critical vulnerabilities introduced
```

### Extension 2: Try to Force Push
Attempt a force push to `main`:
```bash
git commit --amend -m "amended commit"
git push --force origin main
```
Observe the error — document why force push protection matters for audit integrity.

### Extension 3: Bypass Attempt
Try to approve your own MR (with author-approval prevention enabled).
Observe that GitLab blocks self-approval.

---

## Troubleshooting Guide

| Problem | Likely Cause | Solution |
|---|---|---|
| Cannot push to `main` even from Web IDE | Protected branch working correctly | Create a feature branch first |
| CODEOWNERS approvals not appearing | CODEOWNERS syntax error; code owners not members of project | Check syntax; verify users are project members |
| Approval section shows but is not required | `Code owner approval` not enabled on protected branch | Settings → Repository → Protected branches → Enable code owner approval |
| Cannot see Audit Events | Not on Ultimate or insufficient permissions | Requires Maintainer+ role; Ultimate for full events |
| MR merge button grey despite approvals | Pipeline still running or thread unresolved | Wait for pipeline; resolve all threads |

---

## Lab Solution Reference

**CODEOWNERS minimum viable configuration:**
```
[Security Review]
/src/auth/    @reviewer-username

[Safety Review]
/firmware/    @reviewer-username

*             @reviewer-username
```

**Minimum approval settings (Settings → Merge Requests):**
- Pipelines must succeed: ✅
- Prevent approval by author: ✅
- Remove all approvals on new commits: ✅

**Minimum protected branch settings:**
- Allowed to push: `No one`
- Allowed to merge: `Maintainers`
- Code owner approval: `Required`
