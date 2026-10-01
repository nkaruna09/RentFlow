#!/usr/bin/env bash
# First-time setup of an environment, from an empty subscription to a verified,
# CD-ready deployment.
#
#   scripts/azure/bootstrap-environment.sh <staging|production> [--yes]
#
#   1. Check prerequisites and register the resource providers.
#   2. Deploy infra/main.bicep without the container apps (the registry is
#      still empty, so there is nothing to run yet).
#   3. Generate the Key Vault secrets (bootstrap-secrets.sh).
#   4. Build the first api/web images into the registry: `az acr build`,
#      falling back to local Docker where ACR Tasks is unavailable.
#   5. Deploy again with the apps and the migration job, then run migrations.
#   6. Configure the GitHub Environment plus the secrets/variables cd-azure.yml needs.
#   7. Smoke-test the result (staging only).
#
# Re-running is safe: every step is idempotent. After this, pushes to main
# deploy staging through cd-azure.yml.
#
# Prerequisites: az login (Owner on the subscription), gh auth login (repo
# admin), openssl, python, and Docker only if ACR Tasks is blocked.

source "$(dirname "$0")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <staging|production> [--yes]"
rentflow_env "$1"
yes_flag=${2:-}
script_dir=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$script_dir/../.." && pwd)
repo=${GITHUB_REPO:-nkaruna09/RentFlow}

# --- 1. prerequisites -----------------------------------------------------------
log "Checking prerequisites"
state=$(az account show --query state -o tsv) || die "run 'az login' first"
subscription_name=$(az account show --query name -o tsv)
[[ "$state" == Enabled ]] || die "subscription '$subscription_name' is $state; re-enable it first"
gh auth status >/dev/null 2>&1 || die "run 'gh auth login' first"
log "Subscription: $subscription_name ($(az account show --query id -o tsv))"

for namespace in Microsoft.App Microsoft.DBforPostgreSQL Microsoft.ContainerRegistry \
  Microsoft.KeyVault Microsoft.Storage Microsoft.OperationalInsights Microsoft.Insights \
  Microsoft.ManagedIdentity Microsoft.Network; do
  if [[ "$(az provider show -n "$namespace" --query registrationState -o tsv)" != Registered ]]; then
    log "Registering resource provider $namespace"
    az provider register -n "$namespace" --wait -o none
  fi
done

# --- 2. infrastructure without apps ----------------------------------------------
outputs=$(mktemp)
trap 'rm -f "$outputs"' EXIT
log "Deploying infrastructure (step 1 of 2)"
DEPLOY_OUTPUTS_FILE=$outputs bash "$script_dir/deploy-infra.sh" "$ENVIRONMENT" $yes_flag >/dev/null

output() {
  python - "$outputs" "$1" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))[sys.argv[2]]["value"])
PY
}
default_domain=$(output containerAppsDefaultDomain)
registry=$(output registryName)
github_client_id=$(output githubDeployClientId)
api_url="https://$API_APP.$default_domain"
web_url="https://$WEB_APP.$default_domain"

# --- 3. secrets -----------------------------------------------------------------
bash "$script_dir/bootstrap-secrets.sh" "$ENVIRONMENT"

# --- 4. first images -------------------------------------------------------------
# Override with BOOTSTRAP_IMAGE_TAG to reuse images from an earlier run.
tag=${BOOTSTRAP_IMAGE_TAG:-bootstrap-$(git -C "$repo_root" rev-parse --short HEAD)}
api_image="$registry.azurecr.io/rentflow-api:$tag"
web_image="$registry.azurecr.io/rentflow-web:$tag"
web_args=(--build-arg "NEXT_PUBLIC_API_URL=$api_url/api/v1" --build-arg "NEXT_PUBLIC_SITE_URL=$web_url")

