// Parameter values for the production environment.
//
// Durability-first: longer and geo-redundant PostgreSQL backups, zone-redundant
// storage, Key Vault purge protection, and one warm replica per app so the
// first request after idle doesn't pay a cold start.
using '../main.bicep'

param environmentName = 'production'
param location = 'canadacentral'
// strentflowprod and psql-rentflow-prod are already taken globally by someone
// else (checked 2026-09-30), so production names carry a suffix:
// strentflowprodnk09, crrentflowprodnk09, kv-rentflow-prodnk09, psql-rentflow-prodnk09.
param globalNameSuffix = readEnvironmentVariable('RENTFLOW_NAME_SUFFIX', 'nk09')

param deployApps = bool(readEnvironmentVariable('DEPLOY_APPS', 'true'))
param apiImage = readEnvironmentVariable('API_IMAGE', '')
param webImage = readEnvironmentVariable('WEB_IMAGE', '')
param vaultAdminPrincipalId = readEnvironmentVariable('VAULT_ADMIN_PRINCIPAL_ID', '')

param postgresSkuTier = 'Burstable'
param postgresSkuName = 'Standard_B2s'
param postgresBackupRetentionDays = 35
param postgresGeoRedundantBackup = true

param storageSkuName = 'Standard_ZRS'
// Irreversible: deleted vaults/secrets can't be purged early once this is on.
param keyVaultPurgeProtection = true

param minReplicas = 1
param maxReplicas = 5

param logRetentionDays = 90
param logDailyQuotaGb = -1
