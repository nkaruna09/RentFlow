#!/usr/bin/env bash
# Create or update the GitHub Environment that cd-azure.yml deploys through.
#
#   scripts/azure/configure-github-environment.sh <staging|production>
#
# staging     no protection rules: every push to main deploys.
# production  deployments wait for a required reviewer (the authenticated gh
#             user, or REVIEWER_LOGIN) and are only allowed from `main`.
#
# The OIDC federated credential in identity.bicep trusts exactly this
# environment (repo:<owner/repo>:environment:<env>), so a job that skips the
# approval can't obtain an Azure token for production at all.
#
# Idempotent. Needs `gh auth login` with admin rights on the repository.

source "$(dirname "$0")/lib.sh"

[[ $# -eq 1 ]] || die "usage: $0 <staging|production>"
rentflow_env "$1"
repo=${GITHUB_REPO:-nkaruna09/RentFlow}

if [[ "$ENVIRONMENT" == staging ]]; then
  log "Configuring GitHub Environment 'staging' (no protection rules)"
  gh api -X PUT "repos/$repo/environments/staging" --silent
  exit 0
fi

reviewer=${REVIEWER_LOGIN:-$(gh api user --jq .login)}
reviewer_id=$(gh api "users/$reviewer" --jq .id)
log "Configuring GitHub Environment 'production': required reviewer $reviewer, main branch only"
gh api -X PUT "repos/$repo/environments/production" --input - --silent <<JSON
{
  "wait_timer": 0,
  "prevent_self_review": false,
  "reviewers": [{ "type": "User", "id": $reviewer_id }],
  "deployment_branch_policy": { "protected_branches": false, "custom_branch_policies": true }
}
JSON

existing=$(gh api "repos/$repo/environments/production/deployment-branch-policies" \
  --jq '.branch_policies[] | select(.name == "main" and .type == "branch") | .id')
if [[ -z "$existing" ]]; then
  gh api -X POST "repos/$repo/environments/production/deployment-branch-policies" \
    -f name=main -f type=branch --silent
fi

gh api "repos/$repo/environments/production" --jq '{
  environment: .name,
  required_reviewers: [.protection_rules[] | select(.type == "required_reviewers") | .reviewers[].reviewer.login],
  custom_branch_policies: .deployment_branch_policy.custom_branch_policies
}'
