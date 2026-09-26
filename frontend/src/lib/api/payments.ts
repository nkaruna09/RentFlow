// Payment endpoint bindings.
import { get, post } from "@/lib/api/client";
import type {
  ArrearsList,
  Invoice,
  InvoiceCreate,
  InvoiceList,
  InvoiceStatus,
  Payment,
  PaymentCreate,
} from "@/types/api";

export interface InvoiceListParams {
  lease_id?: string;
  status?: InvoiceStatus;
  page?: number;
  page_size?: number;
}

export interface ArrearsListParams {
  page?: number;
  page_size?: number;
}

export function listInvoices(params?: InvoiceListParams): Promise<InvoiceList> {
  return get<InvoiceList>("/payments/invoices", params);
}

export function createInvoice(input: InvoiceCreate): Promise<Invoice> {
  return post<Invoice, InvoiceCreate>("/payments/invoices", input);
}

export function getInvoice(id: string): Promise<Invoice> {
  return get<Invoice>(`/payments/invoices/${encodeURIComponent(id)}`);
}

export function recordPayment(
  invoiceId: string,
  input: PaymentCreate,
): Promise<Payment> {
  return post<Payment, PaymentCreate>(
    `/payments/invoices/${encodeURIComponent(invoiceId)}/payments`,
    input,
  );
}

export function listArrears(params?: ArrearsListParams): Promise<ArrearsList> {
  return get<ArrearsList>("/payments/arrears", params);
}
