// Azure Container Registry for the rentflow-api and rentflow-web images.
//
// The admin user is disabled: Container Apps pull with their managed identity
// (AcrPull) and GitHub Actions pushes with its OIDC identity (AcrPush), both
// granted in identity.bicep.

@description('Azure region for the registry.')
param location string

@description('Deployment environment name, e.g. staging or production.')
param environmentName string

@description('Tags applied to every resource.')
param tags object

@description('Optional suffix for globally unique names, used only if the default name is taken.')
param globalNameSuffix string = ''

@description('Registry SKU. Basic covers this app\'s image volume.')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param skuName string = 'Basic'

// Registry names are 5-50 alphanumerics, globally unique: cr + rentflow + env.
var registryName = take(toLower('crrentflow${replace(environmentName, '-', '')}${globalNameSuffix}'), 50)

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

output registryName string = registry.name
output registryId string = registry.id
output loginServer string = registry.properties.loginServer
