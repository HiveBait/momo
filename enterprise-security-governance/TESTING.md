# Testing Guide: Single Repository Validation

This guide walks through testing the security gate on one repository before organization-wide deployment.

## Option 1: Local Testing (Fastest)

Test the age gate script against any repository without GitHub Actions.

### Step 1: Clone a Test Repository

```bash
# Clone any repo with dependencies
git clone https://github.com/HiveBait/your-test-repo /tmp/test-workspace
cd /tmp/test-workspace

# Or use an existing local repository
cd /path/to/your/test/repo
```

### Step 2: Run Age Gate Locally

```bash
# From the enterprise-security-governance directory
cd /Users/yogev/Repos/Security/public-cloud-security/enterprise-security-governance

# Test against the repository
python3 scripts/dependency_age_gate.py
```

### Step 3: Test with Custom Workspace Path

```bash
# Test against any directory
export WORKSPACE_PATH="/tmp/test-workspace"
python3 scripts/dependency_age_gate.py
```

### Expected Outputs

**If packages are compliant:**
```
================================================================================
🛡️  Enterprise Supply Chain Security Gate
================================================================================
🔍 Scanning workspace: /tmp/test-workspace
📅 Enforcing 7-day maturation policy (packages must be published before 2026-05-18)

📦 Found 245 npm packages in package-lock.json
🔎 Validating 245 total dependencies...

================================================================================
✅ SECURITY GATE PASSED: All dependencies comply with age policy
================================================================================
```

**If violations exist:**
```
================================================================================
❌ SECURITY GATE FAILED: 3 violations detected
================================================================================

❌ npm package 'some-new-package@1.0.0' published 2 days ago (minimum: 7 days)
❌ npm package 'another-package@2.1.5' published 5 days ago (minimum: 7 days)
❌ pypi package 'requests@3.0.0' published 1 days ago (minimum: 7 days)
```

---

## Option 2: GitHub Actions Workflow (Single Repo)

Test the full workflow integration without org-wide enforcement.

### Step 1: Create Test Workflow in Target Repository

In your test repository (e.g., `HiveBait/test-app`), create:

**.github/workflows/test-security-gate.yml**

```yaml
name: Test Security Gate

on:
  pull_request:
    branches: [main]
  workflow_dispatch:  # Manual trigger for testing

jobs:
  security-gate-test:
    name: Supply Chain Security Test
    runs-on: ubuntu-latest

    steps:
      # Checkout the repository being tested
      - name: Checkout Target Repository
        uses: actions/checkout@v4
        with:
          path: workspace

      # Checkout the security governance tools
      - name: Checkout Security Tools
        uses: actions/checkout@v4
        with:
          repository: HiveBait/enterprise-security-governance
          # For testing, use your branch or local repo
          ref: main
          path: security-tools
          # If testing before pushing to GitHub, use a local path:
          # repository: ${{ github.repository_owner }}/enterprise-security-governance

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run Security Gate
        working-directory: workspace
        env:
          WORKSPACE_PATH: ${{ github.workspace }}/workspace
        run: |
          python3 ${{ github.workspace }}/security-tools/scripts/dependency_age_gate.py

      # Optional: Add Coralogix integration for testing
      # - name: Ship to Coralogix (Optional)
      #   if: always()
      #   uses: coralogix/github-actions-integration@v1
      #   with:
      #     api-key: ${{ secrets.CORALOGIX_API_KEY }}
      #     application-name: 'security-gate-test'
      #     subsystem-name: 'test-repo'
```

### Step 2: Test the Workflow

```bash
# Push the workflow file
cd /path/to/your/test-repo
git add .github/workflows/test-security-gate.yml
git commit -m "test: Add security gate validation"
git push

# Trigger manually
gh workflow run test-security-gate.yml
gh run watch

# Or create a test PR
git checkout -b test/security-gate
# Make a change
git commit -m "test: trigger security gate"
git push origin test/security-gate
gh pr create --title "Test Security Gate" --body "Testing supply chain validation"
```

### Step 3: Review Results

```bash
# Check workflow logs
gh run view --log

# Look for the security gate output in the logs
```

---

## Option 3: Test with Mock Violations

Create intentional violations to verify detection works.

### Create Test Repository with Recent Package

```bash
# Create temporary test directory
mkdir -p /tmp/security-gate-test
cd /tmp/security-gate-test

# Initialize npm project with a very recent package
cat > package.json <<EOF
{
  "name": "security-gate-test",
  "version": "1.0.0",
  "dependencies": {
    "react": "18.2.0",
    "some-very-new-package": "latest"
  }
}
EOF

# Generate lockfile
npm install --package-lock-only

# Test the security gate
python3 /Users/yogev/Repos/Security/public-cloud-security/enterprise-security-governance/scripts/dependency_age_gate.py
```

### Expected Result
Should detect the recently published package and fail with specific violation details.

---

## Option 4: Test Allowlist Functionality

Verify break-glass exemptions work correctly.

### Step 1: Create Test Allowlist

```bash
cd /Users/yogev/Repos/Security/public-cloud-security/enterprise-security-governance

# Edit policies/allowlist.json
cat > policies/allowlist.json <<EOF
{
  "exemptions": [
    {
      "package": "test-package",
      "version": "1.0.0",
      "ecosystem": "npm",
      "reason": "Testing exemption functionality",
      "requested_by": "test@h2o.ai",
      "approved_by": "secops@h2o.ai",
      "created_at": "2026-05-25T00:00:00Z",
      "expires_at": "2026-12-31T00:00:00Z",
      "jira_ticket": "TEST-001"
    }
  ]
}
EOF
```

