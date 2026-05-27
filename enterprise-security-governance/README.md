# 🛡️ Enterprise Security Governance Framework

## Overview

Centralized, 100% open-source supply chain security enforcement system for GitHub Enterprise organizations managing 1,000+ developer repositories.

**Key Capabilities:**
- ✅ **Zero-cost tooling:** No commercial licenses required
- 🚫 **Non-invasive:** Enforces policies without modifying developer workflows
- 🔒 **7-day maturation gate:** Blocks packages published within 7 days (configurable)
- 🌍 **Multi-language support:** Node.js (npm), Python (PyPI), Go (proxy.golang.org)
- 📊 **SIEM integration:** Ships all security events to Coralogix
- 🔧 **Bulk remediation:** Automated lockfile generation for legacy repos

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 1: Prevention (Dependabot Native Cooldown) PRIMARY   │
│  • Blocks PR creation for packages < 7 days old              │
│  • Security updates bypass automatically (CVE patches)        │
│  • Configured via .github/dependabot.yml in each repo        │
│  • Zero custom code - GitHub native feature                  │
└──────────────────────────────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 2: Backup Validation (Security Gate) SECONDARY       │
│  • Catches manual dependency updates by developers           │
│  • Validates repos without dependabot.yml configured         │
│  • Enforces break-glass allowlist policy                     │
│  • Provides audit trail to Coralogix SIEM                    │
└──────────────────────────────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 3: Deployment Automation (Bulk Generator)             │
│  • Deploys lockfiles to repos missing them                   │
│  • Deploys dependabot.yml with cooldown configuration        │
│  • Creates compliance PRs automatically                       │
│  • Scales across 1,000+ repositories                          │
└──────────────────────────────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  Observability & Response                                     │
│  • Coralogix SIEM (all validation events logged)             │
│  • GitHub audit log (Dependabot behavior)                    │
│  • PR comments with remediation guidance                      │
│  • Automated incident response playbooks                      │
└──────────────────────────────────────────────────────────────┘
```

**Key Innovation:** Native `cooldown` feature prevents PR creation at the source, eliminating noise and improving developer experience.

---

## Quick Start

### Prerequisites

1. **GitHub Enterprise Cloud** organization with admin access
2. **Terraform ~> 1.10** installed
3. **Coralogix account** with API key
4. **GitHub Personal Access Token** (PAT) with `admin:org`, `repo`, `workflow` scopes

### Deployment Steps

#### 1. Clone and Configure

```bash
git clone https://github.com/HiveBait/enterprise-security-governance.git
cd enterprise-security-governance/terraform

# Copy and customize variables
cp terraform.tfvars terraform.tfvars.local
```

#### 2. Set Sensitive Variables

```bash
# Export Coralogix API key
export TF_VAR_coralogix_api_key="your-coralogix-api-key"

# Export GitHub token for Terraform provider
export GITHUB_TOKEN="ghp_YourPersonalAccessToken"
```

#### 3. Deploy Infrastructure

```bash
terraform init
terraform plan -var-file=terraform.tfvars.local
terraform apply -var-file=terraform.tfvars.local
```

#### 4. Verify Deployment

```bash
# Check organization secrets
gh api /orgs/HiveBait/actions/secrets

# Verify required workflow is active
gh api /orgs/HiveBait/rulesets | jq '.[] | select(.name == "supply-chain-security-gate")'
```

---

## Usage

### For Developers

Security gates run automatically on every pull request. No action required unless violations are detected.

**When a PR fails the security gate:**

1. Review workflow logs for specific package violations
2. **Option A (Recommended):** Wait for packages to mature 7 days
3. **Option B (Emergency only):** Request break-glass exemption (see below)

### For SecOps Team

#### Grant Break-Glass Exemption

When a legitimate emergency requires bypassing the age gate:

1. Create a PR to `policies/allowlist.json`:

```json
{
  "package": "critical-security-patch",
  "version": "1.0.5",
  "ecosystem": "npm",
  "reason": "CVE-2026-54321 requires immediate patching",
  "requested_by": "dev-team@h2o.ai",
  "approved_by": "secops@h2o.ai",
  "created_at": "2026-05-25T12:00:00Z",
  "expires_at": "2026-06-25T12:00:00Z",
  "jira_ticket": "SEC-9876"
}
```

2. Get 2+ SecOps approvals (enforced via CODEOWNERS)
3. Merge to `main` - exemption takes effect immediately

#### Run Bulk Lockfile Remediation

For organizations with legacy repos missing lockfiles:

```bash
# Via GitHub UI:
1. Navigate to: Actions → Bulk Lockfile Remediation
2. Click "Run workflow"
3. Configure:
   - Organization: HiveBait
   - Dry run: true (recommended first run)
   - Max repos: 10 (test batch)
