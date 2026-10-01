// Virtual network shared by the Container Apps environment and PostgreSQL.
//
// PostgreSQL uses private access (VNet integration): it has no public endpoint
// and is reachable only from inside this VNet. The NSG on its subnet narrows
// that further to the Container Apps subnet on 5432. Classic server firewall
// rules don't apply to private-access servers, so the NSG plays that role.
//
//   10.40.0.0/16  vnet-rentflow-<env>
//   ├─ 10.40.0.0/23  snet-container-apps  (delegated to Microsoft.App/environments)
//   └─ 10.40.2.0/24  snet-postgres        (delegated to PostgreSQL flexible servers)

@description('Azure region for the network.')
param location string

@description('Deployment environment name, e.g. staging or production.')
param environmentName string

@description('Tags applied to every resource.')
param tags object

@description('VNet address space.')
param addressPrefix string = '10.40.0.0/16'

@description('Container Apps infrastructure subnet (workload-profiles environments need at least /27).')
param containerAppsSubnetPrefix string = '10.40.0.0/23'

@description('PostgreSQL delegated subnet.')
param postgresSubnetPrefix string = '10.40.2.0/24'

resource postgresNsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: 'nsg-rentflow-postgres-${environmentName}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'allow-postgres-from-container-apps'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: containerAppsSubnetPrefix
          sourcePortRange: '*'
          destinationAddressPrefix: postgresSubnetPrefix
          destinationPortRange: '5432'
        }
      }
      {
        name: 'deny-other-vnet-inbound'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: postgresSubnetPrefix
          destinationPortRange: '*'
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: 'vnet-rentflow-${environmentName}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }
    subnets: [
      {
        name: 'snet-container-apps'
        properties: {
          addressPrefix: containerAppsSubnetPrefix
          delegations: [
            {
              name: 'container-apps'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'snet-postgres'
        properties: {
          addressPrefix: postgresSubnetPrefix
          networkSecurityGroup: {
            id: postgresNsg.id
          }
          delegations: [
            {
              name: 'postgres-flexible'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
    ]
  }

  resource containerAppsSubnet 'subnets' existing = {
    name: 'snet-container-apps'
  }

  resource postgresSubnet 'subnets' existing = {
    name: 'snet-postgres'
  }
}

// Private DNS for the server's private IP; the zone must end in postgres.database.azure.com.
resource postgresDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'rentflow-${environmentName}.private.postgres.database.azure.com'
  location: 'global'
  tags: tags
}

resource postgresDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: postgresDnsZone
  name: 'link-${vnet.name}'
  location: 'global'
  tags: tags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

output vnetId string = vnet.id
output containerAppsSubnetId string = vnet::containerAppsSubnet.id
output postgresSubnetId string = vnet::postgresSubnet.id
// Consumers of these outputs wait for the whole module, including the VNet link.
output postgresDnsZoneId string = postgresDnsZone.id