### Step 2: Test Against Repository with Exempted Package

```bash
# Run against test workspace
WORKSPACE_PATH=/tmp/test-workspace python3 scripts/dependency_age_gate.py

# Should see:
# ✅ Exemption active for test-package@1.0.0: Testing exemption functionality
```

---

## Option 5: Test with Existing H2O Repository

Use a real H2O repository for integration testing.

### Recommended Test Repositories

**Low-risk test candidates:**
- Internal tools/utilities (non-production)
- Documentation sites
- Example/demo applications
- Developer sandbox repos

**DO NOT test on:**
- Production customer-facing applications
- CI/CD infrastructure repos
- Critical internal services

### Testing Steps

```bash
# 1. Choose a test repository
TEST_REPO="HiveBait/internal-docs-site"

# 2. Clone it
git clone https://github.com/$TEST_REPO /tmp/test-repo
cd /tmp/test-repo

# 3. Run local validation
python3 /Users/yogev/Repos/Security/public-cloud-security/enterprise-security-governance/scripts/dependency_age_gate.py

# 4. If passes, create test PR with security workflow
# Add .github/workflows/test-security-gate.yml (from Option 2)
git checkout -b test/security-gate-validation
git add .github/workflows/test-security-gate.yml
git commit -m "test: Add security gate validation (testing)"
git push origin test/security-gate-validation

# 5. Create PR and observe
gh pr create --title "[TEST] Security Gate Validation" \
  --body "Testing enterprise security gate before org-wide rollout. Safe to close after validation."

# 6. Monitor the workflow
gh pr checks --watch
```

---

## Validation Checklist

Before deploying organization-wide, verify:

- [ ] **Script executes successfully** against repos with lockfiles
- [ ] **Detects violations** when packages are too new
- [ ] **Respects allowlist** exemptions correctly
- [ ] **Handles missing lockfiles** gracefully (warning, not failure)
- [ ] **Caching works** (duplicate packages not re-queried)
- [ ] **Internal packages excluded** (@HiveBait/, github.com/HiveBait/)
- [ ] **Workflow integrates** with GitHub Actions properly
- [ ] **Performance acceptable** (<2 minutes for typical repo)
- [ ] **Error messages clear** with remediation guidance
- [ ] **False positive rate** acceptable (<2%)

---

## Common Test Scenarios

### Scenario 1: Repository with Only Old Packages
**Expected:** ✅ Pass - all packages mature

### Scenario 2: Repository with Mix of Old and New
**Expected:** ❌ Fail - list only new packages

### Scenario 3: Repository with No Lockfiles
**Expected:** ⚠️ Warning - suggest running bulk-lockfile-generator

### Scenario 4: Repository with Only Internal Packages
**Expected:** ✅ Pass - all packages excluded

### Scenario 5: Repository with Allowlisted Package
**Expected:** ✅ Pass - exemption active message shown

---

## Troubleshooting Test Issues

### Issue: "No lockfiles found"
**Solution:**
```bash
# Generate lockfiles first
npm install --package-lock-only  # For Node.js
uv lock                           # For Python
go mod tidy                       # For Go
```

### Issue: Rate limiting from registries
**Solution:**
```bash
# Wait 1 minute between test runs
# Or test with smaller repos (fewer dependencies)
```

### Issue: Script can't find allowlist.json
**Solution:**
```bash
# Ensure you're running from the correct directory
cd enterprise-security-governance
python3 scripts/dependency_age_gate.py

# Or set explicit path
export ALLOWLIST_PATH="/full/path/to/policies/allowlist.json"
```

### Issue: Workflow can't find security-tools repo
**Solution:**
```yaml
# If testing before pushing to GitHub, use local files:
- name: Copy Security Tools
  run: |
    cp -r /path/to/local/enterprise-security-governance security-tools
```

---

## Performance Benchmarks

Typical execution times on H2O repositories:

| Repository Size | Dependencies | Execution Time |
|----------------|--------------|----------------|
| Small (< 50)   | 45           | ~10 seconds    |
| Medium (< 200) | 180          | ~30 seconds    |
| Large (< 500)  | 450          | ~90 seconds    |
| Very Large     | 1000+        | ~3 minutes     |

**Optimization tips:**
- Caching reduces duplicate lookups by 70-80%
- Parallel testing: Don't run multiple instances against same repo simultaneously
- Network: Cloud runners have better bandwidth to public registries

---

## Next Steps After Successful Testing

1. **Document findings** in test report
2. **Share results** with security team
3. **Identify false positives** and tune exclusions
4. **Update INTERNAL_PACKAGE_PATTERNS** if needed
5. **Proceed to Terraform deployment** for org-wide rollout

---

## Quick Test Script

Save this as `quick-test.sh` for rapid iteration:

```bash
#!/bin/bash
set -e

TEST_REPO="${1:-/tmp/test-workspace}"
SCRIPT_DIR="/Users/yogev/Repos/Security/public-cloud-security/enterprise-security-governance"

echo "Testing security gate against: $TEST_REPO"
cd "$TEST_REPO"

export WORKSPACE_PATH="$TEST_REPO"
python3 "$SCRIPT_DIR/scripts/dependency_age_gate.py"

echo ""
echo "✅ Test complete"
```

Usage:
```bash
chmod +x quick-test.sh
./quick-test.sh /path/to/test/repo
```
