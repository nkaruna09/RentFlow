// Log Analytics workspace and Application Insights.
//
// Container Apps ships container stdout/stderr to the workspace; the API also
// exports structured logs and request traces to Application Insights through
// APPLICATIONINSIGHTS_CONNECTION_STRING (see backend/app/core/logging.py).

@description('Azure region for the monitoring resources.')
param location string

@description('Deployment environment name, e.g. staging or production.')
param environmentName string

@description('Tags applied to every resource.')
param tags object

@description('Days to keep logs in the workspace. 30 is the free-retention floor.')
@minValue(30)
@maxValue(730)
param retentionInDays int = 30

@description('Daily ingestion cap in GB; -1 disables the cap. Guards the budget if logging runs away.')
param dailyQuotaGb int = -1

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-rentflow-${environmentName}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    workspaceCapping: {
      dailyQuotaGb: dailyQuotaGb
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-rentflow-${environmentName}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    IngestionMode: 'LogAnalytics'
  }
}

output workspaceId string = workspace.id
output workspaceName string = workspace.name
output appInsightsName string = appInsights.name
// Not a secret: the connection string only permits sending telemetry.
output appInsightsConnectionString string = appInsights.properties.ConnectionString
