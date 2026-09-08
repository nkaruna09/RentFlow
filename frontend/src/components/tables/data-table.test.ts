import { describe, expect, it } from "vitest";

import { paginateRows, sortRows } from "./data-table";

describe("data-table helpers", () => {
  it("sorts rows alphabetically in ascending order", () => {
    const rows = [
      { id: "b", name: "Bravo" },
      { id: "a", name: "Alpha" },
      { id: "c", name: "Charlie" },
    ];

    const sorted = sortRows(rows, (row) => row.name, "asc");

    expect(sorted.map((row) => row.id)).toEqual(["a", "b", "c"]);
  });

  it("paginates rows based on the current page and page size", () => {
    const rows = [
      { id: 1 },
      { id: 2 },
      { id: 3 },
      { id: 4 },
      { id: 5 },
    ];

    expect(paginateRows(rows, 2, 2)).toEqual([{ id: 3 }, { id: 4 }]);
  });
});
