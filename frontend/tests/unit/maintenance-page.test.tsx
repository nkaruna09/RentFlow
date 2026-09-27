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
import {
  listMaintenanceRequests,
  updateMaintenanceRequest,
} from "@/lib/api/maintenance";
import { listUnits } from "@/lib/api/units";
import type { MaintenanceRequest, Unit } from "@/types/api";

vi.mock("@/lib/api/maintenance", () => ({
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

describe("MaintenancePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
      screen.getByLabelText("Change status for Burst pipe"),
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
});
