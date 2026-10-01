// User-assigned managed identities and RBAC role assignments.
//
//   id-rentflow-api-<env>     api container app + migration job
//                             Key Vault Secrets User   (vault)
//                             Storage Blob Data Contributor (documents container)
//                             AcrPull                  (registry)
//                             + Entra administrator on PostgreSQL (postgres.bicep)
//   id-rentflow-web-<env>     web container app
//                             AcrPull                  (registry)
//   id-rentflow-github-<env>  GitHub Actions deploys (cd-azure.yml), via an OIDC
//                             federated credential. No client secret exists.
//                             AcrPush                  (registry)
//                             Container Apps Contributor (resource group)
//
// The GitHub identity is a managed identity rather than an Entra app
// registration because the tenant does not let members create app
// registrations. azure/login treats both the same way: client-id + OIDC.

@description('Azure region for the identities.')
param location string

@description('Deployment environment name, e.g. staging or production.')
param environmentName string

@description('Tags applied to every resource.')
param tags object

@description('Key Vault the api identity reads secrets from.')
param keyVaultName string

@description('Storage account holding the documents container.')
param storageAccountName string

@description('Blob container the api identity may read and write.')
param documentsContainerName string

@description('Container registry the apps pull from and GitHub pushes to.')
param registryName string

@description('GitHub repository allowed to deploy, as owner/name.')
param githubRepository string

@description('GitHub Environment whose jobs may use the deploy identity (the federated credential subject).')
param githubEnvironment string

// Built-in role definition IDs.
var roles = {
  keyVaultSecretsUser: '4633458b-17de-408a-b874-0445c86b69e6'
  storageBlobDataContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  acrPush: '8311e382-0749-4cb8-b61a-304f252e45ec'
  containerAppsContributor: '358470bc-b998-42bd-ab17-a7e34c199c0f'
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName

  resource blobService 'blobServices' existing = {
    name: 'default'

    resource documents 'containers' existing = {
      name: documentsContainerName
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

resource apiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-rentflow-api-${environmentName}'
  location: location
  tags: tags
}

resource webIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-rentflow-web-${environmentName}'
  location: location
  tags: tags
}

resource githubIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-rentflow-github-${environmentName}'
  location: location
  tags: tags
}

resource githubFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: githubIdentity
  name: 'github-${githubEnvironment}'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepository}:environment:${githubEnvironment}'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

// --- api ---------------------------------------------------------------------

resource apiKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, apiIdentity.id, roles.keyVaultSecretsUser)
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.keyVaultSecretsUser)
    principalId: apiIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource apiBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount::blobService::documents.id, apiIdentity.id, roles.storageBlobDataContributor)
  scope: storageAccount::blobService::documents
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.storageBlobDataContributor)
    principalId: apiIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource apiAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, apiIdentity.id, roles.acrPull)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.acrPull)
    principalId: apiIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- web ---------------------------------------------------------------------

resource webAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, webIdentity.id, roles.acrPull)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.acrPull)
    principalId: webIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// --- GitHub Actions deploy -----------------------------------------------------

resource githubAcrPush 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, githubIdentity.id, roles.acrPush)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.acrPush)
    principalId: githubIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource githubContainerAppsContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, githubIdentity.id, roles.containerAppsContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.containerAppsContributor)
    principalId: githubIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output apiIdentityId string = apiIdentity.id
output apiIdentityName string = apiIdentity.name
output apiClientId string = apiIdentity.properties.clientId
output apiPrincipalId string = apiIdentity.properties.principalId
output webIdentityId string = webIdentity.id
output webClientId string = webIdentity.properties.clientId
output githubClientId string = githubIdentity.properties.clientId
output githubIdentityName string = githubIdentity.name
