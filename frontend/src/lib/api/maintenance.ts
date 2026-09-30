import { get, patch, post } from "@/lib/api/client";
import type {
  MaintenanceComment,
  MaintenanceCommentCreate,
  MaintenancePriority,
  MaintenanceRequest,
  MaintenanceRequestCreate,
  MaintenanceRequestList,
  MaintenanceRequestUpdate,
  MaintenanceStatus,
} from "@/types/api";

export interface MaintenanceListParams {
  unit_id?: string;
  status?: MaintenanceStatus;
  priority?: MaintenancePriority;
  page?: number;
  page_size?: number;
}

export function listMaintenanceRequests(
  params?: MaintenanceListParams,
): Promise<MaintenanceRequestList> {
  return get<MaintenanceRequestList>("/maintenance", params);
}

export function createMaintenanceRequest(
  input: MaintenanceRequestCreate,
): Promise<MaintenanceRequest> {
  return post<MaintenanceRequest, MaintenanceRequestCreate>(
    "/maintenance",
    input,
  );
}

export function getMaintenanceRequest(id: string): Promise<MaintenanceRequest> {
  return get<MaintenanceRequest>(`/maintenance/${encodeURIComponent(id)}`);
}

export function updateMaintenanceRequest(
  id: string,
  input: MaintenanceRequestUpdate,
): Promise<MaintenanceRequest> {
  return patch<MaintenanceRequest, MaintenanceRequestUpdate>(
    `/maintenance/${encodeURIComponent(id)}`,
    input,
  );
}

export function addMaintenanceComment(
  requestId: string,
  input: MaintenanceCommentCreate,
): Promise<MaintenanceComment> {
  return post<MaintenanceComment, MaintenanceCommentCreate>(
    `/maintenance/${encodeURIComponent(requestId)}/comments`,
    input,
  );
}
