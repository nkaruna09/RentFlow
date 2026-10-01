// Parameter values for the staging environment.
//
// Cost-first: burstable PostgreSQL, LRS storage, apps scale to zero when idle.
// Image tags and the vault admin come from environment variables so the same
// file serves the first bootstrap and later infra updates
// (scripts/azure/deploy-infra.sh sets them).
using '../main.bicep'

param environmentName = 'staging'
param location = 'canadacentral'
param globalNameSuffix = readEnvironmentVariable('RENTFLOW_NAME_SUFFIX', '')

param deployApps = bool(readEnvironmentVariable('DEPLOY_APPS', 'true'))
param apiImage = readEnvironmentVariable('API_IMAGE', '')
param webImage = readEnvironmentVariable('WEB_IMAGE', '')
param vaultAdminPrincipalId = readEnvironmentVariable('VAULT_ADMIN_PRINCIPAL_ID', '')

param postgresSkuTier = 'Burstable'
param postgresSkuName = 'Standard_B1ms'
param postgresBackupRetentionDays = 7
param postgresGeoRedundantBackup = false

param storageSkuName = 'Standard_LRS'
param keyVaultPurgeProtection = false

param minReplicas = 0
param maxReplicas = 3

param logRetentionDays = 30
param logDailyQuotaGb = 1
