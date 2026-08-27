import { del, get, patch, post } from "@/lib/api/client";
import type {
  Unit,
  UnitCreate,
  UnitList,
  UnitStatus,
  UnitUpdate,
} from "@/types/api";

export interface UnitListParams {
  property_id?: string;
  status?: UnitStatus;
  page?: number;
  page_size?: number;
}
export function listUnits(params?: UnitListParams): Promise<UnitList> {
  return get<UnitList>("/units", params);
}
export function createUnit(input: UnitCreate): Promise<Unit> {
  return post<Unit, UnitCreate>("/units", input);
}
export function getUnit(id: string): Promise<Unit> {
  return get<Unit>(`/units/${encodeURIComponent(id)}`);
}
export function updateUnit(id: string, input: UnitUpdate): Promise<Unit> {
  return patch<Unit, UnitUpdate>(`/units/${encodeURIComponent(id)}`, input);
}
export function deleteUnit(id: string): Promise<void> {
  return del<void>(`/units/${encodeURIComponent(id)}`);
}
