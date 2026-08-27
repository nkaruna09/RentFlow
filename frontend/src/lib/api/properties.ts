// Property endpoint bindings.
import { del, get, patch, post } from "@/lib/api/client";
import type {
  Property,
  PropertyCreate,
  PropertyList,
  PropertyUpdate,
  UnitList,
} from "@/types/api";

export interface PropertyListParams {
  page?: number;
  page_size?: number;
}
export function listProperties(
  params?: PropertyListParams,
): Promise<PropertyList> {
  return get<PropertyList>("/properties", params);
}
export function createProperty(input: PropertyCreate): Promise<Property> {
  return post<Property, PropertyCreate>("/properties", input);
}
export function getProperty(id: string): Promise<Property> {
  return get<Property>(`/properties/${encodeURIComponent(id)}`);
}
export function updateProperty(
  id: string,
  input: PropertyUpdate,
): Promise<Property> {
  return patch<Property, PropertyUpdate>(
    `/properties/${encodeURIComponent(id)}`,
    input,
  );
}
export function deleteProperty(id: string): Promise<void> {
  return del<void>(`/properties/${encodeURIComponent(id)}`);
}
export function listPropertyUnits(
  id: string,
  params?: PropertyListParams,
): Promise<UnitList> {
  return get<UnitList>(`/properties/${encodeURIComponent(id)}/units`, params);
}
