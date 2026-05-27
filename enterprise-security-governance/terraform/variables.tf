variable "organization_name" {
  description = "GitHub Enterprise organization name"
  type        = string
}

variable "security_team" {
  description = "GitHub team slug for security/SecOps team with approval authority"
  type        = string
  default     = "security-team"
}

variable "coralogix_api_key" {
  description = "Coralogix API key for SIEM integration (sensitive)"
  type        = string
  sensitive   = true
}

variable "coralogix_application_name" {
  description = "Coralogix application name for log aggregation"
  type        = string
  default     = "enterprise-security-governance"
}

variable "enable_required_workflows" {
  description = "Enable organization-wide required workflows for security gates"
  type        = bool
  default     = true
}

variable "enforce_lockfiles" {
  description = "Block PRs in repositories missing dependency lockfiles"
  type        = bool
  default     = false # Start permissive, migrate to enforcement
}

variable "allowed_bypass_teams" {
  description = "List of team slugs allowed to bypass security gates (emergency use only)"
  type        = list(string)
  default     = []
}

variable "max_package_age_days" {
  description = "Maximum age threshold for dependency packages (days)"
  type        = number
  default     = 7

  validation {
    condition     = var.max_package_age_days >= 1 && var.max_package_age_days <= 90
    error_message = "Package age must be between 1 and 90 days."
  }
}

# ============================================================================
# Enterprise-Level Configuration
# ============================================================================

variable "enable_enterprise_level" {
  description = "Deploy rulesets at GitHub Enterprise level (applies to ALL organizations)"
  type        = bool
  default     = false
}

variable "github_enterprise_slug" {
  description = "GitHub Enterprise slug (e.g., 'HiveBait-enterprise'). Required if enable_enterprise_level = true"
  type        = string
  default     = ""
}

variable "enterprise_security_team_id" {
  description = "Enterprise-level security team ID for bypass permissions. Get from GitHub Enterprise settings"
  type        = number
  default     = null
}

variable "enforcement_mode" {
  description = "Ruleset enforcement mode: 'active' (enforce), 'evaluate' (audit only), 'disabled'"
  type        = string
  default     = "evaluate"

  validation {
    condition     = contains(["active", "evaluate", "disabled"], var.enforcement_mode)
    error_message = "Enforcement mode must be 'active', 'evaluate', or 'disabled'."
  }
}

variable "github_app_integration_id" {
  description = "GitHub App integration ID for pinning status checks (optional)"
  type        = number
  default     = null
}

variable "hub_repository_id" {
  description = "Repository ID of enterprise-security-governance hub (for required workflows)"
  type        = string
  default     = ""
}
