# Enterprise-Level Deployment Guide

## Overview

GitHub Enterprise supports deploying rulesets at **two levels**:

| Level | Scope | Use Case |
|-------|-------|----------|
| **Organization** | Single GitHub organization (e.g., `HiveBait`) | Single organization, or testing before enterprise rollout |
| **Enterprise** | ALL organizations in enterprise | Multi-organization enterprises (HiveBait, HiveBait-labs, etc.) |

---

## Comparison: Organization vs Enterprise Level

### Organization-Level Deployment

**Pros:**
- ✅ Easier to test (limited blast radius)
- ✅ Faster approval process (org admin only)
- ✅ Gradual rollout (one org at a time)

**Cons:**
- ❌ Must deploy separately to each organization
- ❌ Policy drift between organizations
- ❌ No centralized management

**When to use:**
- Single-organization GitHub setup
- Pilot testing before enterprise rollout
- Organization-specific policies needed

**Terraform file:** `main.tf`

---

### Enterprise-Level Deployment (Recommended for H2O.ai)

**Pros:**
- ✅ Single deployment covers ALL organizations
- ✅ Consistent policy enforcement
- ✅ Centralized management and audit
- ✅ Cannot be overridden by org admins

**Cons:**
- ❌ Requires enterprise admin permissions
- ❌ Larger blast radius (all orgs affected)
- ❌ Slower approval process (enterprise governance)

**When to use:**
- Multi-organization GitHub Enterprise setup
- Need consistent security policies across all orgs
- Prevent org-level policy bypass

**Terraform file:** `enterprise.tf`

---

## How to Find Your Enterprise Slug

```bash
# Using GitHub CLI
gh api /user/enterprises --jq '.[].slug'

# Output example:
# HiveBait-enterprise
```

Or visit: `https://github.com/enterprises/<your-enterprise>/settings/profile`

---

## How to Find Enterprise Team ID

Enterprise-level bypass requires an **enterprise-level team**, not an org-level team.

```bash
# List enterprise teams
gh api /enterprises/<enterprise-slug>/teams

# Or use GitHub UI:
# https://github.com/enterprises/<enterprise>/teams
# Click on security team → Look for "Team ID" in settings
```

**Note:** If you don't have enterprise-level teams, you can use organization-level teams with the organization deployment instead.

---

## Deployment Steps: Enterprise-Level

### Step 1: Prepare Configuration

```bash
cd enterprise-security-governance/terraform

# Copy enterprise template
cp terraform.tfvars.enterprise terraform.tfvars.local

# Edit with your values
vim terraform.tfvars.local
```

**Required values:**
```hcl
enable_enterprise_level     = true
github_enterprise_slug      = "HiveBait-enterprise"
enterprise_security_team_id = 123456
hub_repository_id           = "R_kgDOABCDEF"
enforcement_mode            = "evaluate"  # Start with audit-only
```

### Step 2: Set Authentication

```bash
# GitHub PAT with enterprise admin permissions
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Coralogix API key
export TF_VAR_coralogix_api_key="your-coralogix-api-key"
```

**Required PAT scopes:**
- `admin:enterprise` - Manage enterprise rulesets
- `admin:org` - Manage organization secrets
- `repo` - Access repositories

### Step 3: Deploy (Audit Mode First)

```bash
terraform init
terraform plan -var-file=terraform.tfvars.local

# Review plan output carefully
# Verify it shows: "github_enterprise_organization_ruleset.supply_chain_security_enterprise[0]"

terraform apply -var-file=terraform.tfvars.local
```

### Step 4: Monitor and Validate

**Duration:** 7-14 days in `evaluate` mode

```bash
# Check audit logs in GitHub Enterprise
# https://github.com/enterprises/<enterprise>/settings/audit-log

# Search for: action:repository_ruleset.evaluate

# Analyze patterns:
# - How many PRs would be blocked?
# - Which repositories have violations?
# - False positive rate?
```

### Step 5: Activate Enforcement

After validation period:

```bash
# Edit terraform.tfvars.local
enforcement_mode = "active"

# Apply change
terraform apply -var-file=terraform.tfvars.local
```

---

## Testing Strategy

### Phase 1: Single Repository (Manual)

```bash
# Test on one repo first
cd /path/to/test-repo

# Add security gate workflow manually
mkdir -p .github/workflows
curl -o .github/workflows/security-gate.yml \
  https://raw.githubusercontent.com/HiveBait/enterprise-security-governance/main/.github/workflows/central-security-gate.yml

# Create test PR with dependency update
# Verify security gate runs and passes/fails correctly
```

### Phase 2: Single Organization (Terraform)

```bash
# Deploy to one org first
enable_enterprise_level = false  # Use organization-level
organization_name = "HiveBait-sandbox"

terraform apply -var-file=terraform.tfvars.local
```

### Phase 3: Enterprise-Wide (Terraform)

```bash
# Switch to enterprise-level after org testing
enable_enterprise_level = true
enforcement_mode = "evaluate"  # Start with audit-only

terraform apply -var-file=terraform.tfvars.local

# Monitor for 7-14 days → Switch to "active"
```

---

## Enforcement Mode Options

| Mode | Behavior | Use Case |
|------|----------|----------|
| **evaluate** | Audit logs only, PRs not blocked | Testing, monitoring false positives |
| **active** | PRs blocked if checks fail | Production enforcement |
| **disabled** | No checks, no audit logs | Emergency rollback |

