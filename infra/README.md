# Infrastructure

Azure infrastructure as code, written in Bicep. Nothing is created by hand in the portal — if it isn't defined here, it doesn't exist.

## Layout

```
infra/
├── main.bicep              Subscription-scope entry point
├── modules/
│   ├── container-apps.bicep    Container Apps environment + web/api apps
│   ├── postgres.bicep          PostgreSQL Flexible Server + firewall rules
│   ├── storage.bicep           Blob Storage account + documents container
│   ├── keyvault.bicep          Key Vault + access policies
│   ├── monitoring.bicep        Log Analytics + Application Insights
│   └── identity.bicep          Managed identities and role assignments
└── env/
    ├── staging.bicepparam
    └── production.bicepparam
```

## Usage

```bash
az deployment sub create \
  --location canadacentral \
  --template-file infra/main.bicep \
  --parameters infra/env/staging.bicepparam
```

Preview before applying:

```bash
az deployment sub what-if \
  --location canadacentral \
  --template-file infra/main.bicep \
  --parameters infra/env/staging.bicepparam
```

## Conventions

- Resource names: `<type>-rentflow-<env>` (e.g. `ca-rentflow-api-prod`).
- Secrets are never parameters — they live in Key Vault and are referenced by managed identity.
- Every resource is tagged with `project=rentflow`, `env=<environment>`, `managedBy=bicep`.

## TODO

- [ ] Write `main.bicep` and the module files
- [ ] Set up the OIDC federated credential for the GitHub Actions deploy
- [ ] Decide on region and SKUs per environment
- [ ] Configure PostgreSQL backups and retention
- [ ] Add private networking between Container Apps and PostgreSQL
