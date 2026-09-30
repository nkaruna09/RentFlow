// @vitest-environment jsdom

import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import MaintenancePage from "../../src/app/(dashboard)/maintenance/page";
import { getCurrentUser } from "@/lib/api/auth";
import { listLeases } from "@/lib/api/leases";
import {
  createMaintenanceRequest,
  listMaintenanceRequests,
  updateMaintenanceRequest,
} from "@/lib/api/maintenance";
import { listUnits } from "@/lib/api/units";
import type { Lease, MaintenanceRequest, Unit, User } from "@/types/api";

vi.mock("@/lib/api/auth", () => ({ getCurrentUser: vi.fn() }));
vi.mock("@/lib/api/leases", () => ({ listLeases: vi.fn() }));
vi.mock("@/lib/api/maintenance", () => ({
  createMaintenanceRequest: vi.fn(),
  listMaintenanceRequests: vi.fn(),
  updateMaintenanceRequest: vi.fn(),
}));
vi.mock("@/lib/api/units", () => ({ listUnits: vi.fn() }));

const unit: Unit = {
  id: "11111111-1111-1111-1111-111111111111",
  property_id: "22222222-2222-2222-2222-222222222222",
  label: "Unit 9",
  bedrooms: "2",
  bathrooms: "1",
  square_feet: 900,
  market_rent: "1800.00",
  status: "occupied",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const request: MaintenanceRequest = {
  id: "33333333-3333-3333-3333-333333333333",
  unit_id: unit.id,
  reported_by: "44444444-4444-4444-4444-444444444444",
  title: "Burst pipe",
  description: "Water is leaking under the kitchen sink.",
  priority: "emergency",
  status: "in_progress",
  assigned_to: "55555555-5555-5555-5555-555555555555",
  resolved_at: null,
  created_at: "2026-09-27T12:00:00Z",
  updated_at: "2026-09-27T12:00:00Z",
};

const landlord: User = {
  id: "66666666-6666-6666-6666-666666666666",
  email: "owner@example.com",
  full_name: "Property Owner",
  role: "landlord",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("MaintenancePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCurrentUser).mockResolvedValue(landlord);
    vi.mocked(listLeases).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    });
    vi.mocked(listUnits).mockResolvedValue({
      items: [unit],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(listMaintenanceRequests).mockResolvedValue({
      items: [request],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(updateMaintenanceRequest).mockResolvedValue({
      ...request,
      status: "resolved",
      resolved_at: "2026-09-27T13:00:00Z",
    });
    vi.mocked(createMaintenanceRequest).mockResolvedValue(request);
  });

  afterEach(cleanup);

  it("filters requests by unit and priority", async () => {
    const user = userEvent.setup();
    render(<MaintenancePage />);
    await screen.findByText("Burst pipe");

    await user.selectOptions(screen.getByLabelText("Unit"), unit.id);
    await user.selectOptions(screen.getByLabelText("Priority"), "emergency");

    await waitFor(() => {
      expect(listMaintenanceRequests).toHaveBeenCalledWith({
        unit_id: unit.id,
        priority: "emergency",
        page: 1,
        page_size: 100,
      });
    });
  });

  it("patches a status and moves the card without reloading", async () => {
    let resolveUpdate!: (value: MaintenanceRequest) => void;
    vi.mocked(updateMaintenanceRequest).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveUpdate = resolve;
      }),
    );
    const user = userEvent.setup();
    render(<MaintenancePage />);
    await screen.findByText("Burst pipe");

    await user.selectOptions(
      await screen.findByLabelText("Change status for Burst pipe"),
      "resolved",
    );

    expect(updateMaintenanceRequest).toHaveBeenCalledWith(request.id, {
      status: "resolved",
    });
    const resolvedColumn = screen
      .getByRole("heading", { name: "Resolved" })
      .closest("section");
    expect(resolvedColumn).not.toBeNull();
    expect(
      within(resolvedColumn as HTMLElement).getByText("Burst pipe"),
    ).toBeTruthy();

    await act(async () => {
      resolveUpdate({
        ...request,
        status: "resolved",
        resolved_at: "2026-09-27T13:00:00Z",
      });
    });

    expect(listMaintenanceRequests).toHaveBeenCalledTimes(1);
  });

  it("assigns an open request to the current user via assigned_to", async () => {
    const openRequest: MaintenanceRequest = {
      ...request,
      status: "open",
      assigned_to: null,
    };
    vi.mocked(listMaintenanceRequests).mockResolvedValue({
      items: [openRequest],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(updateMaintenanceRequest).mockResolvedValue({
      ...openRequest,
      status: "assigned",
      assigned_to: landlord.id,
    });
    const user = userEvent.setup();
    render(<MaintenancePage />);

    const select = await screen.findByLabelText("Change status for Burst pipe");
    await screen.findByRole("option", { name: "Assign to me" });
    await user.selectOptions(select, "assigned");

    expect(updateMaintenanceRequest).toHaveBeenCalledWith(request.id, {
      assigned_to: landlord.id,
    });
    const assignedColumn = screen
      .getByRole("heading", { name: "Assigned" })
      .closest("section");
    expect(
      within(assignedColumn as HTMLElement).getByText("Burst pipe"),
    ).toBeTruthy();
  });

  it("submits only against a unit from the tenant's active leases", async () => {
    const tenant: User = {
      ...landlord,
      id: request.reported_by,
      email: "tenant@example.com",
      full_name: "Tenant User",
      role: "tenant",
    };
    const otherUnitId = "77777777-7777-7777-7777-777777777777";
    const activeLease: Lease = {
      id: "88888888-8888-8888-8888-888888888888",
      unit_id: unit.id,
      tenant_id: "99999999-9999-9999-9999-999999999999",
      start_date: "2026-01-01",
      end_date: "2027-01-01",
      rent_amount: "1800.00",
      deposit_amount: "1800.00",
      billing_day: 1,
      status: "active",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(getCurrentUser).mockResolvedValue(tenant);
    vi.mocked(listUnits).mockRejectedValue(new Error("Forbidden"));
    vi.mocked(listLeases).mockResolvedValue({
      items: [
        activeLease,
        {
          ...activeLease,
          id: "lease-terminated",
          unit_id: otherUnitId,
          status: "terminated",
        },
      ],
      total: 2,
      page: 1,
      page_size: 100,
    });
    vi.mocked(listMaintenanceRequests).mockResolvedValue({
      items: [request],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(createMaintenanceRequest).mockResolvedValue({
      ...request,
      unit_id: unit.id,
      title: "No heat",
      description: "The radiators are cold.",
      priority: "emergency",
      status: "open",
      assigned_to: null,
    });
    const user = userEvent.setup();

    render(<MaintenancePage />);
    await user.click(
      await screen.findByRole("button", {
        name: "Submit maintenance request",
      }),
    );
    const form = screen
      .getByRole("heading", { name: "Submit maintenance request" })
      .closest("form");
    expect(form).not.toBeNull();
    const requestForm = within(form as HTMLFormElement);
    await user.type(requestForm.getByLabelText("Title"), "  No heat  ");
    await user.type(
      requestForm.getByLabelText("Description"),
      "  The radiators are cold.  ",
    );
    await user.selectOptions(
      requestForm.getByLabelText("Priority"),
      "emergency",
    );
    await user.click(
      requestForm.getByRole("button", { name: "Submit request" }),
    );

    await waitFor(() => {
      expect(createMaintenanceRequest).toHaveBeenCalledWith({
        unit_id: unit.id,
        title: "No heat",
        description: "The radiators are cold.",
        priority: "emergency",
      });
    });
    expect(listLeases).toHaveBeenCalledWith({
      status: "active",
      page: 1,
      page_size: 100,
    });
    expect(screen.queryByText(`Unit ${otherUnitId.slice(0, 8)}`)).toBeNull();
    expect(screen.queryByLabelText("Change status for Burst pipe")).toBeNull();
  });
});
