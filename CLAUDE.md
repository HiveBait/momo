# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**public-cloud-security** - Centralized security tooling, threat intelligence, and incident response playbooks for H2O.ai's multi-cloud infrastructure. Houses supply chain security frameworks, APT threat modeling, and automated security monitoring solutions.

## Repository Structure

**IMPORTANT: Current Hub Repository Configuration**

This repository is currently named `momo` and contains the `enterprise-security-governance/` subdirectory as the security framework hub.

**Repository Layout:**
```
HiveBait/momo/                                    ← Hub repository (configurable name)
├── enterprise-security-governance/               ← Security framework (always this path)
│   ├── .github/workflows/
│   │   ├── central-security-gate.yml            ← Reusable workflow (Layer 2)
│   │   └── bulk-lockfile-generator.yml          ← Deployment automation
│   ├── scripts/dependency_age_gate.py           ← Validation logic
│   ├── templates/                                ← Spoke deployment templates
│   └── policies/allowlist.json                   ← Break-glass exemptions
├── .github/workflows/                            ← Root-level workflows (for hub repo itself)
│   ├── bulk-lockfile-generator.yml              ← Duplicate for convenience
│   └── ...
└── CLAUDE.md                                     ← This file
```

**If the hub repository name changes in the future**, update these locations:

1. **Spoke workflow templates** (`templates/.github-workflows-security-gate.yml`):
   ```yaml
   uses: <org>/<new-hub-repo>/.github/workflows/central-security-gate.yml@main
   #            ^^^^^^^^^^^^^^^^ Update this
   ```

2. **Bulk deployment workflow** (`.github/workflows/bulk-lockfile-generator.yml`):
   - Line ~71: `repository: ${{ inputs.organization }}/momo` → Update to new repo name
   - Line ~76: `sparse-checkout: enterprise-security-governance/...` → Path stays the same

3. **Documentation references** in this file and README files that reference `HiveBait/momo`

4. **Spoke repositories** already deployed: Must update their `.github/workflows/security-gate.yml` to reference new hub repo name

**Key principle:** The security framework directory (`enterprise-security-governance/`) path is fixed, but the containing repository name (`momo`) is configurable.

---

### enterprise-security-governance/
Complete zero-cost supply chain security enforcement framework for GitHub Enterprise organizations using **hub-and-spoke architecture**.

**Purpose:** Centralized policy hub that enforces 7-day package maturation gates across 1,000+ developer repositories. Updates once in the hub automatically apply to all spoke repositories.

**Architecture:** Hub-and-Spoke (Reusable Workflows)
- **Hub:** `momo` repository containing `enterprise-security-governance/` subdirectory (contains all security logic)
- **Spokes:** All other repositories (minimal 23-line workflow that calls hub)
- **Benefit:** Update security logic once in hub → all 1,000+ repos benefit immediately

**Four-Layer Defense System:**
- **Layer 0 (Client-Side):** Package manager configs (npm, pnpm, bun, uv) block installations < 7 days old
- **Layer 1 (Dependabot Cooldown):** Native GitHub feature prevents PR creation for immature packages
- **Layer 2 (Security Gate):** Required workflow validates PRs at merge time (hub-and-spoke)
- **Layer 3 (Observability):** All events shipped to Coralogix SIEM for audit trail

**Key Components:**

**Hub Repository Files:**
- `scripts/dependency_age_gate.py` - Multi-language (npm, PyPI, Go) dependency age validator (410 lines, Python stdlib only)
- `.github/workflows/central-security-gate.yml` - **Reusable workflow** called by spoke repos
- `.github/workflows/bulk-lockfile-generator.yml` - Automated deployment to 1,000+ repos
- `templates/.github-workflows-security-gate.yml` - Template deployed to spoke repos (23 lines)
- `templates/.npmrc`, `.bunfig.toml`, `uv.toml` - Client-side protection configs (Layer 0)
- `policies/allowlist.json` - Break-glass exemption policy (CODEOWNERS-enforced)
- `terraform/main.tf` - Organization-level rulesets and secrets
- `terraform/enterprise.tf` - Enterprise-level rulesets (all orgs in enterprise)

