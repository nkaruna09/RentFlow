// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DataTable, type Column } from "@/components/tables/data-table";

type Row = { id: string; name: string };

const columns: Column<Row>[] = [
  { key: "name", header: "Name", accessor: (row) => row.name },
];

describe("DataTable", () => {
  afterEach(cleanup);

  it("does not paginate server-paginated rows a second time", () => {
    render(
      <DataTable
        columns={columns}
        data={[{ id: "11", name: "Server page two row" }]}
        rowKey={(row) => row.id}
        page={2}
        pageSize={10}
        total={11}
        onPageChange={vi.fn()}
      />,
    );

    expect(screen.getByText("Server page two row")).toBeTruthy();
    expect(screen.getByText("Page 2 of 2")).toBeTruthy();
  });
});
