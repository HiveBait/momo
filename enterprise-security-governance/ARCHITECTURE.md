# Enterprise Security Governance - Complete Architecture

## System Overview

**Multi-layered supply chain defense framework** combining GitHub native features with custom validation logic for comprehensive protection against malicious dependencies.

## Three-Layer Defense Architecture

### Layer 1: Prevention (Primary) - Dependabot Native Cooldown

**Purpose:** Prevent creation of PRs for immature packages

**Technology:** GitHub Dependabot `cooldown` configuration

**Location:** `.github/dependabot.yml` in each spoke repository

**Configuration:**
```yaml
cooldown:
  default-days: 7              # Standard maturation period
  semver-major-days: 14        # Extended for breaking changes
  semver-minor-days: 7         # Standard for features
  semver-patch-days: 3         # Reduced for bug fixes
```

**Behavior:**
- ⏸️ Dependabot queries package registry for publish timestamp
- ⏸️ If `publish_date + cooldown_days > now` → **SKIP PR creation**
- ✅ If `publish_date + cooldown_days ≤ now` → **CREATE PR**
- ✅ Security updates (CVE patches) **bypass cooldown automatically**

**Coverage:**
- npm (Node.js)
- pip (Python)
- gomod (Go)

**Advantages:**
- ✅ Zero PR spam (prevention at source)
- ✅ No failed workflow checks
- ✅ Better developer experience
- ✅ Native GitHub audit trail
- ✅ No custom code required
- ✅ Security patches flow immediately

---

### Layer 2: Backup Validation (Secondary) - Security Gate Workflow

**Purpose:** Catch manual dependency updates and edge cases

**Technology:** Required GitHub Actions workflow + Python script

**Location:** `enterprise-security-governance` repository

**Trigger:** Every pull request across all repositories (GitHub org ruleset)

**Logic Flow:**
```
1. PR created (manual or Dependabot missed by cooldown)
2. Organization ruleset triggers central-security-gate workflow
3. Workflow checks out:
   - Target repository (workspace/)
   - Security governance tools (security-tools/)
4. Python script scans lockfiles:
   - Queries npm/PyPI/Go registries for publish dates
   - Compares against 7-day threshold
   - Checks break-glass allowlist (policies/allowlist.json)
5. If violations:
   - Fail workflow (blocks merge)
   - Comment on PR with details
   - Ship event to Coralogix
6. If compliant:
   - Pass workflow (allows merge)
   - Ship success event to Coralogix
```