**Spoke Repository Files (deployed automatically):**
- `.github/workflows/security-gate.yml` - Calls hub's reusable workflow (23 lines)
- `.github/dependabot.yml` - Native cooldown configuration (Layer 1)
- `package-lock.json`, `uv.lock`, `go.sum` - Lockfiles (if missing)
- `.npmrc`, `bunfig.toml` - Client-side protection (Layer 0, optional)

**Deployment Options:**

**Option A: Organization-Level (Single Org)**
```bash
cd enterprise-security-governance/terraform
export GITHUB_TOKEN="your-pat"
export TF_VAR_coralogix_api_key="your-key"
terraform init
terraform apply -var-file=terraform.tfvars.local
```

**Option B: Enterprise-Level (All Orgs)**
```bash
cd enterprise-security-governance/terraform
export GITHUB_TOKEN="your-enterprise-admin-pat"
export TF_VAR_coralogix_api_key="your-key"
terraform init
terraform apply -var-file=terraform.tfvars.enterprise
```

**Option C: Bulk Deployment (Automated)**
```bash
# Push hub repository first
git push origin main

# Deploy to all spoke repositories
gh workflow run bulk-lockfile-generator.yml \
  -f organization=h2oai \
  -f dry_run=false \
  -f max_repos=0

# This deploys:
# ✅ Lockfiles (if missing)
# ✅ .github/dependabot.yml (Layer 1)
# ✅ .github/workflows/security-gate.yml (Layer 2 - hub caller)
# ✅ Client-side configs (Layer 0 - optional)
```

### .github/Playbook/Supply Chain/
Incident response playbooks and audit tooling for supply chain compromise detection.

**Key Scripts:**
- `audit-org-github-actions.sh` - Scans all org repositories for suspicious workflow activity during incident windows
- `audit-github-actions.sh` - Single-repository deep scan for IOCs (TanStack patterns, token exfiltration, registry manipulation)
- `run-supply-chain-audit.sh` - Wrapper script for quick incident response
- `analyze-tanstack-findings.sh` - Post-audit analysis and reporting

**Usage Pattern (Incident Response):**
```bash
cd .github/Playbook/Supply\ Chain/Github/

# Quick audit for specific incident window
./audit-org-github-actions.sh h2oai "2026-05-11 19:15" "2026-05-11 21:30"

# Review outputs
cat github-org-audit-h2oai-*/00-MASTER-SUMMARY.txt
cat github-org-audit-h2oai-*/00-CRITICAL-FINDINGS.txt
```

**IOC Detection Patterns:**
- TanStack-specific: `getsession.org`, `router_init.js`, malicious `@tanstack` versions
- Token exfiltration: `NPM_TOKEN`, `GITHUB_TOKEN`, `AWS_*_KEY` with curl/wget
- Registry manipulation: `npm config set registry`
- Code execution: base64 decode, eval patterns

### Threat Landscape 2023 Layers/
MITRE ATT&CK Enterprise framework mappings for APT groups and campaigns.

**Format:** JSON files containing technique mappings for threat actors
- `G####-enterprise-layer.json` - APT group profiles (e.g., G0016 = APT29)
- `C####-enterprise-layer.json` - Campaign-specific TTPs

**Usage:** Import into MITRE ATT&CK Navigator for threat modeling and detection gap analysis.

### docs/security-alerts/
Security architecture designs and implementation specifications.

**vpc-flow-logs-waf-automation.md:**
- Comprehensive security monitoring design using VPC Flow Logs + AWS WAF
- 10 threat detection scenarios (port scanning, brute force, DDoS, geo-blocking, etc.)
- Automated IP blocking with configurable block durations
- Integration patterns: CloudWatch Logs, Coralogix, EventBridge, Lambda

## Common Commands

