# GitHub Feature Request: Dependabot Package Maturation Cooldown

## Summary

Add native `cooldown` configuration to `.github/dependabot.yml` to enforce a maturation period for newly published packages before Dependabot creates update PRs.

## Problem Statement

Supply chain attacks often involve publishing malicious packages to public registries (npm, PyPI, Go proxy). Organizations need time for:
- Community detection of malicious packages
- Security scanner coverage
- Manual review by package maintainers

**Current limitation:** Dependabot immediately creates PRs for new packages, requiring downstream blocking via required workflows or manual review.

## Proposed Solution

### Configuration Schema

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
    cooldown:
      default-days: 7              # Global maturation period
      semver-major-days: 14        # Override for major versions
      semver-minor-days: 7         # Override for minor versions  
      semver-patch-days: 3         # Override for patches
      security-bypass: true        # Always true - security updates bypass cooldown
```

### Behavior

**Standard update (feature):**
```
1. Package published to npm: 2026-05-20
2. Dependabot checks: 2026-05-22 (2 days old)
3. Action: ⏸️ SKIP - package not yet 7 days old
4. Dependabot checks: 2026-05-27 (7 days old)
5. Action: ✅ CREATE PR - cooldown period satisfied
```

**Security update (CVE patch):**
```
1. CVE-2026-12345 published: 2026-05-20
2. GitHub Security Advisory detects: 2026-05-20
3. Dependabot checks: 2026-05-21 (1 day old)
4. Action: ✅ CREATE PR IMMEDIATELY - security-bypass active
```

## Benefits

### For GitHub Users

1. **Prevents PR spam** - No PRs created for packages too new
2. **Better developer experience** - Fewer failed required workflow checks
3. **Native supply chain protection** - Defense-in-depth at source

### For GitHub Enterprise

4. **Organizational policy enforcement** - Single config file controls maturation
5. **Compliance alignment** - Meets NIST, SLSA supply chain requirements
6. **Reduced API load** - Fewer PRs created = fewer webhook events

### For Security Teams

7. **Automated detection window** - Community has time to detect malicious packages
8. **Audit trail** - Clear logs of when packages became eligible
9. **Emergency override** - Security updates bypass automatically

## Real-World Use Cases

### Case 1: TanStack npm Compromise (May 2026)

**Timeline:**
- T+0h: Attacker publishes malicious @tanstack/query-core@5.61.0
- T+2h: Dependabot detects, creates 500 PRs across enterprise
- T+3h: Security team detects compromise, must manually close all PRs

**With cooldown:**
- T+0h: Attacker publishes malicious package
- T+2h: Dependabot skips (cooldown not satisfied)
- T+3h: Security team detects, package removed from registry
- Result: ✅ Zero PRs created, zero developer disruption

### Case 2: Critical CVE Patch

**Timeline:**
- T+0h: CVE-2026-54321 published (CVSS 9.8)
- T+1h: Maintainer publishes patch version
- T+2h: Dependabot creates PR (bypasses cooldown via security-bypass)
- T+3h: PR merged, vulnerability fixed

**With cooldown:**
- Same outcome - security updates bypass cooldown automatically

## Implementation Considerations

### Registry Query

Dependabot would need to query package publish timestamps:
- **npm:** `GET https://registry.npmjs.org/{package}` → `time[version]`
- **PyPI:** `GET https://pypi.org/pypi/{package}/{version}/json` → `urls[0].upload_time_iso_8601`
- **Go:** `GET https://proxy.golang.org/{module}/@v/{version}.info` → `Time`

### Caching Strategy

- Cache publish timestamps per package version
- Refresh cache daily during scheduled checks
- No additional API load beyond current Dependabot queries

### User Controls

```yaml
cooldown:
  enabled: true                    # Master switch
  default-days: 7                  # Global default
  security-bypass: true            # Always bypass for security (recommended)
  override-label: "bypass-cooldown" # Manual override via label
```

## Alternative Approaches Considered

### Approach 1: Required Workflows (Current State)

**Pros:** Available today, flexible logic
**Cons:** PRs created then blocked, developer friction, requires custom code

### Approach 2: Dependabot Ignore Rules

**Pros:** Native feature
**Cons:** Manual maintenance per package, no time-based logic

### Approach 3: Third-Party Bots

**Pros:** Feature-rich
**Cons:** Additional cost, external dependency, security risk

## Requested Priority

**High** - Supply chain attacks are increasing:
- TanStack compromise (May 2026)
- SolarWinds (2020)
- Event-stream (2018)
- UA-parser-js (2021)

Enterprises need native tooling to defend against this threat vector.

## References

- [SLSA Supply Chain Framework](https://slsa.dev/)
- [npm Security Best Practices](https://docs.npmjs.com/security-best-practices)
- [NIST SSDF Guidelines](https://csrc.nist.gov/Projects/ssdf)
- [TanStack Compromise Postmortem](https://tanstack.com/blog/npm-supply-chain-compromise-postmortem)

## GitHub Discussion Links

- Feature request: [To be created]
- Community feedback: [To be added]

---

**Submitted by:** H2O.ai Security Team  
**Date:** 2026-05-25  
**Priority:** High  
**Stakeholders:** Enterprise security teams, DevSecOps organizations
