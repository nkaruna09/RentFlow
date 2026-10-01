#!/usr/bin/env bash
# Shift traffic back to a previous revision (docs/deployment.md §Rollback).
#
#   scripts/azure/rollback.sh <staging|production> <api|web> [revision]
#
# Without [revision], targets the most recent revision other than the one
# serving now. deploy-revision.sh keeps that revision active after every deploy,
# so the shift is instant. Older revisions are re-activated first if needed.
# Traffic only moves once the target answers its health check on its own URL.
#
# This does NOT undo database migrations. Check that the target release works
# with the current schema (migrations are backward compatible by policy), and
# only run `alembic downgrade` after confirming it is safe for that revision.

source "$(dirname "$0")/lib.sh"

[[ $# -ge 2 ]] || die "usage: $0 <staging|production> <api|web> [revision]"
rentflow_env "$1"
case "$2" in
  api) app=$API_APP; health_path=/api/v1/health/ready; healthy='^200$' ;;
  web) app=$WEB_APP; health_path=/; healthy='^(200|30[1278])$' ;;
  *) die "component must be 'api' or 'web'" ;;
esac

serving=$(serving_revision "$app")
target=${3:-}
if [[ -z "$target" ]]; then
  target=$(az containerapp revision list -n "$app" -g "$RESOURCE_GROUP" --all \
    --query "sort_by([?name != '$serving'], &properties.createdTime)[-1].name" -o tsv)
fi
[[ -n "$target" ]] || die "no earlier revision of $app to roll back to"
[[ "$target" != "$serving" ]] || die "$target is already serving"

log "$app: rolling back $serving -> $target"
active=$(az containerapp revision show -n "$app" -g "$RESOURCE_GROUP" --revision "$target" \
  --query properties.active -o tsv)
if [[ "$active" != true ]]; then
  log "Re-activating $target"
  az containerapp revision activate -n "$app" -g "$RESOURCE_GROUP" --revision "$target" -o none
fi

url="https://$(az containerapp revision show -n "$app" -g "$RESOURCE_GROUP" --revision "$target" \
  --query properties.fqdn -o tsv)$health_path"
code=000
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$url" || true)
  [[ "$code" =~ $healthy ]] && break
  sleep 10
done
[[ "$code" =~ $healthy ]] || die "$url answered HTTP $code; traffic left on $serving"

az containerapp ingress traffic set -n "$app" -g "$RESOURCE_GROUP" --revision-weight "$target=100" -o none
log "$app now serves $target (was $serving). To undo: $0 $ENVIRONMENT $2 $serving"
