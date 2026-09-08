import { describe, expect, it } from "vitest";

import type { Lease, Unit } from "@/types/api";

import { computeOverviewStats } from "./page";

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
});
