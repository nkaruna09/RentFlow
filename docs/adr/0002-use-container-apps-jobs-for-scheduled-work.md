# ADR 0002 — Use Azure Container Apps jobs for scheduled work

- **Status:** Accepted
- **Date:** 2026-09-26

## Context

RentFlow needs monthly invoice generation and a daily overdue-rent sweep. These
tasks must run independently of API traffic, survive API scaling and restarts,
and support controlled retries. The application is already deployed to Azure
Container Apps, while its current workload does not otherwise require a message
broker or distributed task queue.

## Decision

Run scheduled work as Azure Container Apps scheduled jobs using the backend
container image. Use separate job definitions and schedules for monthly
invoicing and the daily overdue sweep. Each invokes `python -m
app.workers.scheduler` with its job name, runs with one replica, and receives the
same database configuration and managed identity as the API.

Job handlers accept an explicit run date for deterministic retries and recovery
runs. Invoice periods have a database uniqueness constraint, invoice generation
returns the existing row on a retry, and late-fee application uses a persistent
marker and conditional update. Correctness therefore does not depend on the
scheduler providing exactly-once execution.

## Consequences

- Scheduled work cannot be lost when the API scales to zero or restarts.
- Jobs have independent execution history, logs, retry policy, and resource limits.
- No always-on scheduler process or message broker is required.
- Deployment must provision and monitor two additional Container Apps job resources.
- The monthly job is batch-oriented; event-driven workflows may still justify a
  task queue later.

## Alternatives considered

- **In-process scheduler:** simpler locally, but each API replica could run the
  same task and scale-to-zero would prevent schedules from firing.
- **Task queue:** provides richer routing and high-throughput retries, but adds a
  broker, workers, and operational overhead that two periodic jobs do not need.
