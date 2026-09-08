import { describe, expect, it } from "vitest";

import { summarizeLeaseHistory } from "@/lib/dashboard";

describe("tenant lease history", () => {
  it("summarizes active lease details for the selected tenant", () => {
    const leases = [
      {
        id: "lease-1",
        start_date: "2024-01-01",
        end_date: "2024-12-31",
        status: "active",
        rent_amount: "2100.00",
      },
    ];

    expect(summarizeLeaseHistory(leases)).toContain("Active");
    expect(summarizeLeaseHistory(leases)).toContain("2024-01-01");
  });
});
