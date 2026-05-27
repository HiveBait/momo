#!/usr/bin/env python3
"""
Multi-Language Dependency Age Gate Validator
Enforces 7-day maturation rule for supply chain security across npm, PyPI, and Go modules.
Zero external dependencies - uses only Python standard library.
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

# Global cache to avoid redundant API calls
REGISTRY_CACHE: Dict[str, datetime] = {}


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

                if version:
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
                packages.append((name_match.group(1), version_match.group(1)))

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


def validate_dependencies(workspace_path: str) -> List[PackageViolation]:
    """Scan workspace for all lockfiles and validate dependency ages."""
    violations = []
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
        return []

    print(f"\n🔎 Validating {len(all_packages)} total dependencies...\n")

    # Validate each package
    for ecosystem, package_name, version in all_packages:
        # Skip internal packages
        if is_internal_package(package_name):
            continue

        # Skip allowlisted packages
        if is_allowlisted(package_name, version, allowlist):
            continue

        # Query registry for publish date
        publish_date = None

        if ecosystem == "npm":
            publish_date = get_npm_publish_date(package_name, version)
        elif ecosystem == "pypi":
            publish_date = get_pypi_publish_date(package_name, version)
        elif ecosystem == "go":
            publish_date = get_go_publish_date(package_name, version)

        # Check age
        if publish_date and publish_date > cutoff_date:
            violation = PackageViolation(package_name, version, publish_date, ecosystem)
            violations.append(violation)

    return violations


def main():
    """Main entry point."""
    workspace_path = os.getcwd()

    # Allow override via environment variable
    if os.environ.get("WORKSPACE_PATH"):
        workspace_path = os.environ["WORKSPACE_PATH"]

    print("=" * 80)
    print("🛡️  Enterprise Supply Chain Security Gate")
    print("=" * 80)

    violations = validate_dependencies(workspace_path)

    if violations:
        print("\n" + "=" * 80)
        print(f"❌ SECURITY GATE FAILED: {len(violations)} violations detected")
        print("=" * 80 + "\n")

        for violation in violations:
            print(violation)

        # Check context for better messaging
        is_dependabot, is_security = is_dependabot_context()
        threshold = DEPENDABOT_SECURITY_THRESHOLD_DAYS if (is_dependabot and is_security) else AGE_THRESHOLD_DAYS

        print(f"\n📋 Violations summary:")
        print(f"   - Total violations: {len(violations)}")
        print(f"   - Policy: Packages must be published at least {threshold} days ago")

        if is_dependabot and is_security:
            print(f"   - Context: Dependabot security update (reduced threshold applied)")
            print(f"   - Note: Security updates use {DEPENDABOT_SECURITY_THRESHOLD_DAYS}-day threshold vs {AGE_THRESHOLD_DAYS}-day for manual changes")

        print(f"   - Action required: Wait for packages to mature or request break-glass exemption\n")

        print("🔧 To request an exemption, add to policies/allowlist.json:")
        print("   {")
        print(f'     "package": "{violations[0].name}",')
        print(f'     "version": "{violations[0].version}",')
        print('     "reason": "Critical security patch",')
        print('     "expires_at": "2026-06-01T00:00:00Z"')
        print("   }\n")

        sys.exit(1)

    else:
        print("\n" + "=" * 80)
        print("✅ SECURITY GATE PASSED: All dependencies comply with age policy")
        print("=" * 80 + "\n")
        print(f"📊 Cache efficiency: {len(REGISTRY_CACHE)} registry lookups cached")
        sys.exit(0)


if __name__ == "__main__":
    main()
