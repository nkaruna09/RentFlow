# Infrastructure

Azure infrastructure as code, written in Bicep. Nothing is created by hand in the portal — if it isn't defined here, it doesn't exist.

## Layout

```
infra/
├── main.bicep              Subscription-scope entry point: resource group + all modules
├── modules/
│   ├── monitoring.bicep        Log Analytics + Application Insights
│   ├── network.bicep           VNet, Container Apps + PostgreSQL subnets, NSG, private DNS
│   ├── storage.bicep           Blob Storage account + rentflow-documents container
│   ├── keyvault.bicep          Key Vault (RBAC mode)
│   ├── registry.bicep          Azure Container Registry
│   ├── identity.bicep          Managed identities, role assignments, GitHub OIDC credential
│   ├── postgres.bicep          PostgreSQL Flexible Server (private, Entra-only auth, backups)
│   └── container-apps.bicep    Container Apps environment, api + web apps, migration job
└── env/
    ├── staging.bicepparam
    └── production.bicepparam
```

Modules deploy in dependency order, which Bicep infers from the outputs each one consumes:

```
monitoring ─┐
network ────┼──────────────────────────────┬─> postgres ──> container-apps
storage ────┤                              │                     ^
keyvault ───┼─> identity (RBAC on these) ──┘─────────────────────┘
registry ───┘
```

## Usage

Preview first. `what-if` lists every create/modify/delete without changing anything:

```bash
az deployment sub what-if \
  --location canadacentral \
  --template-file infra/main.bicep \
  --parameters infra/env/staging.bicepparam
```

Apply with the helper script rather than a bare `az deployment sub create`. The
script passes in the image tags that are **currently running**, so an infra
change never rolls the app back to an old or placeholder image:

```bash
scripts/azure/deploy-infra.sh staging            # what-if, confirm, then create
```

Bringing up a brand-new environment (empty registry, no secrets yet) is a
one-off bootstrap. See `docs/deployment.md` §First-time setup:

```bash
scripts/azure/bootstrap-environment.sh staging
```

## Conventions

- Resource names: `<type>-rentflow-<env>`, with `<env>` = `staging` or `prod`.
  Globally unique names that only allow alphanumerics drop the dashes.
  `globalNameSuffix` (env var `RENTFLOW_NAME_SUFFIX`) is appended when a name is
  already taken. Production uses `nk09` because `strentflowprod` and
  `psql-rentflow-prod` belong to someone else.

  | Resource | Staging | Production |
  | --- | --- | --- |
  | Resource group | `rg-rentflow-staging` | `rg-rentflow-prod` |
  | Container Apps env | `cae-rentflow-staging` | `cae-rentflow-prod` |
  | api / web apps | `ca-rentflow-api-staging`, `ca-rentflow-web-staging` | `ca-rentflow-api-prod`, `ca-rentflow-web-prod` |
  | Migration job | `caj-rentflow-migrate-staging` | `caj-rentflow-migrate-prod` |
  | PostgreSQL | `psql-rentflow-staging` | `psql-rentflow-prodnk09` |
  | Storage account | `strentflowstaging` | `strentflowprodnk09` |
  | Container registry | `crrentflowstaging` | `crrentflowprodnk09` |
  | Key Vault | `kv-rentflow-staging` | `kv-rentflow-prodnk09` |
  | Identities | `id-rentflow-{api,web,github}-staging` | `id-rentflow-{api,web,github}-prod` |
  | Monitoring | `log-rentflow-staging`, `appi-rentflow-staging` | `log-rentflow-prod`, `appi-rentflow-prod` |
  | Network | `vnet-rentflow-staging`, `nsg-rentflow-postgres-staging` | `vnet-rentflow-prod`, `nsg-rentflow-postgres-prod` |

- Secrets are never parameters. They live in Key Vault and are read by managed
  identity. PostgreSQL has no password at all: it uses Entra-only auth.
- Every resource is tagged with `project=rentflow`, `env=<environment>`, `managedBy=bicep`.

## Security model

| Identity | Used by | Can |
| --- | --- | --- |
| `id-rentflow-api-<env>` | api app, migration job | read Key Vault secrets; read/write the `rentflow-documents` container; pull images; Entra admin on PostgreSQL |
| `id-rentflow-web-<env>` | web app | pull images |
| `id-rentflow-github-<env>` | GitHub Actions (`cd-azure.yml`), via OIDC federated credential for the `<env>` GitHub Environment only | push images; manage container apps/jobs in the resource group |

The GitHub deploy identity is a managed identity, not an Entra app
registration, because the McMaster tenant doesn't allow members to create app
registrations. `azure/login` works the same way with either, and no client
secret exists.

## Decisions

- [x] `main.bicep` and the module files
- [x] OIDC federated credential for the GitHub Actions deploy (`identity.bicep`)
- [x] Region: `canadacentral` (the subscription policy also allows eastus, westus2, northcentralus, mexicocentral)
- [x] SKUs per environment: see `env/*.bicepparam`
- [x] PostgreSQL backups and retention: 7 days staging, 35 days + geo-redundant production
- [x] Private networking between Container Apps and PostgreSQL (`network.bicep`)
