import { beforeEach, describe, expect, it, vi } from "vitest";

import { get } from "@/lib/api/client";
import { listInvoices } from "@/lib/api/payments";

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
});