**Catches:**
- Manual `package.json` updates by developers
- Repositories without `dependabot.yml` configured
- Edge cases where Dependabot cooldown didn't apply
- Internal package exclusions (@HiveBait/*, buf.build/gen/go/HiveBait/*)

**Break-Glass Policy:**
- SecOps team can add exemptions to `policies/allowlist.json`
- Exemptions have expiration dates
- Requires CODEOWNERS approval (2+ SecOps)

---

### Layer 3: Deployment Automation - Bulk Lockfile Generator

**Purpose:** Deploy lockfiles + dependabot.yml to all repositories

**Technology:** GitHub Actions workflow

**Location:** `enterprise-security-governance/.github/workflows/bulk-lockfile-generator.yml`

**Trigger:** Manual (`workflow_dispatch`) or scheduled

**Process:**
```
1. Query GitHub org for all repositories
2. Filter:
   - Not archived
   - Primary language: JavaScript, TypeScript, Python, Go
3. For each repository:
   a. Check for missing lockfiles:
      - package-lock.json (npm)
      - uv.lock (Python)
   b. Check for missing .github/dependabot.yml
   c. If missing:
      - Clone repository
      - Generate lockfiles (npm install --package-lock-only, uv lock)
      - Copy dependabot.yml template
      - Create branch: security/compliance-lockfile-enforcement
      - Commit changes
      - Create PR with full context
4. Dry-run mode available for testing
```

**PR Content:**
- Generated lockfiles
- Dependabot cooldown configuration
- Explanation of security policies
- Documentation links

**Scale:** Handles 1,000+ repositories

---

## Data Flow

### Scenario 1: Dependabot Security Update (CVE Patch)

```
T+0h: CVE-2026-12345 published, affects golang.org/x/crypto@v0.51.0
T+1h: Maintainer publishes patch: golang.org/x/crypto@v0.52.0
T+2h: GitHub Security Advisory created
T+2h: Dependabot detects security update
      ├─ Checks: Is security update? ✅ YES
      ├─ Checks: cooldown elapsed? ⏩ BYPASS (security)
      └─ Action: CREATE PR immediately
T+3h: Security gate workflow runs
      ├─ Detects: Manual or Dependabot? → Dependabot
      ├─ Scans: Dependencies compliant? → Check registry
      └─ Result: ✅ PASS (or fail if < 2 days old)
T+4h: PR merged, vulnerability patched
```

### Scenario 2: Dependabot Feature Update

```
T+0h: react@18.3.0 published (feature update)
T+6h: Dependabot detects update
      ├─ Checks: Is security update? ❌ NO
      ├─ Checks: publish_date + 7 days > now? ✅ YES (too new)
      └─ Action: ⏸️ SKIP - wait until T+168h (7 days)
T+168h (7 days later): Dependabot checks again
      ├─ Checks: publish_date + 7 days > now? ❌ NO (mature)
      └─ Action: CREATE PR
T+168h+1m: Security gate workflow runs
      ├─ Scans: Dependencies compliant? ✅ YES (7 days old)
      └─ Result: ✅ PASS
T+170h: PR reviewed and merged
```

### Scenario 3: Manual Developer Update

```
T+0h: Developer manually updates package.json
      {
        "dependencies": {
          "lodash": "4.17.21" → "5.0.0"  // Published 3 days ago
        }
      }
T+0h+1m: Developer creates PR
T+0h+2m: Security gate workflow triggered
      ├─ Detects: Manual or Dependabot? → Manual
      ├─ Scans: lodash@5.0.0 publish date → 3 days ago
      ├─ Checks: 3 days < 7 days? ✅ VIOLATION
      └─ Action: ❌ FAIL workflow, block merge
T+0h+3m: PR comment posted:
      "Package lodash@5.0.0 published 3 days ago (minimum: 7 days)"
      "Options: Wait 4 more days or request break-glass exemption"
Developer options:
  A. Wait 4 days for package to mature
  B. Request exemption (file PR to allowlist.json)
  C. Rollback to older version
```

---

## Component Responsibilities

### enterprise-security-governance Repository

**Owns:**
- `.github/workflows/central-security-gate.yml` - Required workflow
- `.github/workflows/bulk-lockfile-generator.yml` - Deployment automation
- `scripts/dependency_age_gate.py` - Validation engine
- `policies/allowlist.json` - Break-glass exemptions
- `.github/dependabot.yml` - Template configuration
- `terraform/` - Infrastructure as code

**Does NOT own:**
- Individual spoke repository workflows
- Developer-created dependency updates
- Dependabot execution logic (GitHub native)

### Spoke Repositories (Developer Repos)

**Contains:**
- `.github/dependabot.yml` - Cooldown configuration (deployed by bulk generator)
- `package-lock.json`, `uv.lock`, `go.sum` - Dependency lockfiles
- Application code and dependencies

**Does NOT contain:**
- Custom security gate workflows (central only)
- Duplicate validation logic
- Security policy definitions

---

## Configuration Management

### Centralized Configuration

**Template location:** `enterprise-security-governance/.github/dependabot.yml`

**Deployment method:** Bulk lockfile generator workflow

**Update process:**
```bash
# 1. Update template in central repo
cd enterprise-security-governance
vim .github/dependabot.yml
git commit -m "Update cooldown to 14 days"
git push

# 2. Deploy to all repos
gh workflow run bulk-lockfile-generator.yml \
  -f organization=HiveBait \
  -f dry_run=false

# 3. Monitor rollout
# PRs created automatically in each spoke repo
```

**Consistency:** All repositories use identical cooldown policies

---

## Security Considerations

### Threat Model

**Protected Against:**
- ✅ Supply chain compromise (TanStack, event-stream style attacks)
- ✅ Typosquatting packages
- ✅ Malicious package updates (compromised maintainer accounts)
- ✅ Zero-day vulnerabilities in new packages

**Not Protected Against:**
- ❌ Vulnerabilities in old packages (use Dependabot security updates)
- ❌ Direct code injection via pull requests (use code review)
- ❌ Compromised CI/CD pipelines (separate security control)

### Trust Boundaries

**Layer 1 (Dependabot cooldown):**
- Trusts: GitHub's timestamp queries to registries
- Trusts: Registry publish dates (npm, PyPI, Go proxy)
- Does NOT trust: Package contents (scanned separately)

**Layer 2 (Security gate):**
- Trusts: Public registry APIs (npm, PyPI, Go)
- Trusts: Break-glass allowlist (SecOps controlled)
- Does NOT trust: Developer-claimed package safety

**Layer 3 (Bulk generator):**
- Trusts: GitHub repository metadata
- Trusts: Lockfile generation tools (npm, uv, go)
- Does NOT trust: Existing repository lockfiles (regenerates)

---

## Observability

### Metrics to Monitor

**Dependabot behavior:**
```sql
-- Coralogix query
application:dependabot
| stats count by action, repository
```

**Security gate results:**
```sql
-- Coralogix query
application:enterprise-security-governance
subsystem:supply-chain-gate
| stats count by gate_status, repository
```

**Key Performance Indicators:**
1. **PR Prevention Rate:** `(Dependabot skips / Total checks) * 100`
2. **False Positive Rate:** `(Allowlist exemptions / Total violations) * 100`
3. **Security Update Latency:** `Time from CVE publish to PR merge`
4. **Coverage:** `(Repos with dependabot.yml / Total repos) * 100`

### Alerts

**Alert 1: Excessive violations**
```
Condition: > 50 security gate failures in 24 hours
Action: Review for supply chain campaign
```

**Alert 2: Dependabot cooldown bypass spike**
```
Condition: > 20 security updates in 1 hour
Action: Verify legitimate CVE patches
```

**Alert 3: Break-glass exemption abuse**
```
Condition: > 10 allowlist additions in 7 days
Action: Audit exemption justifications
```

---

## Scalability

**Current capacity:**
- 1,000+ repositories supported
- ~5-10 PRs/hour during bulk deployment
- ~100 security gate validations/hour

**Bottlenecks:**
- GitHub API rate limits (5,000 requests/hour)
- Public registry API rate limits (npm: none, PyPI: ~100/min, Go: ~1000/min)
- Bulk generator execution time (~10-20 sec/repo)

**Optimization:**
- Caching: In-memory cache for duplicate packages
- Parallel execution: Bulk generator uses matrix strategy
- Rate limiting: Exponential backoff on registry queries

---

## Maintenance

**Weekly tasks:**
- Review active break-glass exemptions
- Expire outdated allowlist entries
- Monitor Coralogix dashboards

**Monthly tasks:**
- Review false positive rate
- Tune cooldown thresholds if needed
- Update internal package exclusion patterns

**Quarterly tasks:**
- Dependabot version updates
- Terraform provider updates
- Security policy review with engineering leadership

---

**Document Version:** 2.0 (Native Cooldown)  
**Last Updated:** 2026-05-25  
**Architecture Owner:** H2O.ai Security Team