### Supply Chain Audit (Post-Incident)
```bash
# Audit entire organization for incident window
cd .github/Playbook/Supply\ Chain/Github/
./audit-org-github-actions.sh <org-name> "<start-time>" "<end-time>"

# Example: TanStack incident response
./audit-org-github-actions.sh h2oai "2026-05-11 19:15" "2026-05-11 21:30"

# Audit single repository with deep scan
./audit-github-actions.sh <org/repo> "<start-time>" "<end-time>"
```

### Enterprise Security Gate Deployment
```bash
# Initial deployment
cd enterprise-security-governance/terraform
terraform init
terraform plan -var-file=terraform.tfvars.local
terraform apply -var-file=terraform.tfvars.local

# Update policy configuration
terraform apply -var-file=terraform.tfvars.local -var="max_package_age_days=14"

# Bulk remediate missing lockfiles
gh workflow run bulk-lockfile-generator.yml \
  -f organization=h2oai \
  -f dry_run=true \
  -f max_repos=10
```

### Testing Security Scripts

**Local Testing (Hub Logic):**
```bash
# Test dependency age gate locally against a repository
cd enterprise-security-governance/
export WORKSPACE_PATH=/path/to/test-repo
python3 scripts/dependency_age_gate.py

# Run unit tests
cd tests/
python3 -m pytest test_age_gate.py -v

# Validate policies
python3 -c "import json; json.load(open('policies/allowlist.json'))"

# Quick test script
./quick-test.sh /path/to/test-repo
```

**Integration Testing (Hub-and-Spoke):**
```bash
# 1. Push hub repository
git push origin main

# 2. Deploy spoke workflow to one test repository
cd /path/to/test-repo
mkdir -p .github/workflows
curl -o .github/workflows/security-gate.yml \
  https://raw.githubusercontent.com/h2oai/enterprise-security-governance/main/templates/.github-workflows-security-gate.yml
git add .github/workflows/security-gate.yml
git commit -m "test: Add security gate workflow"
git push

# 3. Create test PR with recent package
# Edit package-lock.json to add package published < 7 days ago
git checkout -b test/security-gate
# ... make changes ...
git push origin test/security-gate
gh pr create --title "Test: Security gate" --body "Testing package age validation"

# 4. Verify check appears on PR
gh pr checks

# Expected output:
# ✅ Dependency review (GitHub built-in)
# ❌ Enforce 7-Day Package Maturation Policy (OUR gate)
```

**Bulk Testing (Dry Run):**
```bash
# Test bulk deployment without creating PRs
gh workflow run bulk-lockfile-generator.yml \
  -f organization=h2oai \
  -f dry_run=true \
  -f max_repos=5

# Review workflow logs
gh run list --workflow=bulk-lockfile-generator.yml
gh run view <run-id> --log
```

## Architecture Patterns

### Hub-and-Spoke Architecture

**Concept:** Single source of truth for security logic
```
Hub (HiveBait/momo repository)                    ← Configurable repository name
└── enterprise-security-governance/               ← Fixed subdirectory path
    ├── .github/workflows/
    │   └── central-security-gate.yml            ← Reusable workflow
    ├── scripts/dependency_age_gate.py           ← Validation logic
    └── policies/allowlist.json                   ← Policy definitions

Spoke Repos (1,000+)
├── .github/workflows/security-gate.yml (23 lines)
└── Calls: uses: HiveBait/momo/.github/workflows/central-security-gate.yml@main
                  ^^^^^^^^^^^^
                  Hub repository name (update if renamed)
```

**Repository Name vs. Path:**
- **Repository name** (`momo`): Configurable, can be changed
- **Subdirectory path** (`enterprise-security-governance/`): Fixed, should not change
- **Workflow reference format:** `<org>/<hub-repo>/.github/workflows/central-security-gate.yml@main`

**Benefits:**
- ✅ Update once in hub → all spokes benefit automatically
- ✅ No logic duplication or drift across 1,000+ repositories
- ✅ Central audit trail in Coralogix
- ✅ Easy rollback: revert hub commit → all spokes use previous version
- ✅ Version control for security policy

**See:** `docs/HUB-SPOKE-ARCHITECTURE.md` for complete explanation and diagrams

---

### Four-Layer Supply Chain Defense

