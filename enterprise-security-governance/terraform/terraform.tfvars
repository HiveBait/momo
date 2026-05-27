# Enterprise Security Governance - Terraform Variables
# Copy this to terraform.tfvars.local and customize for your organization

organization_name = "HiveBait"
security_team     = "security-team"

# Coralogix SIEM Integration
# Set via environment variable: export TF_VAR_coralogix_api_key="your-api-key"
# coralogix_api_key = "SENSITIVE - SET VIA ENV VAR"
coralogix_application_name = "enterprise-security-governance"

# Policy Enforcement Configuration
enable_required_workflows = true  # Enable organization-wide security gates
enforce_lockfiles         = false # Start permissive, migrate to true after remediation

# Supply Chain Security Policy
max_package_age_days = 7 # Minimum package maturation period

# Emergency Bypass (use sparingly)
allowed_bypass_teams = [
  # "incident-response-team"  # Uncomment only during active incidents
]
