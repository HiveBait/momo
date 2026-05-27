# Client-Side Package Manager Protection

## Overview

Modern package managers (npm, pnpm, bun, uv) have native support for blocking packages based on their release age. This provides **Layer 0** defense - blocking at installation time before code even enters the repository.

## Four-Layer Defense Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 0: Package Manager (Client-Side) - NEW                │
│ • Blocks during local npm/pnpm/bun/uv install               │
│ • Developer can't even install package locally               │
│ • Protects developer workstation                             │
│ • CAN be bypassed (developer control)                        │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Dependabot Cooldown (Server-Side Prevention)       │
│ • GitHub prevents PR creation for immature packages          │
│ • Organization-wide enforcement                              │
│ • CANNOT be bypassed by individual developers                │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Security Gate Workflow (Validation)                │
│ • Validates PRs at merge time                                │
│ • Catches manual dependency updates                          │
│ • CANNOT be bypassed (required workflow)                     │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Observability (SIEM)                                │
│ • All events logged to Coralogix                             │
│ • Audit trail for compliance                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration by Package Manager

### npm (Node.js)

**Global configuration (all projects):**
```bash
npm config set min-release-age 7
```

**Per-project configuration:**
```bash
# In project root: .npmrc
min-release-age=7
save-exact=true
audit-level=moderate
```

**Test it:**
```bash
# Try to install a package published < 7 days ago
npm install very-new-package@1.0.0

# Expected output:
# npm ERR! Package 'very-new-package@1.0.0' was published 2 days ago
# npm ERR! Minimum release age is 7 days
```

**Documentation:** https://docs.npmjs.com/cli/v10/using-npm/config#min-release-age

---

### pnpm (Node.js alternative)

**Global configuration:**
```bash
# 10080 minutes = 7 days
pnpm config set minimumReleaseAge 10080
```

**Per-project configuration:**
```bash
# In project root: .npmrc (pnpm uses same file)
minimumReleaseAge=10080
```

**Test it:**
```bash
pnpm install very-new-package@1.0.0

# Expected output:
# ERR_PNPM_PACKAGE_TOO_NEW  Package was published 2880 minutes ago, minimum is 10080 minutes
```

**Documentation:** https://pnpm.io/cli/config#minimumreleaseage

---

### bun (Fast JavaScript runtime)

**Configuration file:**
```toml
# ~/.bunfig.toml (global) or ./bunfig.toml (per-project)
[install]
minimumReleaseAge = 604800  # 604800 seconds = 7 days
exact = true
```

**Test it:**
```bash
bun install very-new-package@1.0.0

# Expected output:
# error: Package 'very-new-package@1.0.0' was published 172800 seconds ago
# error: Minimum release age is 604800 seconds (7 days)
```

**Documentation:** https://bun.sh/docs/cli/bunfig#install-minimumreleaseage

---

### uv (Fast Python package installer)

**Global configuration:**
```toml
# ~/.config/uv/uv.toml
[tool.uv]
exclude-newer = "7days"  # Human-readable format!
prefer-binary = true
```

**Per-project configuration:**
```toml
# pyproject.toml
[tool.uv]
exclude-newer = "7days"
```

**Per-command usage:**
```bash
uv pip install --exclude-newer 7days requests

# Or other formats:
uv pip install --exclude-newer "2024-05-19" requests  # Specific date
uv pip install --exclude-newer "1 week ago" requests  # Relative
```

**Test it:**
```bash
uv pip install --exclude-newer 7days very-new-package==1.0.0

# Expected output:
# error: Package 'very-new-package==1.0.0' was uploaded 2 days ago
# error: Packages uploaded after 2024-05-19 are excluded
```

**Documentation:** https://docs.astral.sh/uv/configuration/files/#exclude-newer

---

## Deployment Strategy

### Option 1: Organization-Wide Mandate (User-Level Config)

Deploy configurations to all developer workstations:

**Setup script for developers:**
```bash
#!/bin/bash
# setup-supply-chain-protection.sh

echo "🛡️  Setting up supply chain protection..."

# npm
npm config set min-release-age 7
npm config set save-exact true
echo "✅ npm configured"

# pnpm (if installed)
if command -v pnpm &> /dev/null; then
    pnpm config set minimumReleaseAge 10080
    pnpm config set save-exact true
    echo "✅ pnpm configured"
fi

# bun (if installed)
if command -v bun &> /dev/null; then
    mkdir -p ~/.config/bun
    cat > ~/.bunfig.toml <<EOF
[install]
minimumReleaseAge = 604800
exact = true
EOF
    echo "✅ bun configured"
fi

# uv (if installed)
if command -v uv &> /dev/null; then
    mkdir -p ~/.config/uv
    cat > ~/.config/uv/uv.toml <<EOF
[tool.uv]
exclude-newer = "7days"
prefer-binary = true
EOF
    echo "✅ uv configured"
fi

echo ""
echo "🎉 Supply chain protection configured!"
echo "This will block packages published < 7 days ago"
```

**Distribute via:**
- Slack announcement + setup script
- Onboarding docs for new engineers
- IT provisioning scripts

---

### Option 2: Per-Repository Config (Enforced via Git)

Add config files to each repository:

```bash
# In bulk-lockfile-generator workflow:
# Deploy these files alongside lockfiles

.npmrc              # For npm/pnpm projects
bunfig.toml         # For bun projects
pyproject.toml      # For Python/uv projects (merge into existing)
```

