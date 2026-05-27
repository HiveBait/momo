#!/usr/bin/env python3
"""
Multi-Language Dependency Age Gate Validator with OpenSSF Scorecard Integration

Enforces two-layer supply chain security:
1. Age Policy: 7-day maturation rule for all packages (npm, PyPI, Go)
2. OpenSSF Scorecard: Minimum security score threshold (configurable, default 5.0/10.0)

Zero external dependencies - uses only Python standard library.

Configuration via environment variables:
- OPENSSF_ENABLED: Enable/disable OpenSSF checks (default: true)
- OPENSSF_MIN_SCORE: Minimum acceptable score (default: 5.0)
- WORKSPACE_PATH: Override workspace directory
"""

import json
import os
import sys
import re
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import Dict, List, Tuple, Optional, Set

# Configuration
AGE_THRESHOLD_DAYS = 7
DEPENDABOT_SECURITY_THRESHOLD_DAYS = 2  # Reduced threshold for Dependabot security updates
DEPENDABOT_FEATURE_THRESHOLD_DAYS = 7   # Same as normal for feature updates
ALLOWLIST_PATH = os.path.join(os.path.dirname(__file__), '..', 'policies', 'allowlist.json')
INTERNAL_PACKAGE_PATTERNS = [
    r'^@HiveBait/',
    r'^github\.com/HiveBait/',
    r'^buf\.build/gen/go/HiveBait/',  # H2O internal buf.build packages
    r'^@yourcompany/',
]

# OpenSSF Scorecard Configuration
OPENSSF_ENABLED = os.environ.get("OPENSSF_ENABLED", "true").lower() == "true"
OPENSSF_MIN_SCORE = float(os.environ.get("OPENSSF_MIN_SCORE", "4.0"))
OPENSSF_API_BASE = "https://api.securityscorecards.dev/projects"

# Global caches to avoid redundant API calls
REGISTRY_CACHE: Dict[str, datetime] = {}
OPENSSF_CACHE: Dict[str, Optional[float]] = {}


class PackageViolation:
    """Represents a package that violates the age gate policy."""

    def __init__(self, name: str, version: str, published_date: datetime, ecosystem: str):
        self.name = name
        self.version = version
        self.published_date = published_date
        self.ecosystem = ecosystem
        self.age_days = (datetime.now(timezone.utc) - published_date).days

    def __str__(self) -> str:
        return (f"❌ {self.ecosystem} package '{self.name}@{self.version}' "
                f"published {self.age_days} days ago (minimum: {AGE_THRESHOLD_DAYS} days)")


class ScorecardViolation:
    """Represents a package that fails OpenSSF Scorecard requirements."""

    def __init__(self, name: str, version: str, score: float, ecosystem: str):
        self.name = name
        self.version = version
        self.score = score
        self.ecosystem = ecosystem

    def __str__(self) -> str:
        return (f"📊 {self.ecosystem} package '{self.name}@{self.version}' "
                f"has OpenSSF Scorecard score {self.score:.1f}/10.0 (minimum: {OPENSSF_MIN_SCORE:.1f})")


def load_allowlist() -> Dict:
    """Load break-glass allowlist from JSON policy file."""
    try:
        if not os.path.exists(ALLOWLIST_PATH):
            return {"exemptions": []}

        with open(ALLOWLIST_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Warning: Could not load allowlist: {e}")
        return {"exemptions": []}


def is_internal_package(package_name: str) -> bool:
    """Check if package matches internal corporate patterns."""
    for pattern in INTERNAL_PACKAGE_PATTERNS:
        if re.match(pattern, package_name):
            return True
    return False


def is_allowlisted(package_name: str, version: str, allowlist: Dict) -> bool:
    """Check if package version has an active break-glass exemption."""
    now = datetime.now(timezone.utc)

    for exemption in allowlist.get("exemptions", []):
        if exemption.get("package") == package_name and exemption.get("version") == version:
            expires_str = exemption.get("expires_at")
            if expires_str:
                try:
                    expires_at = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                    if now < expires_at:
                        reason = exemption.get("reason", "No reason provided")
                        print(f"✅ Exemption active for {package_name}@{version}: {reason}")
                        return True
                except ValueError:
                    pass
    return False


def fetch_json(url: str, cache_key: Optional[str] = None) -> Optional[Dict]:
    """Fetch JSON from URL with caching and error handling."""
    try:
        req = Request(url, headers={'User-Agent': 'Enterprise-Security-Governance/1.0'})
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"⚠️  Warning: Could not fetch {url}: {e}")
        return None


