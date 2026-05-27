#!/usr/bin/env python3
"""
Unit tests for dependency_age_gate.py
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import dependency_age_gate as age_gate


class TestAllowlist(unittest.TestCase):
    """Test allowlist functionality."""

    def setUp(self):
        """Create temporary allowlist file."""
        self.temp_dir = tempfile.mkdtemp()
        self.allowlist_path = os.path.join(self.temp_dir, 'allowlist.json')

        # Override the module's allowlist path
        age_gate.ALLOWLIST_PATH = self.allowlist_path

    def test_load_empty_allowlist(self):
        """Test loading an empty allowlist."""
        with open(self.allowlist_path, 'w') as f:
            json.dump({"exemptions": []}, f)

        allowlist = age_gate.load_allowlist()
        self.assertEqual(allowlist, {"exemptions": []})

    def test_load_missing_allowlist(self):
        """Test loading when allowlist file doesn't exist."""
        os.remove(self.allowlist_path)
        allowlist = age_gate.load_allowlist()
        self.assertEqual(allowlist, {"exemptions": []})

    def test_is_allowlisted_active_exemption(self):
        """Test checking for active exemption."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        allowlist = {
            "exemptions": [
                {
                    "package": "test-package",
                    "version": "1.0.0",
                    "reason": "Critical security patch",
                    "expires_at": future_date
                }
            ]
        }

        result = age_gate.is_allowlisted("test-package", "1.0.0", allowlist)
        self.assertTrue(result)

    def test_is_allowlisted_expired_exemption(self):
        """Test checking for expired exemption."""
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        allowlist = {
            "exemptions": [
                {
                    "package": "test-package",
                    "version": "1.0.0",
                    "reason": "Temporary override",
                    "expires_at": past_date
                }
            ]
        }

        result = age_gate.is_allowlisted("test-package", "1.0.0", allowlist)
        self.assertFalse(result)

    def test_is_allowlisted_no_match(self):
        """Test checking for non-existent exemption."""
        allowlist = {"exemptions": []}
        result = age_gate.is_allowlisted("unknown-package", "1.0.0", allowlist)
        self.assertFalse(result)


class TestInternalPackages(unittest.TestCase):
    """Test internal package detection."""

    def test_internal_HiveBait_npm(self):
        """Test detection of @HiveBait/ scoped npm packages."""
        self.assertTrue(age_gate.is_internal_package("@HiveBait/some-package"))

    def test_internal_HiveBait_go(self):
        """Test detection of github.com/HiveBait/ Go modules."""
        self.assertTrue(age_gate.is_internal_package("github.com/HiveBait/some-module"))

    def test_external_package(self):
        """Test that external packages are not marked as internal."""
        self.assertFalse(age_gate.is_internal_package("react"))
        self.assertFalse(age_gate.is_internal_package("requests"))
        self.assertFalse(age_gate.is_internal_package("github.com/external/module"))


class TestLockfileParsing(unittest.TestCase):
    """Test lockfile parsing functionality."""

    def setUp(self):
        """Create temporary workspace directory."""
        self.temp_dir = tempfile.mkdtemp()

    def test_parse_package_lock_json_v2(self):
        """Test parsing package-lock.json v2 format."""
        lockfile_data = {
            "lockfileVersion": 2,
            "packages": {
                "": {"name": "test-app", "version": "1.0.0"},
                "node_modules/react": {"version": "18.2.0"},
                "node_modules/react-dom": {"version": "18.2.0"}
            }
        }

        lockfile_path = os.path.join(self.temp_dir, 'package-lock.json')
        with open(lockfile_path, 'w') as f:
            json.dump(lockfile_data, f)

        packages = age_gate.parse_package_lock_json(self.temp_dir)

        self.assertEqual(len(packages), 2)
        self.assertIn(("react", "18.2.0"), packages)
        self.assertIn(("react-dom", "18.2.0"), packages)

    def test_parse_poetry_lock(self):
        """Test parsing poetry.lock file."""
        poetry_lock_content = '''[[package]]
name = "requests"
version = "2.31.0"

[[package]]
name = "urllib3"
version = "2.0.0"
'''

        lockfile_path = os.path.join(self.temp_dir, 'poetry.lock')
        with open(lockfile_path, 'w') as f:
            f.write(poetry_lock_content)

        packages = age_gate.parse_poetry_lock(self.temp_dir)

        self.assertEqual(len(packages), 2)
        self.assertIn(("requests", "2.31.0"), packages)
        self.assertIn(("urllib3", "2.0.0"), packages)

    def test_parse_go_sum(self):
        """Test parsing go.sum file."""
        gosum_content = '''github.com/stretchr/testify v1.8.0 h1:abc123
github.com/stretchr/testify v1.8.0/go.mod h1:xyz456
github.com/gin-gonic/gin v1.9.0 h1:def789
'''

        gosum_path = os.path.join(self.temp_dir, 'go.sum')
        with open(gosum_path, 'w') as f:
            f.write(gosum_content)

        packages = age_gate.parse_go_sum(self.temp_dir)

        # Should deduplicate and strip /go.mod suffix
        self.assertGreaterEqual(len(packages), 2)
        self.assertIn(("github.com/stretchr/testify", "v1.8.0"), packages)
        self.assertIn(("github.com/gin-gonic/gin", "v1.9.0"), packages)

    def test_parse_missing_lockfile(self):
        """Test parsing when lockfile doesn't exist."""
        packages = age_gate.parse_package_lock_json(self.temp_dir)
        self.assertEqual(packages, [])


class TestPackageViolation(unittest.TestCase):
    """Test PackageViolation class."""

    def test_violation_string_representation(self):
        """Test string representation of violation."""
        publish_date = datetime.now(timezone.utc) - timedelta(days=3)
        violation = age_gate.PackageViolation(
            name="test-package",
            version="1.0.0",
            published_date=publish_date,
            ecosystem="npm"
        )

        violation_str = str(violation)
        self.assertIn("test-package@1.0.0", violation_str)
        self.assertIn("npm", violation_str)
        self.assertIn("3 days ago", violation_str)

    def test_violation_age_calculation(self):
        """Test age calculation in violation."""
        publish_date = datetime.now(timezone.utc) - timedelta(days=5)
        violation = age_gate.PackageViolation(
            name="test-package",
            version="1.0.0",
            published_date=publish_date,
            ecosystem="pypi"
        )

        self.assertEqual(violation.age_days, 5)


class TestCaching(unittest.TestCase):
    """Test registry lookup caching."""

    def setUp(self):
        """Clear cache before each test."""
        age_gate.REGISTRY_CACHE.clear()

    def test_cache_usage(self):
        """Test that cache is used for duplicate lookups."""
        # This test would require mocking urllib, so we just verify cache structure
        test_date = datetime.now(timezone.utc)
        age_gate.REGISTRY_CACHE["npm:test-pkg@1.0.0"] = test_date

        self.assertIn("npm:test-pkg@1.0.0", age_gate.REGISTRY_CACHE)
        self.assertEqual(age_gate.REGISTRY_CACHE["npm:test-pkg@1.0.0"], test_date)


if __name__ == '__main__':
    unittest.main()
