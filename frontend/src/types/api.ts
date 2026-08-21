// Types generated from / mirroring the backend OpenAPI schema.
export type UserRole = "landlord" | "manager" | "tenant";
export interface ApiErrorBody { detail: string; code?: string; field_errors?: Record<string, string>; }
export interface LoginRequest { email: string; password: string; }
export interface RegisterRequest extends LoginRequest { full_name: string; role?: UserRole; }
export interface TokenPair { access_token: string; refresh_token: string; token_type: string; }
export interface User {
  id: string; email: string; full_name: string; role: UserRole; is_active: boolean;
  created_at: string; updated_at: string;
}