4. Review generated PRs
5. Re-run with dry_run: false for production

# Via GitHub CLI:
gh workflow run bulk-lockfile-generator.yml \
  -f organization=HiveBait \
  -f dry_run=false \
  -f max_repos=0
```

---

## Configuration

### Adjusting Age Threshold

Edit `terraform/terraform.tfvars.local`:

```hcl
max_package_age_days = 14  # Increase to 14 days for stricter policy
```

Apply changes:

```bash
terraform apply -var-file=terraform.tfvars.local
```

### Internal Package Exclusions

Customize patterns in `scripts/dependency_age_gate.py`:

```python
INTERNAL_PACKAGE_PATTERNS = [
    r'^@HiveBait/',              # H2O.ai npm packages
    r'^github\.com/HiveBait/',   # H2O.ai Go modules
    r'^@yourcompany/',        # Add your organization scope
]
```

### Disable Enforcement (Emergency)

Temporarily disable organization-wide enforcement:

```hcl
# terraform/terraform.tfvars.local
enable_required_workflows = false
```

---

## Incident Response Playbooks

### Scenario 1: Supply Chain Compromise Detected

**Example:** TanStack-style incident where malicious packages published to public registries

**Response:**

1. **Immediate (T+0 to T+1 hour):**
   ```bash
   # Review all repos that pulled dependencies during incident window
   cd .github/Playbook/Supply\ Chain/Github/
   ./audit-org-github-actions.sh HiveBait "2026-05-11 19:15" "2026-05-11 21:30"
   
   # Review MASTER-SUMMARY.txt and CRITICAL-FINDINGS.txt
   ```

2. **Rotate Secrets (T+1 to T+4 hours):**
   ```bash
   # Rotate organization-level secrets
   gh secret set NPM_TOKEN --org HiveBait
   gh secret set GITHUB_TOKEN --org HiveBait
   
   # Rotate AWS credentials if exposed
   # Follow AWS credential rotation playbook
   ```

3. **Block Malicious Packages (T+4 to T+8 hours):**
   - Add emergency exemptions to `allowlist.json` for known-good versions
   - Create organization advisory for internal communication

### Scenario 2: False Positive (Legitimate Package Blocked)

**Response:**

1. Validate package legitimacy:
   ```bash
   # Check npm registry
   curl -s https://registry.npmjs.org/package-name | jq '.time'
   
   # Verify publisher identity
   npm view package-name
   
   # Check GitHub source repository
   ```

2. Grant temporary exemption (expires in 7 days):
   ```bash
   # Add to policies/allowlist.json with 7-day expiration
   # Package will auto-clear gate once it ages beyond threshold
   ```

### Scenario 3: Critical Security Patch Needed Urgently

**Response:**

1. Assess risk:
   - CVE severity score
   - Exploit availability
   - Current exposure

2. Grant time-limited exemption:
   ```json
   {
     "package": "vulnerable-package",
     "version": "1.2.3-security-patch",
     "reason": "CVE-2026-12345 (CVSS 9.8) - Active exploitation",
     "expires_at": "2026-06-01T00:00:00Z"
   }
   ```

3. Monitor package behavior:
   - Review package changelog
   - Check npm/PyPI download stats for anomalies
   - Verify source repository commit history

---

## Monitoring & Observability

### Coralogix Dashboards

All security gate events are automatically shipped to Coralogix:

**Key Metrics to Monitor:**

1. **Gate Pass Rate:** `security_gate.status:PASSED / total_runs`
2. **Violation Trends:** `security_gate.status:FAILED by ecosystem`
3. **Exemption Usage:** `allowlist.exemption.active_count`
4. **Response Time:** `security_gate.detection_to_block_latency`

**Sample Coralogix Query:**

```sql
application:enterprise-security-governance
subsystem:supply-chain-gate
security_gate.status:FAILED
| stats count by repository
| sort -count
```

### GitHub Insights

Track organization-wide compliance:

```bash
# List all failed security gate checks (last 30 days)
gh api /orgs/HiveBait/actions/runs \
  --jq '.workflow_runs[] | select(.name == "Central Security Gate") | select(.conclusion == "failure")'

# Count active exemptions
cat policies/allowlist.json | jq '.exemptions | length'
```

---

## Maintenance

### Weekly Tasks

- [ ] Review active exemptions in `policies/allowlist.json`
- [ ] Expire exemptions past their `expires_at` date
- [ ] Review Coralogix dashboard for violation trends

### Monthly Tasks

- [ ] Audit allowlist for unused exemptions
- [ ] Update internal package patterns if needed
- [ ] Review false positive rate and tune thresholds

### Quarterly Tasks

- [ ] Dependency updates for Python script (if standard library changes)
- [ ] Terraform provider version updates
- [ ] Security policy review with engineering leadership

---

## Testing

### Run Unit Tests Locally

```bash
cd tests/
python3 -m pytest test_age_gate.py -v
```

### Test Against Sample Repository

```bash
# Clone a test repo
git clone https://github.com/HiveBait/test-repo workspace

