# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**public-cloud-security** - Centralized security tooling, threat intelligence, and incident response playbooks for H2O.ai's multi-cloud infrastructure. Houses supply chain security frameworks, APT threat modeling, and automated security monitoring solutions.

## Repository Structure

### enterprise-security-governance/
Complete zero-cost supply chain security enforcement framework for GitHub Enterprise organizations.

**Purpose:** Centralized policy hub that enforces 7-day package maturation gates across 1,000+ developer repositories without modifying their workflows.

**Key Components:**
- `scripts/dependency_age_gate.py` - Multi-language (npm, PyPI, Go) dependency age validator using only Python standard library
- `.github/workflows/central-security-gate.yml` - Required security gate workflow with Coralogix SIEM integration
- `.github/workflows/bulk-lockfile-generator.yml` - Automated lockfile remediation for legacy repos
- `policies/allowlist.json` - Break-glass exemption policy for emergency overrides
- `terraform/` - Infrastructure-as-code for GitHub org-level security policies and rulesets

**Deployment:**
```bash
cd enterprise-security-governance/terraform
export TF_VAR_coralogix_api_key="your-key"
export GITHUB_TOKEN="your-pat"
terraform init
terraform apply -var-file=terraform.tfvars.local
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
./audit-org-github-actions.sh HiveBait "2026-05-11 19:15" "2026-05-11 21:30"

# Review outputs
cat github-org-audit-HiveBait-*/00-MASTER-SUMMARY.txt
cat github-org-audit-HiveBait-*/00-CRITICAL-FINDINGS.txt
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
./audit-org-github-actions.sh HiveBait "2026-05-11 19:15" "2026-05-11 21:30"

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
  -f organization=HiveBait \
  -f dry_run=true \
  -f max_repos=10
```

### Testing Security Scripts
```bash
# Test dependency age gate locally
cd enterprise-security-governance/
python3 scripts/dependency_age_gate.py

# Run unit tests
cd tests/
python3 -m pytest test_age_gate.py -v

# Validate policies
python3 -c "import json; json.load(open('policies/allowlist.json'))"
```

## Architecture Patterns

### Supply Chain Security Defense-in-Depth

**Layer 1: Preventive (Enterprise Security Gate)**
- 7-day package maturation policy enforced at PR time
- Zero-dependency Python validator (no attack surface)
- Multi-registry support (npm, PyPI, Go proxy)
- Organization-level GitHub rulesets (required status checks)

**Layer 2: Detective (Audit Scripts)**
- Post-incident forensics via GitHub Actions logs
- Pattern matching for known IOCs (TanStack, Codecov, etc.)
- Workflow run timeline analysis
- Secret exposure detection

**Layer 3: Response (Break-Glass Policy)**
- Time-limited exemptions via `allowlist.json`
- CODEOWNERS-enforced SecOps approval
- Automatic expiration of overrides
- Audit trail for compliance

**Integration Points:**
- Coralogix SIEM: All security gate events shipped via `coralogix/github-actions-integration@v1`
- GitHub Security: SARIF upload, secret scanning alerts
- Terraform: Org-level policy enforcement via GitHub provider

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

### Security Policy Enforcement
- `enterprise-security-governance/policies/allowlist.json` - Break-glass exemptions (requires 2+ SecOps approvals)
- `enterprise-security-governance/.github/CODEOWNERS` - Approval authority restrictions
- `terraform/main.tf` - Organization-wide ruleset definitions

### Incident Response
- `.github/Playbook/Supply Chain/Github/SUPPLY-CHAIN-AUDIT.md` - Incident response runbook
- `.github/Playbook/Supply Chain/Github/TANSTACK-IOCS.md` - Known IOC reference (TanStack incident)

### Threat Intelligence
- `Threat Landscape 2023.json` - Master MITRE ATT&CK layer
- `Threat Landscape 2023 Layers/*.json` - Individual APT group/campaign profiles

### Documentation
- `docs/security-alerts/vpc-flow-logs-waf-automation.md` - Security monitoring architecture spec
- `enterprise-security-governance/README.md` - Framework deployment and operations guide

## Integration with H2O Infrastructure

This security repository complements the main infrastructure repository:

**Cross-Repository Dependencies:**
- Supply chain audits target: `HiveBait` GitHub organization (1,000+ repos)
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

## Notes for Claude Code

### When Working with Security Scripts

1. **Preserve security boundaries:** Do not weaken validation logic without explicit approval
2. **Test thoroughly:** Security changes require unit tests + manual validation
3. **Document rationale:** All IOC patterns and policy changes need justification comments
4. **Follow approval flow:** Changes to `allowlist.json` and `dependency_age_gate.py` require SecOps review

### When Responding to Incidents

1. **Use existing playbooks:** Start with `.github/Playbook/Supply Chain/Github/SUPPLY-CHAIN-AUDIT.md`
2. **Time-boxed response:** Follow T+0, T+1h, T+4h, T+24h timeline structure
3. **Evidence preservation:** Never modify audit outputs or logs during investigation
4. **Communication:** Update #security-team Slack channel with findings and actions

### When Adding New Security Capabilities

1. **Zero external dependencies:** Prefer Python standard library for portability
2. **Fail-safe defaults:** Security tools should fail-open to prevent blocking legitimate work
3. **Comprehensive logging:** All decisions must be observable in Coralogix
4. **Terraform-first:** Infrastructure changes deployed via IaC, not manual clicks