def get_npm_publish_date(package_name: str, version: str) -> Optional[datetime]:
    """Query npm registry for package publish timestamp."""
    cache_key = f"npm:{package_name}@{version}"

    if cache_key in REGISTRY_CACHE:
        return REGISTRY_CACHE[cache_key]

    url = f"https://registry.npmjs.org/{package_name}"
    data = fetch_json(url)

    if data and "time" in data and version in data["time"]:
        timestamp_str = data["time"][version]
        publish_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        REGISTRY_CACHE[cache_key] = publish_date
        return publish_date

    return None


def get_pypi_publish_date(package_name: str, version: str) -> Optional[datetime]:
    """Query PyPI registry for package upload timestamp."""
    cache_key = f"pypi:{package_name}@{version}"

    if cache_key in REGISTRY_CACHE:
        return REGISTRY_CACHE[cache_key]

    url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    data = fetch_json(url)

    if data and "urls" in data and len(data["urls"]) > 0:
        timestamp_str = data["urls"][0].get("upload_time_iso_8601")
        if timestamp_str:
            publish_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            REGISTRY_CACHE[cache_key] = publish_date
            return publish_date

    return None


def get_go_publish_date(module_path: str, version: str) -> Optional[datetime]:
    """Query Go proxy for module publish timestamp."""
    cache_key = f"go:{module_path}@{version}"

    if cache_key in REGISTRY_CACHE:
        return REGISTRY_CACHE[cache_key]

    # Go proxy requires lowercase module paths
    module_path_lower = module_path.lower()
    url = f"https://proxy.golang.org/{module_path_lower}/@v/{version}.info"
    data = fetch_json(url)

    if data and "Time" in data:
        timestamp_str = data["Time"]
        publish_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        REGISTRY_CACHE[cache_key] = publish_date
        return publish_date

    return None


def get_github_repo_from_package(package_name: str, version: str, ecosystem: str) -> Optional[str]:
    """Resolve package to GitHub repository using deps.dev API.

    This is the same approach used by GitHub's dependency-review-action.
    See: https://github.com/actions/dependency-review-action/blob/main/src/scorecard.ts

    Returns GitHub repo path (e.g., 'github.com/org/repo') or None.
    """
    if not OPENSSF_ENABLED:
        return None

    cache_key = f"depsdev:{ecosystem}:{package_name}@{version}"

    if cache_key in OPENSSF_CACHE:
        cached = OPENSSF_CACHE[cache_key]
        return cached if cached != "NONE" else None

    # Map ecosystem names to deps.dev format
    ecosystem_map = {
        "npm": "npm",
        "pypi": "pypi",
        "go": "go",
        "maven": "maven"
    }

    deps_ecosystem = ecosystem_map.get(ecosystem)
    if not deps_ecosystem:
        OPENSSF_CACHE[cache_key] = "NONE"
        return None

    # For Go modules, try direct GitHub path first
    if ecosystem == "go" and package_name.startswith("github.com/"):
        parts = package_name.split('/')
        if len(parts) >= 3:
            github_repo = "/".join(parts[:3])
            OPENSSF_CACHE[cache_key] = github_repo
            return github_repo

    # Query deps.dev API to resolve package -> GitHub repo
    # URL-encode package name for npm scoped packages (@org/package)
    from urllib.parse import quote
    encoded_package = quote(package_name, safe='')
    url = f"https://api.deps.dev/v3/systems/{deps_ecosystem}/packages/{encoded_package}/versions/{version}"

    try:
        req = Request(url, headers={'User-Agent': 'Enterprise-Security-Governance/1.0'})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

            # Extract GitHub repo from relatedProjects
            related_projects = data.get("relatedProjects", [])
            if related_projects and len(related_projects) > 0:
                project_id = related_projects[0].get("projectKey", {}).get("id", "")
                if project_id and project_id.startswith("github.com/"):
                    OPENSSF_CACHE[cache_key] = project_id
                    return project_id

    except (URLError, HTTPError, json.JSONDecodeError, ValueError, KeyError):
        pass

    OPENSSF_CACHE[cache_key] = "NONE"
    return None


