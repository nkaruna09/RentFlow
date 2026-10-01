#!/usr/bin/env bash
# Smoke-test a deployed environment end to end (scripts/azure/smoke_test.py).
#
#   scripts/azure/verify-environment.sh staging
#
# Resolves the api/web URLs from the container apps and runs the checks. It
# creates a throwaway account and a little data, so it refuses production
# unless ALLOW_PRODUCTION_SMOKE_TEST=1.

source "$(dirname "$0")/lib.sh"

[[ $# -eq 1 ]] || die "usage: $0 <staging|production>"
rentflow_env "$1"
if [[ "$ENVIRONMENT" == production && "${ALLOW_PRODUCTION_SMOKE_TEST:-}" != 1 ]]; then
  die "the smoke test writes data; set ALLOW_PRODUCTION_SMOKE_TEST=1 to run it against production"
fi

fqdn() {
  az containerapp show -n "$1" -g "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn -o tsv
}
api_url="https://$(fqdn "$API_APP")"
web_url="https://$(fqdn "$WEB_APP")"

log "Smoke-testing $ENVIRONMENT: $api_url  $web_url"
python_bin=$(command -v python3 || command -v python) || die "python is required"
"$python_bin" "$(dirname "$0")/smoke_test.py" --api-url "$api_url" --web-url "$web_url"
