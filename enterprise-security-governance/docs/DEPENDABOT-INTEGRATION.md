# Dependabot Integration Guide

## Overview

Dependabot automatically creates PRs to update dependencies, often within hours of new releases. This creates a conflict with our 7-day maturation policy. This document explains how the security gate intelligently handles Dependabot updates.

## The Problem

```
Timeline:
─────────────────────────────────────────────────────────────
T+0h: golang.org/x/crypto v0.52.0 published (critical CVE patch)
T+2h: Dependabot detects update, creates PR
T+2h: Security gate runs... ❌ BLOCKS (package only 2 hours old)
```

**Without special handling:**
- ❌ Security patches would be blocked
- ❌ Defeats the purpose of automated security updates
- ❌ Forces manual exemption requests (slow)

## The Solution: Smart Thresholds

### Three-Tier Threshold System

| Context | Threshold | Rationale |
|---------|-----------|-----------|
| **Manual developer PR** | 7 days | Full supply chain protection |
| **Dependabot security update** | 2 days | Balance security vs. risk |
| **Dependabot feature update** | 7 days | Same as manual changes |

### Detection Logic

```python
# 1. Check if PR is from Dependabot
github_actor == "dependabot[bot]"

# 2. Check if it's a security update
PR has "security" label (Dependabot auto-adds for CVE fixes)

# 3. Apply appropriate threshold
if dependabot + security → 2 days
if dependabot + feature  → 7 days
if manual → 7 days
```

## How It Works

### Dependabot Security Update (CVE Fix)

```yaml
# Dependabot creates PR:
Title: "Bump golang.org/x/crypto from v0.51.0 to v0.52.0"
Labels: ["dependencies", "security", "go"]
Actor: dependabot[bot]
```

**Security Gate Behavior:**
```bash
🤖 Dependabot SECURITY update detected - using reduced 2-day threshold
📅 Enforcing 2-day maturation policy (packages must be published before 2026-05-23)

✅ Package published 3 days ago → PASS
```

### Dependabot Feature Update

```yaml
# Dependabot creates PR:
Title: "Bump react from 18.2.0 to 18.3.0"
Labels: ["dependencies", "javascript"]  # No "security" label
Actor: dependabot[bot]
```

**Security Gate Behavior:**
```bash
🤖 Dependabot feature update detected - using standard 7-day threshold
📅 Enforcing 7-day maturation policy (packages must be published before 2026-05-18)

❌ Package published 3 days ago → FAIL
```

### Manual Developer PR

```yaml
# Developer creates PR:
Title: "Update dependencies"
Actor: jane.developer
```

**Security Gate Behavior:**
```bash
📅 Enforcing standard 7-day maturation policy (packages must be published before 2026-05-18)

❌ Package published 3 days ago → FAIL
```

## Configuration

### Adjust Thresholds

Edit `scripts/dependency_age_gate.py`:

```python
# Configuration
AGE_THRESHOLD_DAYS = 7                      # Manual PRs
DEPENDABOT_SECURITY_THRESHOLD_DAYS = 2      # CVE patches
DEPENDABOT_FEATURE_THRESHOLD_DAYS = 7       # Feature updates
```

### Disable Dependabot Special Handling

To treat Dependabot the same as manual PRs:

```python
DEPENDABOT_SECURITY_THRESHOLD_DAYS = 7
DEPENDABOT_FEATURE_THRESHOLD_DAYS = 7
```

## Security Considerations

### Why 2 Days for Security Updates?

**Rationale:**
- ✅ Most supply chain attacks detected within 24-48 hours
- ✅ CVE patches often time-sensitive (active exploitation)
- ✅ Dependabot-created PRs are auditable (visible in PR log)
- ✅ 2 days allows community detection + npm security response

**Attack Timeline Analysis:**
- **TanStack compromise:** Detected within 3 hours
- **Event-stream:** Detected within 2 days
- **UA-parser-js:** Detected within 4 hours

**2-day window provides adequate protection while enabling rapid security response.**

### Audit Trail

All Dependabot threshold applications are logged to Coralogix:

```json
{
  "application": "enterprise-security-governance",
  "subsystem": "supply-chain-gate",
  "custom_fields": {
    "actor": "dependabot[bot]",
    "is_security_update": true,
    "threshold_applied": "2_days",
    "gate_status": "PASSED"
  }
}
```

### Monitoring Dependabot Bypasses

**Coralogix Query:**
```sql
application:enterprise-security-governance
subsystem:supply-chain-gate
custom_fields.actor:"dependabot[bot]"
custom_fields.threshold_applied:"2_days"
| stats count by repository, custom_fields.gate_status
```

