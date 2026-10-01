// Container Apps environment plus the web and api apps.
//
//   cae-rentflow-<env>             environment, VNet-integrated (snet-container-apps)
//   ca-rentflow-api-<env>          FastAPI, port 8000, external HTTPS ingress
//   ca-rentflow-web-<env>          Next.js, port 3000, external HTTPS ingress
//   caj-rentflow-migrate-<env>     manual job: `alembic upgrade head`, started by
//                                  cd-azure.yml before a new api revision takes traffic
//
// Both apps run in *multiple* revision mode so a deploy can bring up a new
// revision, health-check it on its own revision URL with 0% traffic, and only
// then shift traffic (cd-azure.yml). Rollback is shifting traffic back to the
// previous revision (scripts/azure/rollback.sh).
//
// Images: cd-azure.yml owns the running image tags. Re-running this template
// sets the images you pass in (scripts/azure/deploy-infra.sh passes the
// currently running ones), so an infra change never silently rolls back the app.

@description('Azure region for the environment and apps.')
param location string

@description('Short environment name used in resource names, e.g. staging or prod.')
param environmentName string

@description('Value of the ENVIRONMENT setting passed to the app: staging or production.')
@allowed([
  'staging'
  'production'
])
param appEnvironment string

@description('Tags applied to every resource.')
param tags object

@description('Create the api, web and migration job. False on the very first deploy, before any image exists in the registry.')
param deployApps bool = true

@description('Log Analytics workspace that receives container logs.')
param logAnalyticsWorkspaceName string

@description('Subnet delegated to Microsoft.App/environments (network.bicep).')
param infrastructureSubnetId string

@description('Registry login server, e.g. crrentflowstaging.azurecr.io.')
param registryLoginServer string

@description('Full image reference for the api and migration job.')
param apiImage string

@description('Full image reference for the web app.')
param webImage string

@description('Resource ID of the api user-assigned identity.')
param apiIdentityId string

@description('Client ID of the api identity (AZURE_CLIENT_ID for DefaultAzureCredential).')
param apiClientId string

@description('Name of the api identity; it is also the PostgreSQL login name.')
param apiIdentityName string

@description('Resource ID of the web user-assigned identity.')
param webIdentityId string

@description('Key Vault URI the api reads secrets from.')
param keyVaultUri string

@description('Blob endpoint of the documents storage account.')
param storageBlobEndpoint string

@description('Blob container for documents.')
param storageContainerName string

@description('Application Insights connection string (not a secret: send-only).')
param appInsightsConnectionString string

@description('PostgreSQL server FQDN.')
param postgresFqdn string

@description('PostgreSQL database name.')
param postgresDatabaseName string

@description('Minimum replicas. 0 = scale to zero when idle (staging); 1+ keeps production warm.')
@minValue(0)
param minReplicas int = 0

@description('Maximum replicas per app.')
@minValue(1)
param maxReplicas int = 3

@description('Concurrent HTTP requests per replica before scaling out.')
param concurrentRequests int = 50

var apiName = 'ca-rentflow-api-${environmentName}'
var webName = 'ca-rentflow-web-${environmentName}'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-rentflow-${environmentName}'
  location: location
  tags: tags
  properties: {
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: false
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

var defaultDomain = managedEnvironment.properties.defaultDomain
var apiUrl = 'https://${apiName}.${defaultDomain}'
var webUrl = 'https://${webName}.${defaultDomain}'

// Shared by the api and the migration job.
var apiEnv = [
  { name: 'ENVIRONMENT', value: appEnvironment }
  { name: 'LOG_LEVEL', value: 'INFO' }
  { name: 'AZURE_CLIENT_ID', value: apiClientId }
  { name: 'AZURE_KEY_VAULT_URL', value: keyVaultUri }
  { name: 'AZURE_STORAGE_ACCOUNT_URL', value: storageBlobEndpoint }
  { name: 'AZURE_STORAGE_CONTAINER', value: storageContainerName }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
  // No password: DATABASE_ENTRA_AUTH makes the app sign in with an Entra token.
  { name: 'DATABASE_URL', value: 'postgresql+asyncpg://${apiIdentityName}@${postgresFqdn}:5432/${postgresDatabaseName}?ssl=require' }
  { name: 'DATABASE_ENTRA_AUTH', value: 'true' }
  { name: 'BACKEND_CORS_ORIGINS', value: '["${webUrl}"]' }
]

resource api 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: apiName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${apiIdentityId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Multiple'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: registryLoginServer
          identity: apiIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: apiEnv
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/api/v1/health/live'
                port: 8000
              }
              periodSeconds: 3
              failureThreshold: 20
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/v1/health/live'
                port: 8000
              }
              periodSeconds: 30
            }
            {
              // A revision only receives traffic once it can reach the database.
              type: 'Readiness'
              httpGet: {
                path: '/api/v1/health/ready'
                port: 8000
              }
              periodSeconds: 10
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http'
            http: {
              metadata: {
                concurrentRequests: string(concurrentRequests)
              }
            }
          }
        ]
      }
    }
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = if (deployApps) {
  name: webName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${webIdentityId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Multiple'
      ingress: {
        external: true
        targetPort: 3000
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: registryLoginServer
          identity: webIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: webImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          probes: [
            {
              type: 'Liveness'
              tcpSocket: {
                port: 3000
              }
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              tcpSocket: {
                port: 3000
              }
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http'
            http: {
              metadata: {
                concurrentRequests: string(concurrentRequests)
              }
            }
          }
        ]
      }
    }
  }
}

resource migrateJob 'Microsoft.App/jobs@2024-03-01' = if (deployApps) {
  name: 'caj-rentflow-migrate-${environmentName}'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${apiIdentityId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaTimeout: 600
      // A failed migration must stop the deploy, not be retried blindly.
      replicaRetryLimit: 0
      registries: [
        {
          server: registryLoginServer
          identity: apiIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'migrate'
          image: apiImage
          command: [
            'alembic'
            'upgrade'
            'head'
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: apiEnv
        }
      ]
    }
  }
}

output environmentName string = managedEnvironment.name
output defaultDomain string = defaultDomain
output apiAppName string = apiName
output webAppName string = webName
output migrateJobName string = 'caj-rentflow-migrate-${environmentName}'
output apiUrl string = apiUrl
output webUrl string = webUrl