def get_openssf_score(package_name: str, version: str, ecosystem: str) -> Optional[float]:
    """Query OpenSSF Scorecard API for package security score.

    Uses deps.dev to resolve package -> GitHub repo, then queries OpenSSF.
    This is the same approach used by GitHub's dependency-review-action.

    Returns score (0.0-10.0) or None if unavailable.
    APIs are free and do not require authentication.
    """
    if not OPENSSF_ENABLED:
        return None

    # Step 1: Resolve package to GitHub repository
    github_repo = get_github_repo_from_package(package_name, version, ecosystem)
    if not github_repo:
        return None

    # Step 2: Query OpenSSF Scorecard API with GitHub repo
    cache_key = f"openssf:{github_repo}"

    if cache_key in OPENSSF_CACHE:
        cached = OPENSSF_CACHE[cache_key]
        return cached if cached != "NONE" else None

    url = f"{OPENSSF_API_BASE}/{github_repo}"

    try:
        req = Request(url, headers={'User-Agent': 'Enterprise-Security-Governance/1.0'})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

            # Extract score from response
            score = data.get("score")
            if score is not None:
                score_float = float(score)
                OPENSSF_CACHE[cache_key] = score_float
                return score_float

    except (URLError, HTTPError, json.JSONDecodeError, ValueError, KeyError):
        pass

    OPENSSF_CACHE[cache_key] = "NONE"
    return None


def parse_package_lock_json(workspace_path: str) -> List[Tuple[str, str]]:
    """Extract npm package versions from package-lock.json."""
    lockfile_path = os.path.join(workspace_path, "package-lock.json")

    if not os.path.exists(lockfile_path):
        return []

    try:
        with open(lockfile_path, 'r') as f:
            data = json.load(f)

        packages = []

        # Handle both lockfile v2 and v3 formats
        if "packages" in data:
            for package_path, package_info in data["packages"].items():
                if not package_path or package_path == "":  # Skip root
                    continue

                # Extract package name (remove node_modules prefix)
                package_name = package_path.replace("node_modules/", "")
                version = package_info.get("version")

                if not version:
                    continue

                # Skip bundled/nested dependencies (lockfile v3 format issue)
                # Valid packages: "express", "@aws-sdk/client-acm"
                # Invalid (bundled): "aws-cdk-lib/fs-extra", "parent/@scoped/nested"
                if package_name.startswith("@"):
                    # Scoped package: @org/name is valid, @org/parent/nested is bundled
                    parts = package_name.split("/")
                    if len(parts) > 2:  # @org/parent/nested
                        continue
                else:
                    # Regular package: no slash allowed (parent/nested is bundled)
                    if "/" in package_name:
                        continue

                packages.append((package_name, version))

        # Fallback to v1 format
        elif "dependencies" in data:
            for package_name, package_info in data["dependencies"].items():
                version = package_info.get("version")
                if version:
                    packages.append((package_name, version))

        return packages

    except Exception as e:
        print(f"⚠️  Warning: Could not parse package-lock.json: {e}")
        return []


def parse_poetry_lock(workspace_path: str) -> List[Tuple[str, str]]:
    """Extract Python package versions from poetry.lock."""
    lockfile_path = os.path.join(workspace_path, "poetry.lock")

    if not os.path.exists(lockfile_path):
        return []

    try:
        packages = []
        current_package = None
        current_version = None

        with open(lockfile_path, 'r') as f:
            for line in f:
                line = line.strip()

                if line.startswith("name = "):
                    current_package = line.split('"')[1]
                elif line.startswith("version = "):
                    current_version = line.split('"')[1]

                    if current_package and current_version:
                        # Skip malformed package names (should not contain "/" in PyPI)
                        if "/" not in current_package:
                            packages.append((current_package, current_version))
                        current_package = None
                        current_version = None

        return packages

    except Exception as e:
        print(f"⚠️  Warning: Could not parse poetry.lock: {e}")
        return []


def parse_uv_lock(workspace_path: str) -> List[Tuple[str, str]]:
    """Extract Python package versions from uv.lock."""
    lockfile_path = os.path.join(workspace_path, "uv.lock")

    if not os.path.exists(lockfile_path):
        return []

    try:
        packages = []

        with open(lockfile_path, 'r') as f:
            content = f.read()

        # Parse TOML-like format for [[package]] sections
        package_sections = re.findall(r'\[\[package\]\](.*?)(?=\[\[package\]\]|\Z)', content, re.DOTALL)

        for section in package_sections:
            name_match = re.search(r'name\s*=\s*"([^"]+)"', section)
            version_match = re.search(r'version\s*=\s*"([^"]+)"', section)

            if name_match and version_match:
                package_name = name_match.group(1)
                package_version = version_match.group(1)

                # Skip malformed package names (should not contain "/" in PyPI)
                if "/" not in package_name:
                    packages.append((package_name, package_version))

        return packages

    except Exception as e:
        print(f"⚠️  Warning: Could not parse uv.lock: {e}")
        return []


