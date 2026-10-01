#!/usr/bin/env bash
# Blue/green rollout of one container app.
#
#   scripts/azure/deploy-revision.sh <staging|production> <api|web> <image> <revision-suffix>
#
#   1. Pin 100% of traffic to the revision serving now (if any).
#   2. Create a new revision from <image>. It gets 0% traffic.
#   3. Wait until it is provisioned, then health-check it on its own revision
#      URL (api: /api/v1/health/ready, which also proves DB access).
#   4. Only then shift 100% of traffic to it.
#   5. Keep the previous revision active for instant rollback
#      (scripts/azure/rollback.sh) and deactivate anything older, so production
#      doesn't pay for warm replicas of stale revisions.
#
# If the new revision never becomes healthy it is deactivated and traffic
# never moves.

source "$(dirname "$0")/lib.sh"

[[ $# -eq 4 ]] || die "usage: $0 <staging|production> <api|web> <image> <revision-suffix>"
rentflow_env "$1"
component=$2
image=$3
suffix=$4

case "$component" in
  api)
    app=$API_APP
    health_path=/api/v1/health/ready
    healthy_codes='^200$'
    ;;
  web)
    app=$WEB_APP
    health_path=/
    # The landing page may redirect to /login.
    healthy_codes='^(200|30[1278])$'
    ;;
  *) die "component must be 'api' or 'web'" ;;
esac
[[ "$suffix" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ && "$suffix" != *--* ]] ||
  die "revision suffix must be lowercase alphanumerics/dashes and start with a letter"

new_revision="$app--$suffix"
previous_revision=$(serving_revision "$app")
gh_output "${component}_previous_revision" "$previous_revision"
gh_output "${component}_new_revision" "$new_revision"

if [[ -n "$previous_revision" ]]; then
  log "Pinning traffic to the serving revision $previous_revision"
  az containerapp ingress traffic set -n "$app" -g "$RESOURCE_GROUP" \
    --revision-weight "$previous_revision=100" -o none
fi

log "Creating $new_revision from $image (0% traffic)"
az containerapp update -n "$app" -g "$RESOURCE_GROUP" \
  --image "$image" --revision-suffix "$suffix" -o none

abandon() {
  warn "$1"
  az containerapp revision deactivate -n "$app" -g "$RESOURCE_GROUP" \
    --revision "$new_revision" -o none || true
  die "$new_revision was not promoted; traffic stays on ${previous_revision:-<none>}"
}

log "Waiting for $new_revision to provision"
deadline=$((SECONDS + 600))
while :; do
  state=$(az containerapp revision show -n "$app" -g "$RESOURCE_GROUP" \
    --revision "$new_revision" --query properties.provisioningState -o tsv)
  [[ "$state" == Provisioned ]] && break
  [[ "$state" == Failed ]] && abandon "$new_revision failed to provision"
  ((SECONDS < deadline)) || abandon "$new_revision still '$state' after 10 minutes"
  sleep 10
done

fqdn=$(az containerapp revision show -n "$app" -g "$RESOURCE_GROUP" \
  --revision "$new_revision" --query properties.fqdn -o tsv)
url="https://$fqdn$health_path"
log "Health-checking $url before it takes traffic"
# Scale-to-zero revisions cold-start on the first request; allow a few minutes.
deadline=$((SECONDS + 300))
code=000
while ((SECONDS < deadline)); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$url" || true)
  if [[ "$code" =~ $healthy_codes ]]; then
    break
  fi
  sleep 10
done
[[ "$code" =~ $healthy_codes ]] || abandon "$url answered HTTP $code"
log "$url answered HTTP $code"

log "Shifting 100% of traffic to $new_revision"
az containerapp ingress traffic set -n "$app" -g "$RESOURCE_GROUP" \
  --revision-weight "$new_revision=100" -o none

# Keep the new and previous revisions; deactivate the rest.
mapfile -t active < <(az containerapp revision list -n "$app" -g "$RESOURCE_GROUP" \
  --query "[?properties.active].name" -o tsv)
for revision in "${active[@]}"; do
  if [[ "$revision" != "$new_revision" && "$revision" != "$previous_revision" ]]; then
    log "Deactivating old revision $revision"
    az containerapp revision deactivate -n "$app" -g "$RESOURCE_GROUP" \
      --revision "$revision" -o none || warn "could not deactivate $revision"
  fi
done

log "$app now serves $new_revision (rollback target: ${previous_revision:-none})"
