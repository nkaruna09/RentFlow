# Deployment

> Template. Fill in resource names, subscription and tenant IDs as the Azure environment is provisioned.

## Environments

| Environment | Branch | Resource group | Notes |
| --- | --- | --- | --- |
| Local | any | — | Docker Compose |
| Staging | `develop` | `rg-rentflow-staging` | Auto-deploys on merge |
| Production | `main` | `rg-rentflow-prod` | Deploys on tag, with manual approval |

## Azure resources

| Resource | Purpose |
| --- | --- |
| Azure Container Apps | Hosts the `web` and `api` containers, scale-to-zero on staging |
| Azure Container Registry | Stores built images |
| Azure Database for PostgreSQL Flexible Server | Primary datastore |
| Azure Blob Storage | Lease PDFs, receipts, maintenance photos |
| Azure Key Vault | Secrets, referenced by Container Apps via managed identity |
| Azure Communication Services | Transactional email and SMS |
| Application Insights + Log Analytics | Telemetry and structured logs |

Infrastructure lives in [`infra/`](../infra) as Bicep. Nothing is created by hand in the portal — if it isn't in `infra/`, it doesn't exist.

## Pipelines

| Workflow | Trigger | Does |
| --- | --- | --- |
| `ci-frontend.yml` | PR / push touching `frontend/**` | Lint, typecheck, test, build |
| `ci-backend.yml` | PR / push touching `backend/**` | Ruff, mypy, pytest against a Postgres service container |
| `cd-azure.yml` | Push to `main` (→ staging), manual dispatch (→ staging or production) | Build images, push to ACR, run migrations, roll out health-checked revisions |

Authentication to Azure uses OIDC federated credentials — no long-lived secrets in GitHub.
The workflow signs in as the `id-rentflow-github-<env>` managed identity, whose
federated credential only trusts jobs running in the matching GitHub Environment
(`repo:nkaruna09/RentFlow:environment:<env>`). A managed identity is used instead
of an Entra app registration because the McMaster tenant doesn't let members create
app registrations. `azure/login` treats both the same way.

Until an environment is provisioned (its GitHub Environment has no settings), the
deploy job skips with a warning instead of failing every push to `main`.

### Required GitHub secrets / variables

`scripts/azure/bootstrap-environment.sh` sets all of these from the deployment outputs.

| Name | Kind | Scope | Description |
| --- | --- | --- | --- |
| `AZURE_TENANT_ID` | secret | repository | Entra tenant |
| `AZURE_SUBSCRIPTION_ID` | secret | repository | Target subscription |
| `AZURE_CLIENT_ID` | secret | environment | Client ID of `id-rentflow-github-<env>` |
| `ACR_NAME` | variable | environment | Container registry name (`crrentflowstaging`) |
| `RESOURCE_GROUP` | variable | environment | Target resource group (`rg-rentflow-staging`) |

## Deployment sequence

`cd-azure.yml`, using `scripts/azure/run-migrations.sh` and `scripts/azure/deploy-revision.sh`:

1. CI passes on `main` (PRs can't merge red; protect `main` to enforce this).
2. Build and push `rentflow-api` and `rentflow-web` images tagged with the commit SHA.
   The web image is built per environment because `NEXT_PUBLIC_API_URL` is inlined at build time.
3. Run `alembic upgrade head` as the one-off `caj-rentflow-migrate-<env>` Container Apps job
   and wait for `Succeeded` — **before** the new revision takes traffic. A failed migration
   stops the deploy; the running release is untouched.
4. Deploy the new `api` revision, then the new `web` revision. For each app:
   1. Pin 100% traffic to the revision serving now.
   2. Create the new revision (suffix `r<sha7>-<attempt>`) at 0% traffic.
   3. Wait for it to provision, then call it on its **own revision URL**:
      `/api/v1/health/ready` must return 200 (proves the DB is reachable).
   4. Shift 100% traffic to it. The previous revision stays active as the rollback
      target, and anything older is deactivated.

   If the health check fails, the new revision is deactivated and traffic never moves.
5. The job summary lists both revisions and the rollback command.

Migrations must be backward compatible with the previous release: add columns before writing to them, drop them a release later. Never combine a destructive migration with the deploy that stops using the column.

## Rollback

```bash
# shift traffic back to the previous Container Apps revision
az containerapp ingress traffic set \
  --name rentflow-api --resource-group rg-rentflow-prod \
  --revision-weight <previous-revision>=100
```

Data migrations are not automatically reversible — check `alembic downgrade` is safe for the revision in question before running it.

## Local development

```bash
docker compose up --build     # start web, api, postgres
docker compose logs -f api    # tail the API
docker compose down -v        # stop and wipe the local database volume
```