**Advantages:**
- ✅ Version controlled (can't be accidentally deleted)
- ✅ Enforced across team (checked into Git)
- ✅ Works in CI/CD (not just developer machines)

**Disadvantages:**
- ❌ Developer can still override locally
- ❌ Requires updating 1,000+ repositories

---

## Benefits of Client-Side Protection

### 1. Catch Issues Earlier (Shift-Left Security)

**Without client-side protection:**
```
Day 1: Developer runs npm install new-package@1.0.0 (2 days old)
       ✅ Installs successfully
Day 1: Developer writes code using package
Day 2: Developer creates PR
Day 2: Security gate FAILS ❌
       Developer frustrated: "I already wrote code with this!"
       Must refactor or wait 5 more days
```

**With client-side protection:**
```
Day 1: Developer runs npm install new-package@1.0.0 (2 days old)
       ❌ ERROR: Package too new (< 7 days)
       Developer: "Oh, I'll use an older version or wait"
       No code written yet = no wasted effort
```

### 2. Defense Against Compromised Developer Machines

**Scenario:** Developer machine compromised by malware

```
Attacker: Modify package.json to add malicious-package@1.0.0
Attacker: Run npm install
npm: ❌ BLOCKED (package published 6 hours ago)
Attacker: Cannot install even on compromised machine
```

### 3. Protection During Dependencies-of-Dependencies

**Scenario:** Transitive dependency has new version

```
Developer: npm install react@18.3.0 (published 30 days ago)
npm: react@18.3.0 depends on scheduler@0.24.0 (published 2 days ago)
npm: ❌ BLOCKED (transitive dependency too new)
Developer: Cannot install until scheduler matures
```

**This catches supply chain attacks in deep dependency trees!**

---

## Limitations & Bypasses

### Developer Can Override

**npm:**
```bash
# Bypass for single install
npm install --min-release-age 0 some-package

# Bypass globally (remove config)
npm config delete min-release-age
```

**uv:**
```bash
# Bypass per-command
uv pip install --exclude-newer "1970-01-01" some-package
```

**Why this is OK:**
- Client-side is Layer 0 (developer convenience)
- Layers 1-2 (Dependabot + Security Gate) still block at PR time
- Observability (Layer 3) logs all attempts

### Configuration Drift

**Problem:** Developer reinstalls OS, loses config

**Solution:**
- Document in onboarding
- Periodic reminders via Slack
- Automated checks: "Is min-release-age configured?"

### CI/CD Must Also Configure

**GitHub Actions workflows need config too:**

```yaml
- name: Configure npm Supply Chain Protection
  run: |
    npm config set min-release-age 7
    
- name: Install Dependencies
  run: npm ci
```

**Or use per-project .npmrc (recommended):**
```yaml
# .npmrc is checked in, so npm ci automatically respects it
- name: Install Dependencies
  run: npm ci
```

---

## Monitoring & Compliance

### Check Developer Compliance

```bash
# Audit script: check-supply-chain-config.sh
#!/bin/bash

echo "Checking supply chain protection configuration..."

# npm
NPM_AGE=$(npm config get min-release-age)
if [ "$NPM_AGE" == "7" ]; then
    echo "✅ npm: min-release-age = 7"
else
    echo "❌ npm: min-release-age not configured (found: $NPM_AGE)"
fi

# pnpm
if command -v pnpm &> /dev/null; then
    PNPM_AGE=$(pnpm config get minimumReleaseAge)
    if [ "$PNPM_AGE" == "10080" ]; then
        echo "✅ pnpm: minimumReleaseAge = 10080"
    else
        echo "❌ pnpm: minimumReleaseAge not configured (found: $PNPM_AGE)"
    fi
fi

# uv
if [ -f ~/.config/uv/uv.toml ]; then
    if grep -q 'exclude-newer = "7days"' ~/.config/uv/uv.toml; then
        echo "✅ uv: exclude-newer = 7days"
    else
        echo "❌ uv: exclude-newer not configured"
    fi
else
    echo "⚠️  uv: config file not found"
fi
```

**Run quarterly:** Ask all developers to run check script and report results

---

## Recommendation

### Phase 1: Server-Side Only (Current)
- ✅ Deploy Dependabot cooldown (Layer 1)
- ✅ Deploy security gate (Layer 2)
- ✅ High enforcement, zero bypass

### Phase 2: Add Client-Side (Optional)
- 📋 Distribute setup script to developers
- 📋 Add .npmrc / bunfig.toml to repositories
- 📋 Developer convenience + defense-in-depth

**Priority:** Server-side (Layers 1-2) is mandatory. Client-side (Layer 0) is optional but recommended for better developer experience.

---

## FAQ

**Q: Can developer bypass client-side protection?**  
A: Yes, but Layers 1-2 (Dependabot + Security Gate) still enforce at PR time.

**Q: Does this slow down npm install?**  
A: Minimal (<1s) - just queries registry publish date from cache.

**Q: What if emergency patch needed?**  
A: Developer can bypass locally (`--min-release-age 0`), but PR still needs break-glass exemption.

**Q: Does this work with private registries?**  
A: Yes, as long as registry supports publish date queries (npm, Artifactory, Nexus all support it).

**Q: What about Yarn?**  
A: Yarn v1 doesn't support this. Yarn v4 (Berry) does not have native support yet. Use Layer 1-2 enforcement.

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-26  
**Maintained By:** H2O.ai Security Team
