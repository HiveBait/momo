# Enterprise-Level Security Governance Configuration
# Use this instead of main.tf if deploying at GitHub Enterprise level
# Applies rulesets across ALL organizations in the enterprise

# Enterprise-level ruleset for supply chain security
resource "github_enterprise_organization_ruleset" "supply_chain_security_enterprise" {
  count = var.enable_enterprise_level ? 1 : 0

  enterprise_id = var.github_enterprise_slug
  name          = "supply-chain-security-gate"
  target        = "branch"
  enforcement   = var.enforcement_mode # "active", "evaluate", or "disabled"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }

    repository_name {
      include = ["~ALL"]
      exclude = [
        "enterprise-security-governance", # Don't apply to hub itself
        "*.archived",                    # Skip archived repos
        "*.template"                     # Skip template repos
      ]
    }

    # Optional: Apply only to specific organizations within enterprise
    # organization_name {
    #   include = ["HiveBait", "HiveBait-labs"]
    #   exclude = ["HiveBait-sandbox"]
    # }
  }

  # Allow security team to bypass (enterprise-level team)
  bypass_actors {
    actor_id    = var.enterprise_security_team_id
    actor_type  = "Team"
    bypass_mode = "always"
  }

  rules {
    # Require status checks from central security gate
    required_status_checks {
      required_check {
        context        = "Enforce 7-Day Package Maturation Policy"
        integration_id = var.github_app_integration_id # Optional: Pin to specific GitHub App
      }
    }

    # Require pull request before merging
    pull_request {
      required_approving_review_count = 1
      dismiss_stale_reviews_on_push   = true
      require_code_owner_review       = false
      require_last_push_approval      = false
    }
  }
}

# Enterprise-level lockfile enforcement ruleset
resource "github_enterprise_organization_ruleset" "lockfile_enforcement_enterprise" {
  count = var.enable_enterprise_level && var.enforce_lockfiles ? 1 : 0

  enterprise_id = var.github_enterprise_slug
  name          = "lockfile-requirement"
  target        = "branch"
  enforcement   = var.enforcement_mode

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }

    repository_name {
      include = ["~ALL"]
      exclude = [
        "enterprise-security-governance",
        "*.archived",
        "*.template"
      ]
    }
  }

  bypass_actors {
    actor_id    = var.enterprise_security_team_id
    actor_type  = "Team"
    bypass_mode = "always"
  }

  rules {
    # Block commits without lockfiles (file path pattern rules)
    # Note: This is a strict enforcement - use with caution
    required_workflows {
      required_workflow {
        path         = ".github/workflows/central-security-gate.yml"
        ref          = "refs/heads/main"
        repository_id = var.hub_repository_id
      }
    }
  }
}

# Enterprise-level secret for Coralogix (applies to all orgs)
# Note: This requires GitHub Enterprise Cloud with Actions secrets at enterprise level
# Alternative: Deploy org-level secrets via separate Terraform configurations per org

output "enterprise_ruleset_ids" {
  description = "Enterprise-level ruleset IDs for audit and monitoring"
  value = {
    supply_chain_security = var.enable_enterprise_level ? github_enterprise_organization_ruleset.supply_chain_security_enterprise[0].id : null
    lockfile_enforcement  = var.enable_enterprise_level && var.enforce_lockfiles ? github_enterprise_organization_ruleset.lockfile_enforcement_enterprise[0].id : null
  }
}

output "enterprise_coverage" {
  description = "Enterprise-level deployment summary"
  value = var.enable_enterprise_level ? {
    enforcement_mode = var.enforcement_mode
    enterprise_slug  = var.github_enterprise_slug
    status          = "Enterprise-level rulesets active across all organizations"
  } : {
    status = "Enterprise-level deployment disabled (using organization-level)"
  }
}
