// Tenant endpoint bindings.
import { del, get, patch, post } from "@/lib/api/client";
import type {
  LeaseList,
  Tenant,
  TenantCreate,
  TenantList,
  TenantUpdate,
} from "@/types/api";

export interface TenantListParams {
  page?: number;
  page_size?: number;
}
export function listTenants(params?: TenantListParams): Promise<TenantList> {
  return get<TenantList>("/tenants", params);
}
export function createTenant(input: TenantCreate): Promise<Tenant> {
  return post<Tenant, TenantCreate>("/tenants", input);
}
export function getTenant(id: string): Promise<Tenant> {
  return get<Tenant>(`/tenants/${encodeURIComponent(id)}`);
}
export function updateTenant(id: string, input: TenantUpdate): Promise<Tenant> {
  return patch<Tenant, TenantUpdate>(
    `/tenants/${encodeURIComponent(id)}`,
    input,
  );
}
export function deleteTenant(id: string): Promise<void> {
  return del<void>(`/tenants/${encodeURIComponent(id)}`);
}
export function listTenantLeases(
  id: string,
  params?: TenantListParams,
): Promise<LeaseList> {
  return get<LeaseList>(`/tenants/${encodeURIComponent(id)}/leases`, params);
}