**Alert if excessive bypasses:**
```
Alert: > 10 Dependabot security updates passed in 24 hours across org
Action: Review for potential supply chain campaign
```

## Testing Dependabot Handling

### Test 1: Manual PR (Standard Threshold)

```bash
# Create normal PR
git checkout -b feature/update-deps
# Update package.json
git commit -m "Update dependencies"
git push

# Security gate applies 7-day rule
```

### Test 2: Simulate Dependabot Security Update

```bash
# Set environment variables
export GITHUB_ACTOR="dependabot[bot]"
export GITHUB_EVENT_NAME="pull_request"

# Create mock event payload
cat > /tmp/github_event.json <<EOF
{
  "pull_request": {
    "labels": [
      {"name": "dependencies"},
      {"name": "security"},
      {"name": "go"}
    ]
  }
}
EOF

export GITHUB_EVENT_PATH="/tmp/github_event.json"

# Run security gate
python3 scripts/dependency_age_gate.py

# Should see: "🤖 Dependabot SECURITY update detected - using reduced 2-day threshold"
```

### Test 3: Simulate Dependabot Feature Update

```bash
# Same as above but remove "security" label
cat > /tmp/github_event.json <<EOF
{
  "pull_request": {
    "labels": [
      {"name": "dependencies"},
      {"name": "go"}
    ]
  }
}
EOF

export GITHUB_EVENT_PATH="/tmp/github_event.json"
python3 scripts/dependency_age_gate.py

# Should see: "🤖 Dependabot feature update detected - using standard 7-day threshold"
```

## Dependabot Configuration Best Practices

### Enable Security-Only Updates

**.github/dependabot.yml**
```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
    # Only open PRs for security updates
    open-pull-requests-limit: 10

  - package-ecosystem: "gomod"
    directory: "/"
    schedule:
      interval: "weekly"
    # Group non-security updates
    groups:
      production-dependencies:
        dependency-type: "production"
```

### Label Configuration

Dependabot automatically adds labels:
- `dependencies` - All dependency updates
- `security` - CVE patches (triggers reduced threshold)
- `<ecosystem>` - npm, go, python, etc.

**Do not remove the `security` label** - it's used by the security gate for threshold decisions.

## Troubleshooting

### Issue: Dependabot security update still blocked

**Diagnosis:**
```bash
# Check if "security" label present
gh pr view 123 --json labels

# Check GitHub event payload
cat $GITHUB_EVENT_PATH | jq '.pull_request.labels'
```

**Solution:**
- Verify Dependabot added "security" label
- Check if package was published within 2 days (still too new)
- Request break-glass exemption if critical

### Issue: False positive - not a security update but passed

**Diagnosis:**
```bash
# Check Coralogix logs
# Query for: actor:dependabot threshold_applied:2_days
```

**Solution:**
- Verify label detection logic
- Review GitHub event payload structure
- Update label matching in `is_dependabot_context()`

## Integration with GitHub Security

### Security Alerts Integration

Dependabot creates PRs based on:
1. **GitHub Security Alerts** (Dependabot alerts)
2. **Version updates** (scheduled checks)

**Only #1 gets "security" label** and reduced threshold.

### Workflow

```
GitHub Security Alert Detected
        ↓
Dependabot Creates PR (adds "security" label)
        ↓
Security Gate Runs (detects Dependabot + security)
        ↓
Applies 2-day threshold
        ↓
Package published 3 days ago → ✅ PASS
        ↓
Auto-merge (if configured)
```

## Recommendations

### For Security Team

1. **Monitor Dependabot bypasses weekly**
   - Query Coralogix for all 2-day threshold applications
   - Review for patterns or anomalies

2. **Tune thresholds quarterly**
   - Review false positive rate
   - Adjust based on supply chain threat landscape

3. **Alert on suspicious patterns**
   - Multiple Dependabot PRs in short window
   - Packages from new/unknown publishers
   - Unusual dependency chains

### For Developers

1. **Trust Dependabot for security updates**
   - They get reduced threshold for good reason
   - Still protected by 2-day maturation

2. **Use manual PRs for feature updates**
   - Full 7-day protection applies
   - Plan dependency updates in advance

3. **Request exemptions for critical cases**
   - Zero-day exploits
   - Active attacks in production
   - Business-critical hotfixes

---

**Last Updated:** 2026-05-25  
**Policy Version:** 1.1 (Dependabot integration)  
**Maintained By:** H2O.ai Security Team