# Run age gate validation
cd workspace
python3 ../scripts/dependency_age_gate.py
```

### Simulate Workflow Execution

```bash
# Using act (GitHub Actions local runner)
act pull_request -W .github/workflows/central-security-gate.yml \
  -s CORALOGIX_API_KEY=test-key
```

---

## Troubleshooting

### Issue: Security gate not triggering on PRs

**Diagnosis:**
```bash
# Check if organization ruleset is active
gh api /orgs/HiveBait/rulesets | jq '.[] | select(.name == "supply-chain-security-gate")'
```

**Fix:**
- Verify `enable_required_workflows = true` in Terraform config
- Ensure repository is not in exclusion list
- Check if repository is archived

### Issue: Rate limiting from public registries

**Symptoms:** `⚠️ Warning: Could not fetch https://registry.npmjs.org/...`

**Fix:**
- The script includes retry logic and caching
- For extreme cases, implement local registry mirror

### Issue: Coralogix integration failing

**Diagnosis:**
```bash
# Verify secret is set
gh secret list --org HiveBait | grep CORALOGIX_API_KEY

# Check action version
gh api /repos/coralogix/github-actions-integration/releases/latest
```

**Fix:**
- Rotate Coralogix API key
- Update action version in workflow file

---

## FAQ

**Q: Can developers bypass the security gate?**
A: No. Only the SecOps team (via CODEOWNERS) can approve exemptions to `allowlist.json`.

**Q: What happens if a package registry is down?**
A: The age gate will log a warning and skip validation for that package (fail-open to prevent blocking deployments).

**Q: Do we scan transitive dependencies?**
A: Yes. All lockfiles include transitive dependencies, so the entire dependency tree is validated.

**Q: How do we handle private registries?**
A: Add patterns to `INTERNAL_PACKAGE_PATTERNS` to exclude private/internal packages from public registry checks.

**Q: Can we customize the age threshold per repository?**
A: Not currently. The threshold is organization-wide. Request an exemption for specific packages if needed.

**Q: What about security patches for old vulnerabilities?**
A: Security patches should be granted break-glass exemptions with justification (CVE number, severity).

---

## Architecture Decisions

### Why 7 days?

Based on analysis of supply chain compromise incidents:
- **TanStack incident:** Malicious package detected within 2-3 hours
- **Event-stream incident:** Malicious code introduced, detected after 2 days
- **UA-parser-js incident:** Compromised within hours, widespread detection after 1-2 days

**7 days provides:**
- Time for community detection
- npm security team response window
- Automated scanner coverage

### Why zero external dependencies?

**Rationale:**
- Reduces attack surface (no transitive dependencies to validate)
- Ensures reproducibility (Python standard library is stable)
- Fast execution (no `pip install` overhead)
- Portable (works on any Python 3.7+ runner)

### Why central repository vs. distributed workflows?

**Centralized benefits:**
- Single source of truth for security policy
- No workflow file pollution in 1,000+ repos
- Atomic policy updates (one PR to change all repos)
- Easier to audit and maintain

---

## Contributing

This repository is maintained by the H2O.ai Security Team. Contributions welcome via pull request.

**Contribution Guidelines:**
1. All changes require 2+ SecOps approvals (CODEOWNERS enforced)
2. Include unit tests for script changes
3. Update documentation for policy changes
4. Run `pre-commit run --all-files` before submitting

**Contact:**
- Slack: #security-team
- Email: secops@h2o.ai
- On-call: PagerDuty "Security Incidents" escalation

---

## License

This framework is 100% open-source, zero-license-cost.

**Components:**
- Python scripts: Python Standard Library (PSF License)
- GitHub Actions: GitHub-provided actions (MIT)
- Terraform: HashiCorp Terraform (MPL 2.0)
- Coralogix integration: Coralogix official action (Apache 2.0)

---

## References

- **TanStack Compromise:** https://tanstack.com/blog/npm-supply-chain-compromise-postmortem
- **GitHub Actions Security:** https://docs.github.com/en/actions/security-guides
- **SLSA Framework:** https://slsa.dev/
- **CISA Software Supply Chain Guidance:** https://www.cisa.gov/supply-chain

---

**Last Updated:** 2026-05-25  
**Framework Version:** 1.0.0  
**Maintained By:** H2O.ai Security Team
