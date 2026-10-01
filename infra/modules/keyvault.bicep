// Key Vault and role assignments for the app managed identities.
//
// The vault uses Azure RBAC rather than legacy access policies. The API's
// managed identity is granted "Key Vault Secrets User" (read-only) in
// identity.bicep; at startup backend/app/core/config.py reads the secrets listed
// in KEY_VAULT_SECRETS with that identity.
//
// Secret *values* are never Bicep parameters. They are written once by
// scripts/azure/bootstrap-secrets.sh (e.g. a freshly generated JWT signing key),
// by a human who is granted "Key Vault Secrets Officer" here.

@description('Azure region for the vault.')
param location string

@description('Deployment environment name, e.g. staging or production.')
param environmentName string

@description('Tags applied to every resource.')
param tags object

@description('Optional suffix for globally unique names, used only if the default name is taken.')
param globalNameSuffix string = ''

@description('Block permanent deletion during the retention period. Cannot be turned off once enabled, so leave it off for throwaway staging vaults.')
param enablePurgeProtection bool = false

@description('Days a deleted vault or secret can be recovered.')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 90

@description('Object ID of a person or group allowed to write secrets (runs bootstrap-secrets.sh). Empty to skip.')
param vaultAdminPrincipalId string = ''

@description('Principal type of vaultAdminPrincipalId.')
@allowed([
  'User'
  'Group'
])
param vaultAdminPrincipalType string = 'User'

// Key Vault names: 3-24 characters, letters/digits/dashes, globally unique.
var vaultName = take('kv-rentflow-${environmentName}${globalNameSuffix}', 24)

// Built-in role: Key Vault Secrets Officer.
var secretsOfficerRoleId = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: softDeleteRetentionInDays
    // Bicep can't set purge protection back to false, so omit it instead.
    enablePurgeProtection: enablePurgeProtection ? true : null
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource vaultAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(vaultAdminPrincipalId)) {
  name: guid(vault.id, vaultAdminPrincipalId, secretsOfficerRoleId)
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsOfficerRoleId)
    principalId: vaultAdminPrincipalId
    principalType: vaultAdminPrincipalType
  }
}

output vaultName string = vault.name
output vaultId string = vault.id
output vaultUri string = vault.properties.vaultUri
