// Domain models: Property, Unit, Tenant, Lease, Payment, MaintenanceRequest.
export type PropertyType =
  "single_family" | "multi_family" | "condo" | "commercial";
export type UnitStatus = "vacant" | "occupied" | "unavailable";
export type LeaseStatus = "draft" | "active" | "expired" | "terminated";

export interface Property {
  id: string;
  owner_id: string;
  name: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  region: string;
  postal_code: string;
  country: string;
  property_type: PropertyType;
  created_at: string;
  updated_at: string;
}
export interface Unit {
  id: string;
  property_id: string;
  label: string;
  bedrooms: number;
  bathrooms: number;
  square_feet: number | null;
  market_rent: string;
  status: UnitStatus;
  created_at: string;
  updated_at: string;
}
export interface Tenant {
  id: string;
  user_id: string | null;
  full_name: string;
  email: string;
  phone: string;
  emergency_contact: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}
export interface Lease {
  id: string;
  unit_id: string;
  tenant_id: string;
  start_date: string;
  end_date: string;
  rent_amount: string;
  deposit_amount: string;
  billing_day: number;
  status: LeaseStatus;
  created_at: string;
  updated_at: string;
}
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
