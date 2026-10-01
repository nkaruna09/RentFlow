# Shared helpers for the scripts in scripts/azure. Source it, don't run it:
#
#   source "$(dirname "$0")/lib.sh"
#   rentflow_env staging        # sets RESOURCE_GROUP, ACR_NAME, API_APP, ...
#
# Names mirror infra/main.bicep. RESOURCE_GROUP and ACR_NAME can be overridden
# by environment variables (cd-azure.yml sets them from GitHub variables).

set -euo pipefail

# The Azure CLI on Windows otherwise prints through the 'charmap' codec and
# crashes on non-ASCII output (build logs, emoji in tool output).
export PYTHONIOENCODING=utf-8

log() { printf '\033[1;34m==>\033[0m %s\n' "$*" >&2; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

rentflow_env() {
  case "${1:-}" in
    staging)
      ENVIRONMENT=staging
      ENV_SHORT=staging
      NAME_SUFFIX=${RENTFLOW_NAME_SUFFIX-}
      ;;
    production)
      ENVIRONMENT=production
      ENV_SHORT=prod
      # Matches infra/env/production.bicepparam (default names are taken).
      NAME_SUFFIX=${RENTFLOW_NAME_SUFFIX-nk09}
      ;;
    *) die "environment must be 'staging' or 'production' (got '${1:-}')" ;;
  esac

  RESOURCE_GROUP=${RESOURCE_GROUP:-rg-rentflow-$ENV_SHORT}
  ACR_NAME=${ACR_NAME:-crrentflow$ENV_SHORT$NAME_SUFFIX}
  API_APP=ca-rentflow-api-$ENV_SHORT
  WEB_APP=ca-rentflow-web-$ENV_SHORT
  MIGRATE_JOB=caj-rentflow-migrate-$ENV_SHORT
  KEY_VAULT=kv-rentflow-$ENV_SHORT$NAME_SUFFIX
  export ENVIRONMENT ENV_SHORT NAME_SUFFIX RESOURCE_GROUP ACR_NAME API_APP WEB_APP MIGRATE_JOB KEY_VAULT
}

# Revision currently receiving traffic (resolves `latestRevision: true`).
serving_revision() {
  local app=$1 pinned
  pinned=$(az containerapp ingress traffic show -n "$app" -g "$RESOURCE_GROUP" \
    --query "[?weight > \`0\` && revisionName != null].revisionName | [0]" -o tsv 2>/dev/null || true)
  if [[ -n "$pinned" ]]; then
    echo "$pinned"
  else
    az containerapp show -n "$app" -g "$RESOURCE_GROUP" \
      --query properties.latestReadyRevisionName -o tsv
  fi
}

# Write key=value to $GITHUB_OUTPUT when running in Actions.
gh_output() {
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "$1=$2" >>"$GITHUB_OUTPUT"
  fi
}
