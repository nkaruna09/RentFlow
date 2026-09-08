"use client";

import { useMemo, useState, type ReactNode } from "react";

export type SortDirection = "asc" | "desc";

export type Column<T> = {
  key: string;
  header: string;
  accessor?: (row: T) => string | number | boolean | Date | null | undefined;
  render?: (row: T) => ReactNode;
  sortable?: boolean;
  className?: string;
};

export function sortRows<T>(
  rows: T[],
  accessor: ((row: T) => unknown) | keyof T,
  direction: SortDirection = "asc",
): T[] {
  const getValue =
    typeof accessor === "function"
      ? accessor
      : (row: T) => (row as Record<string, unknown>)[String(accessor)];

  return [...rows].sort((left, right) => {
    const leftValue = getValue(left);
    const rightValue = getValue(right);

    if (leftValue == null && rightValue == null) return 0;
    if (leftValue == null) return 1;
    if (rightValue == null) return -1;

    if (typeof leftValue === "number" && typeof rightValue === "number") {
      return direction === "asc" ? leftValue - rightValue : rightValue - leftValue;
    }

    const leftString = String(leftValue).toLowerCase();
    const rightString = String(rightValue).toLowerCase();

    if (leftString === rightString) return 0;
    return direction === "asc"
      ? leftString.localeCompare(rightString)
      : rightString.localeCompare(leftString);
  });
}

export function paginateRows<T>(rows: T[], page: number, pageSize: number): T[] {
  const safePage = Math.max(1, page);
  const safePageSize = Math.max(1, pageSize);
  const start = (safePage - 1) * safePageSize;
  return rows.slice(start, start + safePageSize);
}

type DataTableProps<T> = {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T) => string;
  page?: number;
  pageSize?: number;
  total?: number;
  emptyMessage?: string;
  sortKey?: string | null;
  sortDirection?: SortDirection;
  onPageChange?: (page: number) => void;
  onSortChange?: (key: string, direction: SortDirection) => void;
};

export function DataTable<T>({
  columns,
  data,
  rowKey,
  page = 1,
  pageSize = 10,
  total,
  emptyMessage = "No records found.",
  sortKey,
  sortDirection = "asc",
  onPageChange,
  onSortChange,
}: DataTableProps<T>) {
  const [internalSort, setInternalSort] = useState<{
    key: string;
    direction: SortDirection;
  } | null>(null);

  const activeSortKey = sortKey ?? internalSort?.key ?? null;
  const activeSortDirection = sortDirection ?? internalSort?.direction ?? "asc";

  const sortedRows = useMemo(() => {
    if (!activeSortKey) return data;
    const column = columns.find((item) => item.key === activeSortKey);
    if (!column) return data;

    const accessor =
      column.accessor ??
      ((row: T) => (row as Record<string, unknown>)[column.key]);

    return sortRows(data, accessor, activeSortDirection);
  }, [activeSortDirection, activeSortKey, columns, data]);

  const totalPages =
    total != null ? Math.max(1, Math.ceil(total / Math.max(pageSize, 1))) : Math.max(1, Math.ceil(sortedRows.length / Math.max(pageSize, 1)));
  const visibleRows =
    onPageChange != null || total != null
      ? paginateRows(sortedRows, page, pageSize)
      : sortedRows;

  const handleSort = (key: string) => {
    const nextDirection =
      activeSortKey === key && activeSortDirection === "asc" ? "desc" : "asc";

    if (onSortChange) {
      onSortChange(key, nextDirection);
      return;
    }

    setInternalSort({ key, direction: nextDirection });
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-left text-sm text-slate-700">
          <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            <tr>
              {columns.map((column) => {
                const sortable = column.sortable !== false;
                const isActive = activeSortKey === column.key;

                return (
                  <th
                    key={column.key}
                    className={[
                      "border-b border-slate-200 px-4 py-3",
                      column.className ?? "",
                    ].join(" ")}
                  >
                    {sortable ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 font-semibold"
                        onClick={() => handleSort(column.key)}
                      >
                        <span>{column.header}</span>
                        {isActive ? (
                          <span className="text-slate-700">
                            {activeSortDirection === "asc" ? "↑" : "↓"}
                          </span>
                        ) : null}
                      </button>
                    ) : (
                      <span>{column.header}</span>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visibleRows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-sm text-slate-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              visibleRows.map((row) => {
                return (
                  <tr key={rowKey(row)} className="border-b border-slate-200 last:border-b-0">
                    {columns.map((column) => {
                      const value = column.accessor ? column.accessor(row) : undefined;
                      const rendered = column.render
                        ? column.render(row)
                        : value == null
                          ? "—"
                          : typeof value === "string" || typeof value === "number" || typeof value === "boolean"
                            ? String(value)
                            : value instanceof Date
                              ? value.toLocaleDateString()
                              : String(value);

                      return (
                        <td key={`${rowKey(row)}-${column.key}`} className="px-4 py-3 align-middle">
                          {rendered}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {onPageChange && total !== undefined ? (
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <span>
            Page {page} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={page <= 1}
              onClick={() => onPageChange(Math.max(1, page - 1))}
            >
              Previous
            </button>
            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={page >= totalPages}
              onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