**Layer 0: Package Manager (Client-Side) - OPTIONAL**
- **Technology:** npm `min-release-age`, pnpm `minimumReleaseAge`, bun `minimumReleaseAge`, uv `exclude-newer`
- **Protects:** Developer workstation before code is written
- **Enforcement:** Blocks `npm install` / `uv pip install` for packages < 7 days old
- **Bypass:** Developer can override (this is Layer 0, convenience layer)
- **Files:** `.npmrc`, `bunfig.toml`, `pyproject.toml` (checked into Git)
- **Deployment:** Optional via bulk-lockfile-generator

**Layer 1: Dependabot Cooldown (Server-Side Prevention) - PRIMARY**
- **Technology:** GitHub Dependabot native `cooldown` feature
- **Protects:** Organization-wide, prevents PR creation at source
- **Enforcement:** Dependabot will NOT create PRs for packages < 7 days old
- **Bypass:** Cannot be bypassed (GitHub native enforcement)
- **Files:** `.github/dependabot.yml` in each spoke repository
- **Deployment:** Automated via bulk-lockfile-generator
- **Security Updates:** CVE patches automatically bypass cooldown (GitHub native)

**Layer 2: Security Gate (Server-Side Validation) - BACKUP**
- **Technology:** Hub-and-spoke reusable GitHub Actions workflow
- **Protects:** Manual PRs and edge cases (developers updating dependencies directly)
- **Enforcement:** Required status check, PR blocked if violations found
- **Bypass:** Cannot be bypassed (organization ruleset enforced)
- **Files:** Hub workflow + spoke caller workflow
- **Deployment:** Hub pushed once, spoke workflows deployed via bulk generator
- **Logic:** 410-line Python script with zero external dependencies

**Layer 3: Observability (SIEM Audit Trail)**
- **Technology:** Coralogix integration
- **Protects:** Audit trail for compliance and forensics
- **Enforcement:** Logging only (no blocking)
- **Files:** Telemetry shipped from central-security-gate.yml
- **Deployment:** Organization secret `CORALOGIX_API_KEY`

**Defense-in-Depth Rationale:**
- Layer 0: Developer convenience (catch early, before code written)
- Layer 1: Primary enforcement (prevents PR spam, cleanest UX)
- Layer 2: Backup validation (catches manual updates, Dependabot bypasses)
- Layer 3: Observability (audit trail, incident response, metrics)

---

### Post-Incident Response (Detective Controls)

**Audit Scripts:**
- Post-incident forensics via GitHub Actions logs
- Pattern matching for known IOCs (TanStack, Codecov, etc.)
- Workflow run timeline analysis
- Secret exposure detection

**Break-Glass Policy:**
- Time-limited exemptions via `allowlist.json`
- CODEOWNERS-enforced SecOps approval (2+ reviewers)
- Automatic expiration of overrides (max 30 days)
- Audit trail for compliance

**Integration Points:**
- Coralogix SIEM: All security gate events (pass/fail/exemptions)
- GitHub Security: SARIF upload, secret scanning alerts
- Terraform: Org/enterprise-level policy enforcement via GitHub provider

### Incident Response Workflow

```
Incident Detected → Run Audit Scripts → Analyze Findings → Rotate Secrets
                                              ↓
                         Generate Report → Block Artifacts → Update Policies
                                              ↓
                         Coralogix Dashboard → Trend Analysis → Lessons Learned
```

**Critical Timeframes:**
- T+0 to T+1h: Execute audit scripts, identify affected repos
- T+1 to T+4h: Rotate all exposed secrets (NPM_TOKEN, AWS credentials, GitHub PATs)
- T+4 to T+8h: Block malicious packages via emergency allowlist updates
- T+24h: Complete root cause analysis, update detection patterns

## Security Considerations

### When Adding New IOC Patterns

**Location:** `.github/Playbook/Supply Chain/Github/audit-github-actions.sh`

**Process:**
1. Research incident postmortem for unique indicators
2. Add grep patterns to `check_logs_for_suspicious_activity()` function
3. Balance sensitivity (catch attacks) vs. specificity (avoid false positives)
4. Test against known-good workflow logs before deployment
5. Document pattern rationale in comments