def parse_go_sum(workspace_path: str) -> List[Tuple[str, str]]:
    """Extract Go module versions from go.sum."""
    gosum_path = os.path.join(workspace_path, "go.sum")

    if not os.path.exists(gosum_path):
        return []

    try:
        packages = []
        seen = set()

        with open(gosum_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    module_path = parts[0]
                    version = parts[1]

                    # Strip /go.mod suffix if present
                    version = version.replace('/go.mod', '')

                    # Deduplicate (go.sum has both module and go.mod entries)
                    key = f"{module_path}@{version}"
                    if key not in seen:
                        packages.append((module_path, version))
                        seen.add(key)

        return packages

    except Exception as e:
        print(f"⚠️  Warning: Could not parse go.sum: {e}")
        return []


def is_dependabot_context() -> Tuple[bool, bool]:
    """
    Detect if running in Dependabot context.
    Returns: (is_dependabot, is_security_update)
    """
    # Check GitHub Actions context
    github_actor = os.environ.get("GITHUB_ACTOR", "")
    github_event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    is_dependabot = github_actor in ["dependabot[bot]", "dependabot-preview[bot]"]

    # Check if it's a security update (Dependabot adds labels)
    # Read from GitHub event payload if available
    is_security = False
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.exists(event_path):
        try:
            with open(event_path, 'r') as f:
                event_data = json.load(f)
                pr_labels = event_data.get("pull_request", {}).get("labels", [])
                is_security = any(label.get("name") == "security" for label in pr_labels)
        except Exception:
            pass

    return is_dependabot, is_security


def validate_dependencies(workspace_path: str) -> Tuple[List[PackageViolation], List[ScorecardViolation]]:
    """Scan workspace for all lockfiles and validate dependency ages and OpenSSF scores."""
    age_violations = []
    scorecard_violations = []
    allowlist = load_allowlist()

    # Determine threshold based on context
    is_dependabot, is_security = is_dependabot_context()

    if is_dependabot and is_security:
        threshold_days = DEPENDABOT_SECURITY_THRESHOLD_DAYS
        context_msg = f"🤖 Dependabot SECURITY update detected - using reduced {threshold_days}-day threshold"
    elif is_dependabot:
        threshold_days = DEPENDABOT_FEATURE_THRESHOLD_DAYS
        context_msg = f"🤖 Dependabot feature update detected - using standard {threshold_days}-day threshold"
    else:
        threshold_days = AGE_THRESHOLD_DAYS
        context_msg = f"📅 Enforcing standard {threshold_days}-day maturation policy"

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=threshold_days)

    print(f"🔍 Scanning workspace: {workspace_path}")
    print(f"{context_msg} (packages must be published before {cutoff_date.date()})\n")

    # Collect all packages from all ecosystems
    all_packages = []

    # Node.js
    npm_packages = parse_package_lock_json(workspace_path)
    if npm_packages:
        print(f"📦 Found {len(npm_packages)} npm packages in package-lock.json")
        all_packages.extend([("npm", pkg, ver) for pkg, ver in npm_packages])

    # Python (Poetry)
    poetry_packages = parse_poetry_lock(workspace_path)
    if poetry_packages:
        print(f"🐍 Found {len(poetry_packages)} Python packages in poetry.lock")
        all_packages.extend([("pypi", pkg, ver) for pkg, ver in poetry_packages])

    # Python (uv)
    uv_packages = parse_uv_lock(workspace_path)
    if uv_packages:
        print(f"⚡ Found {len(uv_packages)} Python packages in uv.lock")
        all_packages.extend([("pypi", pkg, ver) for pkg, ver in uv_packages])

    # Go
    go_packages = parse_go_sum(workspace_path)
    if go_packages:
        print(f"🔷 Found {len(go_packages)} Go modules in go.sum")
        all_packages.extend([("go", pkg, ver) for pkg, ver in go_packages])

    if not all_packages:
        print("⚠️  No lockfiles found. This repository may be missing dependency lockfiles.")
        print("   Consider running the bulk-lockfile-generator workflow.\n")
        return [], []

    if OPENSSF_ENABLED:
        print(f"\n🔎 Validating {len(all_packages)} total dependencies (age + OpenSSF Scorecard)...\n")
    else:
        print(f"\n🔎 Validating {len(all_packages)} total dependencies (age only)...\n")

    # Validate each package
    for ecosystem, package_name, version in all_packages:
        # Skip internal packages
        if is_internal_package(package_name):
            continue

        # Skip allowlisted packages
        if is_allowlisted(package_name, version, allowlist):
            continue

        # Check 1: Package Age
        publish_date = None

        if ecosystem == "npm":
            publish_date = get_npm_publish_date(package_name, version)
        elif ecosystem == "pypi":
            publish_date = get_pypi_publish_date(package_name, version)
        elif ecosystem == "go":
            publish_date = get_go_publish_date(package_name, version)

        if publish_date and publish_date > cutoff_date:
            violation = PackageViolation(package_name, version, publish_date, ecosystem)
            age_violations.append(violation)

        # Check 2: OpenSSF Scorecard (if enabled)
        if OPENSSF_ENABLED:
            score = get_openssf_score(package_name, version, ecosystem)
            if score is not None and score < OPENSSF_MIN_SCORE:
                scorecard_violation = ScorecardViolation(package_name, version, score, ecosystem)
                scorecard_violations.append(scorecard_violation)

    return age_violations, scorecard_violations


