# Deployment

## Environments

| Environment | Deploys from | Resource group | Notes |
| --- | --- | --- | --- |
| Local | any | — | Docker Compose (web, api, postgres, azurite) |
| Staging | push to `main` | `rg-rentflow-staging` | Auto-deploys on merge; apps scale to zero when idle |
| Production | manual dispatch of `cd-azure.yml` from `main` | `rg-rentflow-prod` | Waits for a required reviewer (`production` GitHub Environment) |

Subscription: **Azure for Students** (`a85aea16-fd68-4d8d-9e75-606247c71820`), tenant
McMaster University (`44376307-b429-42ad-8c25-28cd496f4772`), region `canadacentral`.
A subscription policy restricts deployments to canadacentral, eastus, westus2,
northcentralus and mexicocentral.

## Azure resources

Exact names per environment are in [`infra/README.md`](../infra/README.md#conventions).

| Resource | Name (staging) | Purpose |
| --- | --- | --- |
| Azure Container Apps | `cae-rentflow-staging`, `ca-rentflow-{api,web}-staging` | Hosts the `web` and `api` containers, scale-to-zero on staging |
| Container Apps job | `caj-rentflow-migrate-staging` | Runs `alembic upgrade head` before each rollout |
| Azure Container Registry | `crrentflowstaging` | Stores built images |
| Azure Database for PostgreSQL Flexible Server | `psql-rentflow-staging` | Primary datastore: private network only, Entra-only auth |
| Virtual network | `vnet-rentflow-staging` | Connects Container Apps to PostgreSQL privately |
| Azure Blob Storage | `strentflowstaging` / `rentflow-documents` | Lease PDFs, receipts, maintenance photos (managed identity only) |
| Azure Key Vault | `kv-rentflow-staging` | Secrets, read by the api with its managed identity |
| Managed identities | `id-rentflow-{api,web,github}-staging` | App identities and the GitHub OIDC deploy identity |
| Application Insights + Log Analytics | `appi-rentflow-staging`, `log-rentflow-staging` | Telemetry and structured logs |
| Azure Communication Services | — | Transactional email and SMS (M7; notifications are log-only until then) |

Infrastructure lives in [`infra/`](../infra) as Bicep. Nothing is created by hand in the portal — if it isn't in `infra/`, it doesn't exist.

### Configuration the api receives

Set by `container-apps.bicep`. None of these values is a secret.

| Variable | Value |
| --- | --- |
| `ENVIRONMENT` | `staging` / `production`; the app refuses to start with the placeholder `SECRET_KEY` |
| `AZURE_CLIENT_ID` | api managed identity, used by `DefaultAzureCredential` |
| `AZURE_KEY_VAULT_URL` | vault holding `secret-key` (→ `SECRET_KEY`) |
| `DATABASE_URL` + `DATABASE_ENTRA_AUTH=true` | `postgresql+asyncpg://id-rentflow-api-<env>@<server>:5432/rentflow?ssl=require`, with no password: an Entra token is supplied per connection |
| `AZURE_STORAGE_ACCOUNT_URL`, `AZURE_STORAGE_CONTAINER` | document storage |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | telemetry export |
| `BACKEND_CORS_ORIGINS` | exactly the web app's URL |

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

### Production approval gate

The `production` GitHub Environment (configured by
`scripts/azure/configure-github-environment.sh production`) has:

- **Required reviewer:** `nkaruna09`. Every production deploy pauses at
  "Waiting for review" until approved in the Actions UI.
- **Deployment branches:** `main` only. A dispatch from any other branch is
  rejected before the job starts.

Because the production deploy identity's federated credential trusts only
`environment:production`, a job can't get an Azure token for production without
passing this gate.

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

## First-time setup

Brings an empty subscription to a verified, CD-ready environment. Run once per
environment, from the repo root in Git Bash, logged in with `az login`
(Owner on the subscription) and `gh auth login` (repo admin):

```bash
scripts/azure/deploy-infra.sh staging --what-if-only   # optional: preview everything first
scripts/azure/bootstrap-environment.sh staging
```

The bootstrap:

1. Checks that the subscription is **Enabled** and registers the resource providers.
2. Deploys `infra/main.bicep` without the apps, since the registry is still empty.
3. Generates the JWT signing key straight into Key Vault (`bootstrap-secrets.sh`).
4. Builds the first images with `az acr build`. ACR Tasks is often blocked on
   free-credit subscriptions; the script then falls back to local Docker, so
   start Docker Desktop if it asks.
5. Deploys again with the apps and the migration job, then runs migrations.
6. Configures the GitHub Environment and the five secrets/variables above.
7. Runs `scripts/azure/verify-environment.sh`, an end-to-end smoke test proving the
   M1–M5 app works against the real resources: DB over the private network,
   Key Vault-signed JWTs, CRUD, document upload/download through Blob Storage, and CORS.

Every step is idempotent, so re-run it after fixing whatever stopped it.

Infra changes after that: `scripts/azure/deploy-infra.sh <env>` (always shows a
what-if and asks first; keeps the running images).

Production is the same command with `production` once you're ready to pay for it
(see Costs). Its parameters are already in `infra/env/production.bicepparam`.

## Rollback

Every rollout keeps the previous revision active, so rolling back is a traffic
shift that takes seconds:

```bash
scripts/azure/rollback.sh staging api          # back to the previous api revision
scripts/azure/rollback.sh staging web
scripts/azure/rollback.sh production api ca-rentflow-api-prod--r1a2b3c4-1   # a specific revision
```

The script re-activates the target if needed and health-checks it on its own
URL. It only then shifts 100% of traffic, and it prints the command to undo
the rollback. The underlying Azure CLI call is:

```bash
az containerapp ingress traffic set \
  --name ca-rentflow-api-prod --resource-group rg-rentflow-prod \
  --revision-weight <previous-revision>=100
```

Roll back the api and web together if the release changed the API contract
between them.

Data migrations are not automatically reversible — check `alembic downgrade` is safe for the revision in question before running it.
Because migrations are backward compatible by policy, the previous api revision
runs fine against the newer schema, so a traffic rollback alone is normally enough.

### Rehearsal (staging)

Do this at least once before relying on rollback in production:

1. Note the serving revisions: `az containerapp revision list -n ca-rentflow-api-staging -g rg-rentflow-staging -o table`.
2. Merge any small change to `main` and let `cd-azure.yml` deploy it. The new
   revision serves, and the old one stays active at 0%.
3. `scripts/azure/rollback.sh staging api` and `... web`. Confirm the old
   revisions serve 100% and `scripts/azure/verify-environment.sh staging` passes.
4. Roll forward again with the command the script printed, and re-verify.
5. Record the date and revisions in the M6 PR or issue #54.

## Monitoring

- **Logs:** Log Analytics `log-rentflow-<env>`, table `ContainerAppConsoleLogs_CL`
  (JSON lines from `app/core/logging.py`).
- **Telemetry:** Application Insights `appi-rentflow-<env>` receives `app.*`
  logs and request/dependency traces (health probes excluded).
- **Migration failures:** the deploy log prints a ready-to-run Log Analytics query.

## Costs and teardown

Approximate monthly cost in canadacentral (USD, light use):

| | Staging | Production |
| --- | --- | --- |
| PostgreSQL (B1ms / B2s + 32 GB) | ~$17 | ~$35 + geo-backup storage |
| Container Apps (scale to zero / 1 warm replica each) | ~$0–3 | ~$15–25 |
| Container Registry Basic | ~$5 | ~$5 |
| Key Vault, Storage, Log Analytics, DNS | ~$1–3 | ~$3–8 |
| **Total** | **~$20–25** | **~$55–75** |

PostgreSQL bills while it exists, even when idle. To pause staging without losing data:

```bash
az postgres flexible-server stop -g rg-rentflow-staging -n psql-rentflow-staging   # auto-restarts after 7 days
```

To delete an environment completely (irreversible; Key Vault stays soft-deleted
for 90 days, so recreating it under the same name needs `az keyvault purge`):

```bash
az group delete --name rg-rentflow-staging
```

## Local development

```bash
docker compose up --build     # start web, api, postgres, azurite
docker compose logs -f api    # tail the API
docker compose down -v        # stop and wipe the local database volume
```