**Example Pattern Addition:**
```bash
# Check for new malicious registry pattern
if echo "$logs" | grep -i "registry.evil.com" > /dev/null; then
    echo "  [!] MALICIOUS REGISTRY: Evil registry detected (CVE-2026-XXXXX)" >> "$findings_file"
fi
```

### Break-Glass Exemption Guidelines

**When to Approve (`allowlist.json`):**
- ✅ Critical security patches (CVE with active exploitation)
- ✅ Zero-day vulnerability mitigations
- ✅ Time-sensitive business-critical dependencies
- ✅ Packages with verified maintainer identity and source

**When to Deny:**
- ❌ Convenience ("I want this feature now")
- ❌ Unclear package provenance
- ❌ Developer impatience
- ❌ Permanent exemptions without expiration

**Exemption Template:**
```json
{
  "package": "package-name",
  "version": "x.y.z",
  "ecosystem": "npm|pypi|go",
  "reason": "CVE-YYYY-XXXXX: Critical remote code execution (CVSS 9.8)",
  "requested_by": "engineer@h2o.ai",
  "approved_by": "secops-lead@h2o.ai",
  "created_at": "2026-MM-DDTHH:mm:ssZ",
  "expires_at": "2026-MM-DDTHH:mm:ssZ",  # Max 30 days
  "jira_ticket": "SEC-NNNN"
}
```

### Modifying Security Gate Logic

**File:** `enterprise-security-governance/scripts/dependency_age_gate.py`

**Critical Sections (Do Not Modify Without Review):**
- `AGE_THRESHOLD_DAYS`: Policy constant (change via Terraform variable instead)
- `REGISTRY_CACHE`: Performance optimization (prevents rate limiting)
- Registry query functions (`get_npm_publish_date`, etc.): Handle API changes carefully

**Safe to Modify:**
- `INTERNAL_PACKAGE_PATTERNS`: Add organization-specific package scopes
- Parser functions: Extend for new lockfile formats (Cargo.lock, etc.)
- Violation output formatting: Customize for organization needs

**Testing Requirements:**
- Unit tests must pass: `pytest tests/test_age_gate.py`
- Lint checks: `flake8 scripts/` and `black --check scripts/`
- Manual smoke test against real lockfiles

## Key Files and Locations

### Files Requiring Updates if Hub Repository is Renamed

**IMPORTANT:** If the hub repository name changes from `momo` to something else, update these files:

1. **Root-level bulk deployment workflow:**
   - File: `.github/workflows/bulk-lockfile-generator.yml`
   - Line ~71: `repository: ${{ inputs.organization }}/momo`
   - Line ~73: `token: ${{ secrets.REPO_ACCESS_TOKEN || secrets.GITHUB_TOKEN }}`
   - Update `momo` to new repository name

2. **Subdirectory bulk deployment workflow:**
   - File: `enterprise-security-governance/.github/workflows/bulk-lockfile-generator.yml`
   - Line ~71: `repository: ${{ inputs.organization }}/momo`
   - Update `momo` to new repository name

3. **Spoke workflow template:**
   - File: `enterprise-security-governance/templates/.github-workflows-security-gate.yml`
   - Line referencing: `uses: HiveBait/momo/.github/workflows/central-security-gate.yml@main`
   - Update `HiveBait/momo` to `<org>/<new-repo-name>`

4. **All deployed spoke repositories:**
   - Each spoke's `.github/workflows/security-gate.yml`
   - Must be redeployed via bulk-lockfile-generator or manually updated

5. **Documentation:**
   - `CLAUDE.md` (this file)
   - `README.md` files
   - Any references to `HiveBait/momo` or example URLs

**Path that stays constant:** `enterprise-security-governance/` subdirectory structure

---

### Hub Repository (enterprise-security-governance/)

**Core Workflows:**
- `.github/workflows/central-security-gate.yml` - Reusable workflow (hub logic)
- `.github/workflows/bulk-lockfile-generator.yml` - Automated deployment to spokes
- `.github/workflows/secops-ci.yml` - CI for security scripts (linting, testing)

