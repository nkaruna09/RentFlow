// Lease endpoint bindings.
import { get, patch, post } from "@/lib/api/client";
import type {
  Lease,
  LeaseCreate,
  LeaseList,
  LeaseRenewRequest,
  LeaseStatus,
  LeaseTerminateRequest,
  LeaseUpdate,
} from "@/types/api";

export interface LeaseListParams {
  unit_id?: string;
  tenant_id?: string;
  status?: LeaseStatus;
  page?: number;
  page_size?: number;
}
export function listLeases(params?: LeaseListParams): Promise<LeaseList> {
  return get<LeaseList>("/leases", params);
}
export function createLease(input: LeaseCreate): Promise<Lease> {
  return post<Lease, LeaseCreate>("/leases", input);
}
export function getLease(id: string): Promise<Lease> {
  return get<Lease>(`/leases/${encodeURIComponent(id)}`);
}
export function updateLease(id: string, input: LeaseUpdate): Promise<Lease> {
  return patch<Lease, LeaseUpdate>(`/leases/${encodeURIComponent(id)}`, input);
}
export function activateLease(id: string): Promise<Lease> {
  return post<Lease, Record<string, never>>(
    `/leases/${encodeURIComponent(id)}/activate`,
    {},
  );
}
export function renewLease(
  id: string,
  input?: LeaseRenewRequest,
): Promise<Lease> {
  return post<Lease, LeaseRenewRequest>(
    `/leases/${encodeURIComponent(id)}/renew`,
    input ?? {},
  );
}
export function terminateLease(
  id: string,
  input: LeaseTerminateRequest,
): Promise<Lease> {
  return post<Lease, LeaseTerminateRequest>(
    `/leases/${encodeURIComponent(id)}/terminate`,
    input,
  );
}
