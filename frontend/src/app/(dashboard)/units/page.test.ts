import { describe, expect, it } from "vitest";

import { filterUnits } from "./page";

describe("unit filters", () => {
  it("combines property and status filters", () => {
    const rows = [
      { id: "1", property_id: "prop-a", status: "vacant" },
      { id: "2", property_id: "prop-a", status: "occupied" },
      { id: "3", property_id: "prop-b", status: "vacant" },
      { id: "4", property_id: "prop-b", status: "occupied" },
    ];

    expect(filterUnits(rows, "prop-a", "vacant")).toEqual([
      { id: "1", property_id: "prop-a", status: "vacant" },
    ]);
  });
});