**Transition timeline:**
```
evaluate (7-14 days) → active (ongoing) → disabled (emergency only)
```

---

## Architecture: Enterprise vs Organization

### Enterprise-Level Architecture

```
GitHub Enterprise (HiveBait-enterprise)
├── Enterprise Ruleset: supply-chain-security-gate
│   └── Applies to ALL organizations automatically
│
├── Organization: HiveBait
│   ├── Repo: api-gateway ✅ (ruleset applies)
│   ├── Repo: ml-platform ✅ (ruleset applies)
│   └── Repo: enterprise-security-governance ⏭️ (excluded)
│
├── Organization: HiveBait-labs
│   ├── Repo: experiment-tracker ✅ (ruleset applies)
│   └── Repo: research-tools ✅ (ruleset applies)
│
└── Organization: HiveBait-internal
    └── Repo: internal-docs ✅ (ruleset applies)
```

**Key Point:** One ruleset deployment → 3+ organizations covered

---

### Organization-Level Architecture

```
Organization: HiveBait
├── Organization Ruleset: supply-chain-security-gate
│   └── Applies to HiveBait repos only
│
├── Repo: api-gateway ✅ (ruleset applies)
└── Repo: ml-platform ✅ (ruleset applies)

Organization: HiveBait-labs
├── ❌ NO RULESET DEPLOYED
│
├── Repo: experiment-tracker ❌ (not protected)
└── Repo: research-tools ❌ (not protected)
```

**Key Point:** Must deploy separately to each organization

---

## Rollback Procedure

### Emergency Rollback (Immediate)

```bash
# Disable enforcement immediately
enforcement_mode = "disabled"

terraform apply -var-file=terraform.tfvars.local

# All PRs unblocked within 30 seconds
```

### Graceful Rollback (Planned)

```bash
# Step 1: Switch to audit-only
enforcement_mode = "evaluate"
terraform apply

# Step 2: Investigate issues (7 days)

# Step 3: Remove rulesets entirely
enable_enterprise_level = false
terraform apply
```

---

## Troubleshooting

### Issue: "Enterprise not found"

**Cause:** GitHub PAT lacks `admin:enterprise` scope

**Fix:**
```bash
# Create new PAT with enterprise admin scope
# https://github.com/settings/tokens/new
# Scopes: admin:enterprise, admin:org, repo
export GITHUB_TOKEN="ghp_NEW_TOKEN"
```

---

### Issue: "Team not found"

**Cause:** Using org-level team ID instead of enterprise-level team ID

**Fix:**
```bash
# Option 1: Get enterprise team ID
gh api /enterprises/<enterprise>/teams

# Option 2: Use organization-level deployment instead
enable_enterprise_level = false
```

---

### Issue: "Repository access denied"

**Cause:** Ruleset applies to archived or inaccessible repos

**Fix:**
```hcl
# Update exclusions in enterprise.tf
repository_name {
  exclude = [
    "enterprise-security-governance",
    "*.archived",
    "*.template",
    "inaccessible-repo-name"  # Add specific exclusions
  ]
}
```

---

## Monitoring and Audit

### View Enterprise Ruleset Activity

```bash
# GitHub UI
https://github.com/enterprises/<enterprise>/settings/rules

# API
gh api /enterprises/<enterprise>/rulesets

# Audit log
gh api /enterprises/<enterprise>/audit-log \
  --jq '.[] | select(.action | contains("repository_ruleset"))'
```

### Metrics to Track

**Week 1-2 (Evaluate Mode):**
- Total PRs scanned: `gh api /enterprises/<enterprise>/audit-log | grep repository_ruleset.evaluate | wc -l`
- Would-be blocked: Filter for `passed: false`
- False positive rate: Manual review of violations

**Week 3+ (Active Mode):**
- PRs blocked: `gh api /enterprises/<enterprise>/audit-log | grep repository_ruleset.rejected`
- Break-glass exemptions: Count allowlist.json updates
- Policy coverage: % of repos with lockfiles

---

## Cost Considerations

**GitHub Enterprise Cloud:**
- ✅ Enterprise rulesets: Included (no additional cost)
- ✅ Required workflows: Included
- ✅ Organization secrets: Included

**GitHub Actions Minutes:**
- Security gate workflow: ~30 seconds per PR
- Estimated: 5,000 PRs/month × 30s = 2,500 minutes/month
- Cost: Minimal (included in most GitHub plans)

---

## Success Criteria

**After 30 days:**
- ✅ 95%+ repositories covered by enterprise ruleset
- ✅ < 2% false positive rate
- ✅ Zero supply chain incidents from immature packages
- ✅ Security gate passes in < 1 minute average
- ✅ Break-glass process validated with < 5 exemptions/month

---

## Support

**Documentation:**
- GitHub Enterprise Rulesets: https://docs.github.com/en/enterprise-cloud@latest/admin/policies/enforcing-policies-for-your-enterprise/about-enterprise-policies
- Terraform GitHub Provider: https://registry.terraform.io/providers/integrations/github/latest/docs

**Contact:**
- Slack: #security-team
- Email: secops@h2o.ai
- GitHub: @HiveBait/security-team

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-26  
**Maintained By:** H2O.ai Security Team
