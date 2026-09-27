import { beforeEach, describe, expect, it, vi } from "vitest";

import { get, post } from "@/lib/api/client";
import {
  createInvoice,
  getInvoice,
  listArrears,
  listInvoices,
  recordPayment,
} from "@/lib/api/payments";

vi.mock("@/lib/api/client", () => ({
  get: vi.fn(),
  post: vi.fn(),
}));

describe("payment API bindings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("passes lease and status filters to the invoice endpoint", () => {
    void listInvoices({
      lease_id: "lease-123",
      status: "partial",
      page: 2,
      page_size: 10,
    });

    expect(get).toHaveBeenCalledWith("/payments/invoices", {
      lease_id: "lease-123",
      status: "partial",
      page: 2,
      page_size: 10,
    });
  });

  it("binds invoice creation, lookup, payment recording, and arrears paths", () => {
    const invoice = {
      lease_id: "lease-123",
      period_start: "2026-09-01",
      period_end: "2026-10-01",
      amount_due: "1000.00",
      due_date: "2026-09-01",
    };
    const payment = {
      amount: "250.00",
      paid_at: "2026-09-27T12:00:00Z",
      method: "bank_transfer" as const,
      reference: "transfer-1",
    };

    void createInvoice(invoice);
    void getInvoice("invoice/1");
    void recordPayment("invoice/1", payment);
    void listArrears({ page: 2, page_size: 25 });

    expect(post).toHaveBeenCalledWith("/payments/invoices", invoice);
    expect(get).toHaveBeenCalledWith("/payments/invoices/invoice%2F1");
    expect(post).toHaveBeenCalledWith(
      "/payments/invoices/invoice%2F1/payments",
      payment,
    );
    expect(get).toHaveBeenCalledWith("/payments/arrears", {
      page: 2,
      page_size: 25,
    });
  });
});
