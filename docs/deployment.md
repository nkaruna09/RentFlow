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
| `cd-azure.yml` | Push to `main`, manual dispatch | Build images, push to ACR, run migrations, deploy revisions |

Authentication to Azure uses OIDC federated credentials — no long-lived secrets in GitHub.

### Required GitHub secrets / variables

| Name | Kind | Description |
| --- | --- | --- |
| `AZURE_CLIENT_ID` | secret | App registration for the OIDC federated credential |
| `AZURE_TENANT_ID` | secret | Entra tenant |
| `AZURE_SUBSCRIPTION_ID` | secret | Target subscription |
| `ACR_NAME` | variable | Container registry name |
| `RESOURCE_GROUP` | variable | Target resource group |

## Deployment sequence

1. CI passes on `main`.
2. Build and push `rentflow-api` and `rentflow-web` images tagged with the commit SHA.
3. Run `alembic upgrade head` as a one-off Container Apps job — **before** the new revision takes traffic.
4. Deploy the new `api` revision, then the new `web` revision.
5. Verify `/health/ready` returns 200 on the new revision.

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
