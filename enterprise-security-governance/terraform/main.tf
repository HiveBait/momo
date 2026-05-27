# Enterprise Security Governance - Terraform Configuration
# Manages GitHub Enterprise organization-level security policies and automation

# Organization Secrets (for Coralogix integration)
resource "github_actions_organization_secret" "coralogix_api_key" {
  secret_name     = "CORALOGIX_API_KEY"
  visibility      = "all"
  plaintext_value = var.coralogix_api_key
}

# Repository: enterprise-security-governance
resource "github_repository" "security_governance" {
  name        = "enterprise-security-governance"
  description = "Centralized supply chain security policy enforcement and automation hub"

  visibility           = "internal"
  has_issues           = true
  has_projects         = false
  has_wiki             = false
  allow_merge_commit   = false
  allow_squash_merge   = true
  allow_rebase_merge   = false
  delete_branch_on_merge = true

  # Require signed commits
  web_commit_signoff_required = true

  # Security settings
  vulnerability_alerts                    = true
  has_vulnerability_alerts_enabled        = true

  topics = ["security", "supply-chain", "devsecops", "governance"]
}

# Branch Protection for main branch
resource "github_branch_protection" "security_governance_main" {
  repository_id = github_repository.security_governance.node_id
  pattern       = "main"

  required_status_checks {
    strict   = true
    contexts = [
      "Lint and Test Security Scripts",
      "Validate Terraform Configuration"
    ]
  }

  required_pull_request_reviews {
    dismiss_stale_reviews           = true
    require_code_owner_reviews      = true
    required_approving_review_count = 2
    require_last_push_approval      = true
    restrict_dismissals             = true
    dismissal_restrictions          = [data.github_team.security.node_id]
  }

  enforce_admins = true

  required_linear_history         = true
  require_conversation_resolution = true
  require_signed_commits          = true

  push_restrictions = [data.github_team.security.node_id]
}

# CODEOWNERS file restriction (managed via repository file)
# See .github/CODEOWNERS in the repository

# Organization Rulesets (GitHub Enterprise Cloud feature)
# Enforce security gates across all repositories
resource "github_organization_ruleset" "supply_chain_security" {
  count = var.enable_required_workflows ? 1 : 0

  name        = "supply-chain-security-gate"
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }

    repository_name {
      include = ["~ALL"]
      exclude = [
        "enterprise-security-governance", # Don't apply to itself
        "*.archived"                     # Skip archived repos
      ]
    }
  }

  bypass_actors {
    actor_id    = data.github_team.security.id
    actor_type  = "Team"
    bypass_mode = "always"
  }

  rules {
    # Require status checks from central security gate
    required_status_checks {
      required_check {
        context = "Enforce 7-Day Package Maturation Policy"
      }
    }

    # Require pull request before merging
    pull_request {
      required_approving_review_count   = 1
      dismiss_stale_reviews_on_push     = true
      require_code_owner_review         = false
      require_last_push_approval        = false
    }
  }
}

# Organization Ruleset for lockfile enforcement (optional strict mode)
resource "github_organization_ruleset" "lockfile_enforcement" {
  count = var.enforce_lockfiles ? 1 : 0

  name        = "dependency-lockfile-requirement"
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }

    repository_name {
      include = ["~ALL"]
      exclude = ["*.archived"]
    }
  }

  bypass_actors {
    actor_id    = data.github_team.security.id
    actor_type  = "Team"
    bypass_mode = "always"
  }

  rules {
    # Require specific files to be present
    required_file {
      file_path = "package-lock.json"
      # Only enforced if package.json exists (conditional via workflow)
    }
  }
}

# Data source: Security team
data "github_team" "security" {
  slug = var.security_team
}

# Organization Variables (non-sensitive configuration)
resource "github_actions_organization_variable" "max_package_age" {
  variable_name = "MAX_PACKAGE_AGE_DAYS"
  visibility    = "all"
  value         = tostring(var.max_package_age_days)
}

resource "github_actions_organization_variable" "coralogix_app_name" {
  variable_name = "CORALOGIX_APPLICATION_NAME"
  visibility    = "all"
  value         = var.coralogix_application_name
}

# Repository Environment (for workflow dispatch protection)
resource "github_repository_environment" "bulk_remediation" {
  repository  = github_repository.security_governance.name
  environment = "bulk-remediation"

  reviewers {
    teams = [data.github_team.security.id]
  }

  deployment_branch_policy {
    protected_branches     = true
    custom_branch_policies = false
  }
}

# Outputs
output "security_governance_repo_url" {
  description = "URL of the enterprise security governance repository"
  value       = github_repository.security_governance.html_url
}

output "security_team_id" {
  description = "GitHub team ID for security team"
  value       = data.github_team.security.id
}

output "ruleset_ids" {
  description = "IDs of created organization rulesets"
  value = {
    supply_chain_security = var.enable_required_workflows ? github_organization_ruleset.supply_chain_security[0].id : null
    lockfile_enforcement  = var.enforce_lockfiles ? github_organization_ruleset.lockfile_enforcement[0].id : null
  }
}
