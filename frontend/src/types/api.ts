// Types generated from / mirroring the backend OpenAPI schema.
import type {
  Lease,
  LeaseStatus,
  Invoice,
  InvoiceStatus,
  Paginated,
  Payment,
  PaymentMethod,
  Property,
  PropertyType,
  Tenant,
  Unit,
  UnitStatus,
} from "@/types/models";

export type UserRole = "landlord" | "manager" | "tenant";
export interface ApiErrorBody {
  detail: string;
  code?: string;
  field_errors?: Record<string, string>;
}
export interface LoginRequest {
  email: string;
  password: string;
}
export interface RegisterRequest extends LoginRequest {
  full_name: string;
  role?: UserRole;
}
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
export type {
  Lease,
  LeaseStatus,
  Invoice,
  InvoiceStatus,
  Paginated,
  Payment,
  PaymentMethod,
  Property,
  PropertyType,
  Tenant,
  Unit,
  UnitStatus,
};

export type PropertyList = Paginated<Property>;
export type UnitList = Paginated<Unit>;
export type TenantList = Paginated<Tenant>;
export type LeaseList = Paginated<Lease>;
export type InvoiceList = Paginated<Invoice>;
export interface PropertyCreate {
  name: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  region: string;
  postal_code: string;
  country: string;
  property_type: PropertyType;
}
export type PropertyUpdate = Partial<PropertyCreate>;
export interface UnitCreate {
  property_id: string;
  label: string;
  bedrooms: string;
  bathrooms: string;
  square_feet?: number | null;
  market_rent: string;
  status: UnitStatus;
}
export type UnitUpdate = Partial<Omit<UnitCreate, "property_id">>;
export interface TenantCreate {
  user_id?: string | null;
  full_name: string;
  email: string;
  phone: string;
  emergency_contact?: Record<string, unknown> | null;
}
export type TenantUpdate = Partial<TenantCreate>;
export interface LeaseCreate {
  unit_id: string;
  tenant_id: string;
  start_date: string;
  end_date: string;
  rent_amount: string;
  deposit_amount: string;
  billing_day: number;
  status?: LeaseStatus;
}
export type LeaseUpdate = Partial<
  Omit<LeaseCreate, "unit_id" | "tenant_id" | "status">
>;
export interface LeaseRenewRequest {
  start_date?: string;
  end_date?: string;
  rent_amount?: string;
  deposit_amount?: string;
  billing_day?: number;
}
export interface LeaseTerminateRequest {
  reason: string;
  end_date: string;
}
export interface InvoiceCreate {
  lease_id: string;
  period_start: string;
  period_end: string;
  amount_due: string;
  due_date: string;
  status?: InvoiceStatus;
}
export interface PaymentCreate {
  amount: string;
  paid_at: string;
  method: PaymentMethod;
  reference?: string | null;
}
export interface ArrearsItem {
  lease_id: string;
  outstanding_balance: string;
}
export interface ArrearsList {
  items: ArrearsItem[];
  total: number;
  outstanding_total: string;
  page: number;
  page_size: number;
}
