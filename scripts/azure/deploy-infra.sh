#!/usr/bin/env bash
# Preview and apply infra/main.bicep for one environment.
#
#   scripts/azure/deploy-infra.sh <staging|production> [--yes] [--what-if-only]
#
# Always runs `az deployment sub what-if` first and asks before applying
# (--yes skips the prompt). Passes in the images that are *currently running*,
# so re-applying infrastructure never rolls the app back. Override with
# API_IMAGE / WEB_IMAGE. If the apps don't exist yet and no images are given,
# it deploys everything except the apps (DEPLOY_APPS=false), which is the first
# step of scripts/azure/bootstrap-environment.sh.

source "$(dirname "$0")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <staging|production> [--yes] [--what-if-only]"
rentflow_env "$1"
shift
assume_yes=false
what_if_only=false
for arg in "$@"; do
  case "$arg" in
    --yes) assume_yes=true ;;
    --what-if-only) what_if_only=true ;;
    *) die "unknown option $arg" ;;
  esac
done

repo_root=$(cd "$(dirname "$0")/../.." && pwd)
location=canadacentral

state=$(az account show --query state -o tsv)
[[ "$state" == Enabled ]] || die "subscription '$(az account show --query name -o tsv)' is $state"

current_image() {
  az containerapp show -n "$1" -g "$RESOURCE_GROUP" \
    --query 'properties.template.containers[0].image' -o tsv 2>/dev/null || true
}

if [[ -z "${API_IMAGE:-}" ]]; then API_IMAGE=$(current_image "$API_APP"); fi
if [[ -z "${WEB_IMAGE:-}" ]]; then WEB_IMAGE=$(current_image "$WEB_APP"); fi
if [[ -n "$API_IMAGE" && -n "$WEB_IMAGE" ]]; then
  DEPLOY_APPS=${DEPLOY_APPS:-true}
else
  warn "no running or supplied images; deploying without the container apps (DEPLOY_APPS=false)"
  DEPLOY_APPS=false
fi
if [[ -z "${VAULT_ADMIN_PRINCIPAL_ID:-}" ]]; then
  VAULT_ADMIN_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)
fi
export API_IMAGE WEB_IMAGE DEPLOY_APPS VAULT_ADMIN_PRINCIPAL_ID
log "environment=$ENVIRONMENT deployApps=$DEPLOY_APPS"
log "api image: ${API_IMAGE:-<none>}"
log "web image: ${WEB_IMAGE:-<none>}"

args=(
  --location "$location"
  --template-file "$repo_root/infra/main.bicep"
  --parameters "$repo_root/infra/env/$ENVIRONMENT.bicepparam"
)

log "What-if (no changes are made)"
az deployment sub what-if "${args[@]}" >&2 || die "what-if failed"
$what_if_only && exit 0

if ! $assume_yes; then
  read -r -p "Apply these changes to $ENVIRONMENT? [y/N] " answer </dev/tty >&2
  [[ "$answer" =~ ^[Yy]$ ]] || die "aborted"
fi

deployment="rentflow-$ENV_SHORT-$(date -u +%Y%m%d%H%M%S)"
log "Applying as deployment $deployment"
az deployment sub create --name "$deployment" "${args[@]}" -o none
az deployment sub show --name "$deployment" --query properties.outputs -o json |
  tee "${DEPLOY_OUTPUTS_FILE:-/dev/null}" >/dev/null
log "Done. Outputs: az deployment sub show --name $deployment --query properties.outputs"
gh_output deployment_name "$deployment"
echo "$deployment"
