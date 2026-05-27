#!/bin/bash
# pnpm Configuration - Supply Chain Security
# Run this script to configure pnpm globally

# Block packages published within last 7 days (10080 minutes)
pnpm config set minimumReleaseAge 10080

# Optional: Save exact versions
pnpm config set save-exact true

echo "✅ pnpm configured with 7-day package maturation policy"
echo "Verify: pnpm config get minimumReleaseAge"

# Documentation: https://pnpm.io/cli/config