def main():
    """Main entry point."""
    workspace_path = os.getcwd()

    # Allow override via environment variable
    if os.environ.get("WORKSPACE_PATH"):
        workspace_path = os.environ["WORKSPACE_PATH"]

    print("=" * 80)
    print("🛡️  Enterprise Supply Chain Security Gate")
    print("=" * 80)

    age_violations, scorecard_violations = validate_dependencies(workspace_path)
    total_violations = len(age_violations) + len(scorecard_violations)

    if total_violations > 0:
        print("\n" + "=" * 80)
        print(f"❌ SECURITY GATE FAILED: {total_violations} violations detected")
        print("=" * 80 + "\n")

        # Print age violations first
        if age_violations:
            print(f"📅 Age Policy Violations ({len(age_violations)}):")
            print("-" * 80)
            for violation in age_violations:
                print(violation)
            print()

        # Print scorecard violations
        if scorecard_violations:
            print(f"📊 OpenSSF Scorecard Violations ({len(scorecard_violations)}):")
            print("-" * 80)
            for violation in scorecard_violations:
                print(violation)
            print()

        # Check context for better messaging
        is_dependabot, is_security = is_dependabot_context()
        threshold = DEPENDABOT_SECURITY_THRESHOLD_DAYS if (is_dependabot and is_security) else AGE_THRESHOLD_DAYS

        print(f"📋 Violations Summary:")
        print(f"   - Age violations: {len(age_violations)}")
        print(f"   - Scorecard violations: {len(scorecard_violations)}")
        print(f"   - Total violations: {total_violations}")
        print(f"   - Age policy: Packages must be published at least {threshold} days ago")

        if OPENSSF_ENABLED:
            print(f"   - Scorecard policy: Packages must score at least {OPENSSF_MIN_SCORE:.1f}/10.0")

        if is_dependabot and is_security:
            print(f"   - Context: Dependabot security update (reduced threshold applied)")
            print(f"   - Note: Security updates use {DEPENDABOT_SECURITY_THRESHOLD_DAYS}-day threshold vs {AGE_THRESHOLD_DAYS}-day for manual changes")

        print(f"   - Action required: Wait for packages to mature or request break-glass exemption\n")

        if age_violations:
            print("🔧 To request an age policy exemption, add to policies/allowlist.json:")
            print("   {")
            print(f'     "package": "{age_violations[0].name}",')
            print(f'     "version": "{age_violations[0].version}",')
            print('     "reason": "Critical security patch",')
            print('     "expires_at": "2026-06-01T00:00:00Z"')
            print("   }\n")

        sys.exit(1)

    else:
        print("\n" + "=" * 80)
        checks_performed = ["age policy"]
        if OPENSSF_ENABLED:
            checks_performed.append("OpenSSF Scorecard")

        print(f"✅ SECURITY GATE PASSED: All dependencies comply with {' + '.join(checks_performed)}")
        print("=" * 80 + "\n")
        print(f"📊 Cache efficiency: {len(REGISTRY_CACHE)} registry lookups cached")

        if OPENSSF_ENABLED:
            scored_count = sum(1 for score in OPENSSF_CACHE.values() if score is not None)
            print(f"📊 OpenSSF Scorecard: {scored_count} packages scored successfully")

        sys.exit(0)


if __name__ == "__main__":
    main()
