import { describe, expect, it } from "vitest";

import type { Lease, Unit } from "@/types/api";

import { computeOverviewStats, listAllPages } from "@/lib/dashboard";

describe("dashboard overview stats", () => {
  it("computes live occupancy and vacancy metrics from unit and lease state", () => {
    const units: Pick<Unit, "status">[] = [
      { status: "vacant" },
      { status: "occupied" },
      { status: "vacant" },
      { status: "occupied" },
    ];
    const leases: Pick<Lease, "status">[] = [
      { status: "active" },
      { status: "draft" },
      { status: "active" },
    ];

    expect(computeOverviewStats(units, leases)).toEqual({
      totalUnits: 4,
      vacantUnits: 2,
      activeLeaseCount: 2,
      occupancyPercentage: 50,
    });
  });

  it("returns zero occupancy when the portfolio has no units", () => {
    expect(computeOverviewStats([], [])).toEqual({
      totalUnits: 0,
      vacantUnits: 0,
      activeLeaseCount: 0,
      occupancyPercentage: 0,
    });
  });

  it("loads every API page", async () => {
    const loadPage = async (page: number) => ({
      items: [`page-${page}`],
      total: 201,
    });

    await expect(listAllPages(loadPage)).resolves.toEqual([
      "page-1",
      "page-2",
      "page-3",
    ]);
  });
});
