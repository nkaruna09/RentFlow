// @vitest-environment jsdom

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PaymentsPage from "../../src/app/(dashboard)/payments/page";
import { listLeases } from "@/lib/api/leases";
import { listArrears, listInvoices, recordPayment } from "@/lib/api/payments";
import { listTenants } from "@/lib/api/tenants";
import type { ArrearsList, Invoice, Lease, Tenant } from "@/types/api";

vi.mock("@/lib/api/leases", () => ({ listLeases: vi.fn() }));
vi.mock("@/lib/api/payments", () => ({
  listArrears: vi.fn(),
  listInvoices: vi.fn(),
  recordPayment: vi.fn(),
}));
vi.mock("@/lib/api/tenants", () => ({ listTenants: vi.fn() }));

const lease: Lease = {
  id: "11111111-1111-1111-1111-111111111111",
  unit_id: "22222222-2222-2222-2222-222222222222",
  tenant_id: "33333333-3333-3333-3333-333333333333",
  start_date: "2026-01-01",
  end_date: "2027-01-01",
  rent_amount: "1000.00",
  deposit_amount: "1000.00",
  billing_day: 1,
  status: "active",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const tenant: Tenant = {
  id: lease.tenant_id,
  user_id: null,
  full_name: "Jordan Lee",
  email: "jordan@example.com",
  phone: "555-0100",
  emergency_contact: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const openInvoice: Invoice = {
  id: "44444444-4444-4444-4444-444444444444",
  lease_id: lease.id,
  period_start: "2026-09-01",
  period_end: "2026-10-01",
  amount_due: "100.00",
  late_fee_amount: null,
  due_date: "2026-09-01",
  status: "open",
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
};

function arrears(outstandingBalance: string): ArrearsList {
  return {
    items: [{ lease_id: lease.id, outstanding_balance: outstandingBalance }],
    total: 1,
    outstanding_total: outstandingBalance,
    page: 1,
    page_size: 100,
  };
}

function mockReferenceData() {
  vi.mocked(listLeases).mockResolvedValue({
    items: [lease],
    total: 1,
    page: 1,
    page_size: 100,
  });
  vi.mocked(listTenants).mockResolvedValue({
    items: [tenant],
    total: 1,
    page: 1,
    page_size: 100,
  });
}

describe("PaymentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReferenceData();
    vi.mocked(recordPayment).mockResolvedValue({
      id: "55555555-5555-5555-5555-555555555555",
      invoice_id: openInvoice.id,
      amount: "40.00",
      paid_at: "2026-09-27T12:00:00Z",
      method: "bank_transfer",
      reference: null,
      created_at: "2026-09-27T12:00:00Z",
      updated_at: "2026-09-27T12:00:00Z",
    });
  });

  afterEach(cleanup);

  it("combines lease and status filters in the invoice request", async () => {
    vi.mocked(listInvoices).mockResolvedValue({
      items: [openInvoice],
      total: 1,
      page: 1,
      page_size: 10,
    });
    vi.mocked(listArrears).mockResolvedValue(arrears("100.00"));
    const user = userEvent.setup();

    render(<PaymentsPage />);
    await screen.findByRole("button", { name: "Record payment" });

    await user.selectOptions(screen.getByLabelText("Lease"), lease.id);
    await user.selectOptions(screen.getByLabelText("Status"), "open");

    await waitFor(() => {
      expect(listInvoices).toHaveBeenCalledWith({
        lease_id: lease.id,
        status: "open",
        page: 1,
        page_size: 10,
      });
    });
  });

  it("refreshes the invoice status and arrears after recording a payment", async () => {
    const partialInvoice = { ...openInvoice, status: "partial" as const };
    vi.mocked(listInvoices)
      .mockResolvedValueOnce({
        items: [openInvoice],
        total: 1,
        page: 1,
        page_size: 10,
      })
      .mockResolvedValue({
        items: [partialInvoice],
        total: 1,
        page: 1,
        page_size: 10,
      });
    vi.mocked(listArrears)
      .mockResolvedValueOnce(arrears("100.00"))
      .mockResolvedValue(arrears("60.00"));
    const user = userEvent.setup();

    render(<PaymentsPage />);
    await user.click(
      await screen.findByRole("button", { name: "Record payment" }),
    );
    const form = screen
      .getByRole("heading", { name: "Record payment" })
      .closest("form");
    expect(form).not.toBeNull();
    const paymentForm = within(form as HTMLFormElement);
    fireEvent.change(paymentForm.getByLabelText("Amount"), {
      target: { value: "40.00" },
    });
    await user.selectOptions(
      paymentForm.getByLabelText("Method"),
      "bank_transfer",
    );
    await user.click(
      paymentForm.getByRole("button", { name: "Record payment" }),
    );

    await waitFor(() => {
      expect(recordPayment).toHaveBeenCalledWith(
        openInvoice.id,
        expect.objectContaining({ amount: "40.00", method: "bank_transfer" }),
      );
      expect(listInvoices).toHaveBeenCalledTimes(2);
      expect(listArrears).toHaveBeenCalledTimes(2);
    });

    expect(
      await screen.findByText("partial", { selector: "span" }),
    ).toBeTruthy();
    expect(screen.getAllByText("$60.00")).toHaveLength(2);
    expect(
      screen.queryByRole("heading", { name: "Record payment" }),
    ).toBeNull();
  });
});
