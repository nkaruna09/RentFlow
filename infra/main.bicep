// Subscription-scope entry point: creates the resource group and wires every module together.
//
// Naming: <type>-rentflow-<env>, where <env> is `staging` or `prod`
// (e.g. rg-rentflow-staging, ca-rentflow-api-prod). Resources whose names
// must be globally unique and alphanumeric drop the dashes (strentflowprod,
// crrentflowprod). Every resource carries project/env/managedBy tags.
//
// Deploy order (implicit from the module outputs each one consumes):
//   monitoring, network, storage, keyvault, registry
//     -> identity (role assignments on those resources)
//       -> postgres (api identity as Entra admin)
//         -> container-apps
//
// Usage: see infra/README.md. For anything beyond a what-if preview, use
// scripts/azure/deploy-infra.sh, which supplies the running image tags.

targetScope = 'subscription'

@description('Environment being deployed. Matches the GitHub Environment used by cd-azure.yml.')
@allowed([
  'staging'
  'production'
])
param environmentName string

@description('Azure region. The subscription policy allows canadacentral, eastus, westus2, northcentralus and mexicocentral.')
param location string = 'canadacentral'

@description('Optional suffix for globally unique names (storage, registry, Key Vault, PostgreSQL). Only needed if a default name is taken.')
param globalNameSuffix string = ''

@description('GitHub repository allowed to deploy through OIDC, as owner/name.')
param githubRepository string = 'nkaruna09/RentFlow'

@description('Object ID of the person who bootstraps Key Vault secrets (Key Vault Secrets Officer). Empty to skip.')
param vaultAdminPrincipalId string = ''

@description('Create the container apps and migration job. False only on the very first deploy, before images exist.')
param deployApps bool = true

@description('api image to run, e.g. crrentflowstaging.azurecr.io/rentflow-api:<sha>. Required when deployApps is true.')
param apiImage string = ''

@description('web image to run. Required when deployApps is true.')
param webImage string = ''

// --- Per-environment sizing (set in env/*.bicepparam) ---------------------------

@description('PostgreSQL compute tier.')
param postgresSkuTier string = 'Burstable'

@description('PostgreSQL compute size.')
param postgresSkuName string = 'Standard_B1ms'

@description('PostgreSQL point-in-time-restore window in days (7-35).')
param postgresBackupRetentionDays int = 7

@description('Keep geo-redundant PostgreSQL backups. Fixed at server creation.')
param postgresGeoRedundantBackup bool = false

@description('Storage replication SKU.')
param storageSkuName string = 'Standard_LRS'

@description('Key Vault purge protection. Irreversible once enabled.')
param keyVaultPurgeProtection bool = false

@description('Minimum replicas per app; 0 scales to zero when idle.')
param minReplicas int = 0

@description('Maximum replicas per app.')
param maxReplicas int = 3

@description('Log Analytics retention in days.')
param logRetentionDays int = 30

@description('Log Analytics daily ingestion cap in GB (-1 = no cap).')
param logDailyQuotaGb int = -1

var envShort = environmentName == 'production' ? 'prod' : environmentName

var tags = {
  project: 'rentflow'
  env: environmentName
  managedBy: 'bicep'
}

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-rentflow-${envShort}'
  location: location
  tags: tags
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    location: location
    environmentName: envShort
    tags: tags
    retentionInDays: logRetentionDays
    dailyQuotaGb: logDailyQuotaGb
  }
}

module network 'modules/network.bicep' = {
  name: 'network'
  scope: rg
  params: {
    location: location
    environmentName: envShort
    tags: tags
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: location
    environmentName: envShort
    tags: tags
    globalNameSuffix: globalNameSuffix
    skuName: storageSkuName
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  scope: rg
  params: {
    location: location
    environmentName: envShort
    tags: tags
    globalNameSuffix: globalNameSuffix
    enablePurgeProtection: keyVaultPurgeProtection
    vaultAdminPrincipalId: vaultAdminPrincipalId
  }
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  scope: rg
  params: {
    location: location
    environmentName: envShort
    tags: tags
    globalNameSuffix: globalNameSuffix
  }
}

module identity 'modules/identity.bicep' = {
  name: 'identity'
  scope: rg
  params: {
    location: location
    environmentName: envShort
    tags: tags
    keyVaultName: keyVault.outputs.vaultName
    storageAccountName: storage.outputs.accountName
    documentsContainerName: storage.outputs.containerName
    registryName: registry.outputs.registryName
    githubRepository: githubRepository
    githubEnvironment: environmentName
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  scope: rg
  params: {
    location: location
    environmentName: envShort
    tags: tags
    globalNameSuffix: globalNameSuffix
    skuTier: postgresSkuTier
    skuName: postgresSkuName
    backupRetentionDays: postgresBackupRetentionDays
    geoRedundantBackup: postgresGeoRedundantBackup
    delegatedSubnetId: network.outputs.postgresSubnetId
    privateDnsZoneId: network.outputs.postgresDnsZoneId
    adminPrincipalId: identity.outputs.apiPrincipalId
    adminPrincipalName: identity.outputs.apiIdentityName
  }
}

module containerApps 'modules/container-apps.bicep' = {
  name: 'container-apps'
  scope: rg
  params: {
    location: location
    environmentName: envShort
    appEnvironment: environmentName
    tags: tags
    deployApps: deployApps
    logAnalyticsWorkspaceName: monitoring.outputs.workspaceName
    infrastructureSubnetId: network.outputs.containerAppsSubnetId
    registryLoginServer: registry.outputs.loginServer
    apiImage: apiImage
    webImage: webImage
    apiIdentityId: identity.outputs.apiIdentityId
    apiClientId: identity.outputs.apiClientId
    apiIdentityName: identity.outputs.apiIdentityName
    webIdentityId: identity.outputs.webIdentityId
    keyVaultUri: keyVault.outputs.vaultUri
    storageBlobEndpoint: storage.outputs.blobEndpoint
    storageContainerName: storage.outputs.containerName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    postgresFqdn: postgres.outputs.serverFqdn
    postgresDatabaseName: postgres.outputs.databaseName
    minReplicas: minReplicas
    maxReplicas: maxReplicas
  }
}

// Values cd-azure.yml and the scripts need. None of them are secrets.
output resourceGroupName string = rg.name
output registryName string = registry.outputs.registryName
output registryLoginServer string = registry.outputs.loginServer
output keyVaultName string = keyVault.outputs.vaultName
output postgresServerName string = postgres.outputs.serverName
output containerAppsDefaultDomain string = containerApps.outputs.defaultDomain
output apiAppName string = containerApps.outputs.apiAppName
output webAppName string = containerApps.outputs.webAppName
output migrateJobName string = containerApps.outputs.migrateJobName
output apiUrl string = containerApps.outputs.apiUrl
output webUrl string = containerApps.outputs.webUrl
output githubDeployClientId string = identity.outputs.githubClientId