# Build one image with ACR Tasks and wait for the run's real result.
# Returns 0 on success, 1 if the build itself failed, 2 if ACR couldn't queue it.
# Logs aren't streamed: on Windows the CLI crashes encoding build output for
# the console ('charmap' codec), which says nothing about the build.
acr_build() {
  local repository_tag=$1 context=$2 run_id status
  shift 2
  if az acr repository show -n "$registry" --image "$repository_tag" -o none 2>/dev/null; then
    log "$repository_tag already in $registry; skipping build"
    return 0
  fi
  local queued
  # --no-wait returns no JSON; the run ID is only in the "Queued a build with ID: <id>" line.
  queued=$(az acr build -r "$registry" -t "$repository_tag" --target runtime "$@" \
    --no-wait "$context" 2>&1) || return 2
  run_id=$(grep -oE 'Queued a build with ID: [A-Za-z0-9]+' <<<"$queued" | awk '{print $NF}' || true)
  [[ -n "$run_id" ]] || return 2
  log "ACR run $run_id building $repository_tag"
  while :; do
    status=$(az acr task show-run -r "$registry" --run-id "$run_id" --query status -o tsv)
    case "$status" in
      Succeeded) return 0 ;;
      Failed | Canceled | Error | Timeout)
        warn "ACR run $run_id ended '$status'; last log lines:"
        az acr task logs -r "$registry" --run-id "$run_id" 2>/dev/null | tail -40 >&2 || true
        return 1
        ;;
    esac
    sleep 15
  done
}

log "Building images with ACR Tasks"
acr_build "rentflow-api:$tag" "$repo_root/backend" && api_built=0 || api_built=$?
if ((api_built == 0)); then
  acr_build "rentflow-web:$tag" "$repo_root/frontend" "${web_args[@]}" && web_built=0 || web_built=$?
else
  web_built=$api_built
fi
if ((api_built == 1 || web_built == 1)); then
  die "an image failed to build (see the log above); fix it and re-run this script"
elif ((api_built == 0 && web_built == 0)); then
  log "Images built in ACR"
else
  warn "ACR Tasks couldn't queue a build (often blocked on free-credit subscriptions); using local Docker"
  docker info >/dev/null 2>&1 || die "start Docker Desktop, then re-run this script"
  az acr login -n "$registry"
  docker build --target runtime -t "$api_image" "$repo_root/backend"
  docker build --target runtime "${web_args[@]}" -t "$web_image" "$repo_root/frontend"
  docker push "$api_image"
  docker push "$web_image"
fi

# --- 5. apps + migrations ---------------------------------------------------------
log "Deploying infrastructure with the container apps (step 2 of 2)"
API_IMAGE=$api_image WEB_IMAGE=$web_image DEPLOY_APPS=true \
  bash "$script_dir/deploy-infra.sh" "$ENVIRONMENT" --yes >/dev/null
bash "$script_dir/run-migrations.sh" "$ENVIRONMENT" "$api_image"

# --- 6. GitHub ------------------------------------------------------------------
bash "$script_dir/configure-github-environment.sh" "$ENVIRONMENT"
log "Setting GitHub secrets and variables for cd-azure.yml"
gh secret set AZURE_TENANT_ID -R "$repo" --body "$(az account show --query tenantId -o tsv)"
gh secret set AZURE_SUBSCRIPTION_ID -R "$repo" --body "$(az account show --query id -o tsv)"
gh secret set AZURE_CLIENT_ID -R "$repo" --env "$ENVIRONMENT" --body "$github_client_id"
gh variable set ACR_NAME -R "$repo" --env "$ENVIRONMENT" --body "$registry"
gh variable set RESOURCE_GROUP -R "$repo" --env "$ENVIRONMENT" --body "$RESOURCE_GROUP"

# --- 7. verify --------------------------------------------------------------------
if [[ "$ENVIRONMENT" == staging ]]; then
  bash "$script_dir/verify-environment.sh" staging
else
  log "Skipping the write-heavy smoke test for production; check $api_url/api/v1/health/ready"
fi

log "$ENVIRONMENT is ready: web $web_url, api $api_url"
log "Next deploys go through cd-azure.yml."
