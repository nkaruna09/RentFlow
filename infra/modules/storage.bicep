// Storage account and the rentflow-documents blob container.
//
// Access is Entra ID only: shared-key (account key / connection string) auth is
// disabled, so the API reaches blobs through its managed identity with the
// Storage Blob Data Contributor role (granted in identity.bicep). Uploads and
// downloads are proxied through the API, so the container is never public.

@description('Azure region for the storage account.')
param location string

@description('Deployment environment name, e.g. staging or production.')
param environmentName string

@description('Tags applied to every resource.')
param tags object

@description('Replication SKU. LRS is enough for staging; production should use ZRS.')
@allowed([
  'Standard_LRS'
  'Standard_ZRS'
  'Standard_GRS'
  'Standard_GZRS'
])
param skuName string = 'Standard_LRS'

@description('Days a deleted blob or container stays recoverable.')
@minValue(1)
@maxValue(365)
param softDeleteRetentionDays int = 7

@description('Name of the private blob container holding uploaded documents.')
param containerName string = 'rentflow-documents'

// Storage account names are 3-24 lowercase letters/digits with no dashes, so the
// <type>-rentflow-<env> convention becomes st + rentflow + env (e.g. strentflowstaging).
var accountName = take(toLower('strentflow${replace(environmentName, '-', '')}'), 24)

resource account 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: skuName
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: account
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: softDeleteRetentionDays
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: softDeleteRetentionDays
    }
  }
}

resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}

output accountName string = account.name
output accountId string = account.id
output blobEndpoint string = account.properties.primaryEndpoints.blob
output containerName string = documentsContainer.name
