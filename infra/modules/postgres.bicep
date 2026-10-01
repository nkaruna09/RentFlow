// PostgreSQL Flexible Server, database, firewall and backup policy.
//
// Networking: private access only (see network.bicep). The server has no public
// endpoint; the NSG on its delegated subnet admits 5432 from the Container Apps
// subnet only.
//
// Authentication: Microsoft Entra ID only, with password auth disabled. The api
// managed identity is the Entra administrator, so the app and the migration job
// sign in with a short-lived token (backend/app/db/session.py). No database
// password exists anywhere, which keeps the "secrets are never parameters" rule.
//
// Backups: automatic daily snapshots + WAL, restorable to any point within
// backupRetentionDays. Production also keeps geo-redundant copies.

@description('Azure region for the server.')
param location string

@description('Deployment environment name, e.g. staging or production.')
param environmentName string

@description('Tags applied to every resource.')
param tags object

@description('Optional suffix for globally unique names, used only if the default name is taken.')
param globalNameSuffix string = ''

@description('Compute tier.')
@allowed([
  'Burstable'
  'GeneralPurpose'
  'MemoryOptimized'
])
param skuTier string = 'Burstable'

@description('Compute size, e.g. Standard_B1ms (Burstable) or Standard_D2ds_v5 (GeneralPurpose).')
param skuName string = 'Standard_B1ms'

@description('Major PostgreSQL version (matches docker-compose and CI).')
param postgresVersion string = '16'

@description('Allocated storage in GB. Auto-grow is on, so this is the starting size.')
param storageSizeGB int = 32

@description('Point-in-time restore window in days.')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

@description('Keep geo-redundant backup copies in the paired region. Can only be set when the server is created.')
param geoRedundantBackup bool = false

@description('Delegated subnet for the server (network.bicep).')
param delegatedSubnetId string

@description('Private DNS zone linked to the VNet (network.bicep).')
param privateDnsZoneId string

@description('Object (principal) ID of the managed identity made Entra administrator.')
param adminPrincipalId string

@description('Name of that managed identity; it is also the PostgreSQL login name.')
param adminPrincipalName string

@description('Application database name.')
param databaseName string = 'rentflow'

// Server names become <name>.postgres.database.azure.com, so they are globally unique.
var serverName = 'psql-rentflow-${environmentName}${globalNameSuffix}'

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    version: postgresVersion
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: geoRedundantBackup ? 'Enabled' : 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: delegatedSubnetId
      privateDnsZoneArmResourceId: privateDnsZoneId
      publicNetworkAccess: 'Disabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenant().tenantId
    }
  }
}

resource entraAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2024-08-01' = {
  parent: server
  name: adminPrincipalId
  properties: {
    principalType: 'ServicePrincipal'
    principalName: adminPrincipalName
    tenantId: tenant().tenantId
  }
}

// Azure only allows CREATE EXTENSION for allow-listed extensions. The Alembic
// migrations create citext (users.email) and btree_gist (lease overlap constraint).
resource allowedExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: server
  name: 'azure.extensions'
  properties: {
    value: 'BTREE_GIST,CITEXT'
    source: 'user-override'
  }
  dependsOn: [
    entraAdmin
  ]
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: server
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
  // Server-level child operations must run one at a time.
  dependsOn: [
    allowedExtensions
  ]
}

output serverName string = server.name
output serverFqdn string = server.properties.fullyQualifiedDomainName
output databaseName string = database.name
