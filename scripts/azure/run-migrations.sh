#!/usr/bin/env bash
# Run `alembic upgrade head` as a one-off Container Apps job and wait for it.
#
#   scripts/azure/run-migrations.sh <staging|production> <api-image>
#
# Points the migration job at the api image being deployed, starts one
# execution, and exits non-zero unless it succeeds. cd-azure.yml runs this
# before any new api revision exists, so a failed migration stops the deploy
# while the previous release keeps serving traffic.
#
# Migrations must be backward compatible with the release still running
# (docs/deployment.md §Deployment sequence).

source "$(dirname "$0")/lib.sh"

[[ $# -eq 2 ]] || die "usage: $0 <staging|production> <api-image>"
rentflow_env "$1"
image=$2
timeout_seconds=${MIGRATION_TIMEOUT_SECONDS:-900}

log "Pointing $MIGRATE_JOB at $image"
az containerapp job update -n "$MIGRATE_JOB" -g "$RESOURCE_GROUP" --image "$image" -o none

log "Starting migration job"
execution=$(az containerapp job start -n "$MIGRATE_JOB" -g "$RESOURCE_GROUP" --query name -o tsv)
[[ -n "$execution" ]] || die "job start returned no execution name"
gh_output migration_execution "$execution"

deadline=$((SECONDS + timeout_seconds))
status=""
while ((SECONDS < deadline)); do
  status=$(az containerapp job execution show -n "$MIGRATE_JOB" -g "$RESOURCE_GROUP" \
    --job-execution-name "$execution" --query properties.status -o tsv)
  case "$status" in
    Succeeded)
      log "Migrations applied ($execution)"
      exit 0
      ;;
    Failed | Stopped | Degraded)
      break
      ;;
  esac
  sleep 10
done

warn "Migration execution $execution ended with status '${status:-timeout}'."
warn "Logs (Log Analytics workspace log-rentflow-$ENV_SHORT):"
warn "  ContainerAppConsoleLogs_CL | where ContainerGroupName_s startswith '$execution' | project TimeGenerated, Log_s"
die "migrations did not succeed; the deploy stops here and traffic is unchanged"