**Security Scripts:**
- `scripts/dependency_age_gate.py` - Validation engine (410 lines, Python stdlib only)
- `tests/test_age_gate.py` - Unit tests for validation logic
- `quick-test.sh` - Local testing script

**Templates (Deployed to Spokes):**
- `templates/.github-workflows-security-gate.yml` - Spoke workflow template (23 lines)
- `templates/.npmrc` - npm/pnpm client-side protection (Layer 0)
- `templates/.bunfig.toml` - bun client-side protection (Layer 0)
- `templates/uv.toml` - Python/uv client-side protection (Layer 0)
- `templates/pnpm-config.sh` - pnpm setup script

**Policy & Infrastructure:**
- `policies/allowlist.json` - Break-glass exemptions (requires 2+ SecOps approvals)
- `.github/CODEOWNERS` - Approval authority restrictions
- `.github/dependabot.yml` - Template with native cooldown configuration
- `terraform/main.tf` - Organization-wide ruleset definitions
- `terraform/enterprise.tf` - Enterprise-level ruleset definitions (all orgs)
- `terraform/variables.tf` - Configuration schema
- `terraform/terraform.tfvars` - Organization-level config template
- `terraform/terraform.tfvars.enterprise` - Enterprise-level config template

**Documentation:**
- `README.md` - Framework operations guide
- `ARCHITECTURE.md` - Complete system design
- `SUMMARY.md` - Deployment options and success metrics
- `TESTING.md` - How to test locally and in CI
- `docs/HUB-SPOKE-ARCHITECTURE.md` - Hub-and-spoke explanation with diagrams
- `docs/ENTERPRISE-DEPLOYMENT.md` - Enterprise vs organization deployment guide
- `docs/CLIENT-SIDE-PROTECTION.md` - Layer 0 documentation (package manager configs)
- `docs/DEPENDABOT-INTEGRATION.md` - Native cooldown feature documentation
- `docs/NATIVE-COOLDOWN-MIGRATION.md` - Migration guide from custom detection
- `docs/GITHUB-FEATURE-REQUEST.md` - Feature request template (if cooldown didn't exist)

### Spoke Repositories (Deployed Files)

**Files deployed by bulk-lockfile-generator:**
- `.github/workflows/security-gate.yml` - Calls hub workflow (Layer 2)
- `.github/dependabot.yml` - Native cooldown config (Layer 1)
- `package-lock.json` / `uv.lock` / `go.sum` - Lockfiles (if missing)
- `.npmrc` / `bunfig.toml` - Client-side protection (Layer 0, optional)
- `pyproject.toml` - Updated with `[tool.uv]` section (Layer 0, optional)

### Incident Response
- `.github/Playbook/Supply Chain/Github/SUPPLY-CHAIN-AUDIT.md` - Incident response runbook
- `.github/Playbook/Supply Chain/Github/TANSTACK-IOCS.md` - Known IOC reference (TanStack incident)
- `.github/Playbook/Supply Chain/Github/audit-org-github-actions.sh` - Org-wide audit script
- `.github/Playbook/Supply Chain/Github/audit-github-actions.sh` - Single-repo audit script

### Threat Intelligence
- `Threat Landscape 2023.json` - Master MITRE ATT&CK layer
- `Threat Landscape 2023 Layers/*.json` - Individual APT group/campaign profiles

### Security Monitoring
- `docs/security-alerts/vpc-flow-logs-waf-automation.md` - AWS WAF automation architecture

## Integration with H2O Infrastructure

This security repository complements the main infrastructure repository:

**Cross-Repository Dependencies:**
- Supply chain audits target: `h2oai` GitHub organization (1,000+ repos)
- VPC flow log monitoring applies to: All production VPCs in HAMC accounts
- Security gates enforce policies across: All developer repositories with package managers

**Shared Services:**
- Coralogix: Centralized SIEM for all security events
- AWS Organizations: Multi-account security controls
- GitHub Enterprise: Organization-level policy enforcement

**Alert Routing:**
- Critical security findings → #security-team Slack channel
- Supply chain violations → PR comments + Coralogix alerts
- Infrastructure threats → SNS → PagerDuty → On-call security engineer

## Critical Concepts

### Hub-and-Spoke Workflow Execution

**IMPORTANT:** The security gate only runs if the spoke repository has the caller workflow file.

**Execution Flow:**
```
1. PR created in spoke repository (h2oai/api-gateway)
   └── Developer updates package-lock.json

2. Spoke workflow triggers
   └── File: .github/workflows/security-gate.yml
   └── Trigger: on.pull_request (lockfile modified)

3. Spoke workflow calls hub workflow
   └── uses: h2oai/enterprise-security-governance/.github/workflows/central-security-gate.yml@main

4. Hub workflow executes
   └── Checks out spoke repo
   └── Checks out hub repo
   └── Runs: python3 scripts/dependency_age_gate.py
   └── Returns: exit 0 (pass) or exit 1 (fail)

5. GitHub marks PR check
   └── ✅ "Enforce 7-Day Package Maturation Policy" = PASS
   └── OR
   └── ❌ "Enforce 7-Day Package Maturation Policy" = FAIL

6. Branch protection enforces
   └── Merge button enabled/disabled based on check status
```

**Common Mistake:** Assuming security gate runs automatically
- ❌ **Wrong:** Security gate runs on all PRs automatically (like Dependabot review)
- ✅ **Correct:** Security gate only runs if `.github/workflows/security-gate.yml` exists in spoke repo

**Deployment:** Use bulk-lockfile-generator to deploy spoke workflow files to all repositories.

---

### No Lockfile = Fail-Open (Configurable)

**Default Behavior:**
- Repository has `package.json` but NO `package-lock.json`
- Security gate: ✅ PASS (with warning)
- Rationale: Gradual migration, don't break existing workflows

**Strict Mode (Recommended After Bulk Remediation):**
```bash
# Set environment variable in workflow
ENFORCE_LOCKFILES=true

# Security gate behavior:
# - No lockfiles found: ❌ FAIL
# - Rationale: No lockfiles = cannot validate = security risk
```

**Why package.json alone is not checked:**
- Contains version ranges (`^2.0.0`, `~1.5.0`) not exact versions
- Cannot determine which exact version will be installed
- Lockfiles are required for deterministic validation

---

## Notes for Claude Code

### When Working with Security Scripts

1. **Preserve security boundaries:** Do not weaken validation logic without explicit approval
2. **Test thoroughly:** Security changes require unit tests + manual validation
3. **Document rationale:** All IOC patterns and policy changes need justification comments
4. **Follow approval flow:** Changes to `allowlist.json` and `dependency_age_gate.py` require SecOps review
5. **Hub-and-spoke updates:** Changes to hub workflows automatically propagate to all spokes (no spoke repo changes needed)

### When Responding to Incidents

1. **Use existing playbooks:** Start with `.github/Playbook/Supply Chain/Github/SUPPLY-CHAIN-AUDIT.md`
2. **Time-boxed response:** Follow T+0, T+1h, T+4h, T+24h timeline structure
3. **Evidence preservation:** Never modify audit outputs or logs during investigation
4. **Communication:** Update #security-team Slack channel with findings and actions

### When Adding New Security Capabilities

1. **Zero external dependencies:** Prefer Python standard library for portability
2. **Fail-safe defaults:** Security tools should fail-open to prevent blocking legitimate work (except ENFORCE_LOCKFILES mode)
3. **Comprehensive logging:** All decisions must be observable in Coralogix
4. **Terraform-first:** Infrastructure changes deployed via IaC, not manual clicks
5. **Hub-first:** Update hub repository, not individual spoke repositories

---

## Troubleshooting

### Issue: Security gate doesn't run on PR

**Symptoms:**
- PR only shows GitHub's built-in `Dependency review` check
- No `Enforce 7-Day Package Maturation Policy` check appears

**Cause:** Spoke repository missing `.github/workflows/security-gate.yml`

**Fix:**
```bash
cd spoke-repository
mkdir -p .github/workflows
curl -o .github/workflows/security-gate.yml \
  https://raw.githubusercontent.com/h2oai/enterprise-security-governance/main/templates/.github-workflows-security-gate.yml
git add .github/workflows/security-gate.yml
git commit -m "chore: Add security gate workflow"
git push
```

**Prevention:** Run bulk-lockfile-generator to deploy to all repositories

---

### Issue: Security gate passes but package is < 7 days old

**Symptoms:**
- Package published yesterday
- Security gate: ✅ PASS (should fail)

**Possible Causes:**

**Cause 1:** No lockfile in repository
- Check: Does `package-lock.json` / `uv.lock` / `go.sum` exist?
- Default: Fail-open (pass with warning)
- Fix: Generate lockfile via `npm install --package-lock-only` or bulk-lockfile-generator

**Cause 2:** Package is internal (excluded by pattern)
```python
INTERNAL_PACKAGE_PATTERNS = [
    r'^@h2oai/',
    r'^github\.com/h2oai/',
    r'^buf\.build/gen/go/h2oai/',
]
```
- Check: Does package match internal pattern?
- Fix: If incorrectly excluded, update pattern in `dependency_age_gate.py`

**Cause 3:** Package has break-glass exemption
- Check: `policies/allowlist.json` for active exemption
- Fix: Remove or wait for expiration

---

### Issue: "Workflow not found" error

**Symptoms:**
```
Error: h2oai/enterprise-security-governance/.github/workflows/central-security-gate.yml@main could not be found
```

**Cause:** Hub repository not pushed or workflow file missing

**Fix:**
```bash
# Verify hub workflow exists
gh api repos/h2oai/enterprise-security-governance/contents/.github/workflows/central-security-gate.yml

# If 404: Hub repository not set up correctly
cd enterprise-security-governance
git push origin main
```

---

### Issue: "Secret not found: CORALOGIX_API_KEY"

**Symptoms:**
```
Error: Secret CORALOGIX_API_KEY is required but not found
```

**Cause:** Organization secret not configured

**Fix (via GitHub UI):**
1. Go to: `https://github.com/organizations/h2oai/settings/secrets/actions`
2. New organization secret
3. Name: `CORALOGIX_API_KEY`
4. Value: `<your-api-key>`
5. Repository access: **All repositories**

**Fix (via Terraform):**
```bash
cd enterprise-security-governance/terraform
terraform apply -var-file=terraform.tfvars.local
```

---

### Issue: Hub logic update not applying to spokes

**Symptoms:**
- Updated `dependency_age_gate.py` in hub
- Spokes still use old logic

**Cause:** Spokes pinned to old version

**Check spoke workflow:**
```yaml
# If pinned to specific version:
uses: h2oai/enterprise-security-governance/.github/workflows/central-security-gate.yml@v1.0.0

# Should use latest:
uses: h2oai/enterprise-security-governance/.github/workflows/central-security-gate.yml@main
```

**Fix:** Update spoke workflows to reference `@main` instead of version tag

---

### Issue: False positive - legitimate package blocked

**Symptoms:**
- Package is from trusted source
- Published < 7 days ago
- Business-critical need

**Solution:** Add break-glass exemption

```bash
cd enterprise-security-governance
vim policies/allowlist.json

# Add:
{
  "exemptions": [
    {
      "package": "package-name",
      "version": "x.y.z",
      "ecosystem": "npm",
      "reason": "CVE-YYYY-XXXXX: Critical security patch",
      "requested_by": "engineer@h2o.ai",
      "approved_by": "secops@h2o.ai",
      "created_at": "2026-05-27T00:00:00Z",
      "expires_at": "2026-06-26T00:00:00Z",
      "jira_ticket": "SEC-1234"
    }
  ]
}

git add policies/allowlist.json
git commit -m "chore: Add break-glass exemption for package-name"
git push

# Requires 2+ SecOps approvals via CODEOWNERS
# Re-run failed PR check after merge
```
