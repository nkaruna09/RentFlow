"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  DataTable,
  type Column,
  type SortDirection,
} from "@/components/tables/data-table";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listLeases } from "@/lib/api/leases";
import { listInvoices } from "@/lib/api/payments";
import { listAllPages, MAX_API_PAGE_SIZE } from "@/lib/dashboard";
import type { Invoice, InvoiceStatus, Lease } from "@/types/api";

const PAGE_SIZE = 10;

const statusOptions: Array<{ value: InvoiceStatus | "all"; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "open", label: "Open" },
  { value: "partial", label: "Partial" },
  { value: "overdue", label: "Overdue" },
  { value: "paid", label: "Paid" },
  { value: "void", label: "Void" },
];

const statusVariants: Record<InvoiceStatus, BadgeVariant> = {
  open: "info",
  paid: "success",
  partial: "warning",
  overdue: "danger",
  void: "neutral",
};

const moneyFormatter = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
});

const dateFormatter = new Intl.DateTimeFormat("en-CA", {
  dateStyle: "medium",
  timeZone: "UTC",
});

function formatMoney(value: string): string {
  return moneyFormatter.format(Number(value));
}

function formatDate(value: string): string {
  return dateFormatter.format(new Date(`${value}T00:00:00Z`));
}

function shortId(value: string): string {
  return value.slice(0, 8);
}

function leaseLabel(lease: Lease): string {
  return `${formatDate(lease.start_date)} – ${formatDate(lease.end_date)} · ${shortId(lease.id)}`;
}

export default function PaymentsPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [leases, setLeases] = useState<Lease[]>([]);
  const [leaseFilter, setLeaseFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "all">(
    "all",
  );
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<string | null>("due_date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const leaseById = useMemo(
    () => Object.fromEntries(leases.map((lease) => [lease.id, lease])),
    [leases],
  );

  const loadLeases = useCallback(async () => {
    try {
      const allLeases = await listAllPages<Lease>((nextPage) =>
        listLeases({ page: nextPage, page_size: MAX_API_PAGE_SIZE }),
      );
      setLeases(allLeases);
    } catch (apiError) {
      const message =
        apiError instanceof Error
          ? apiError.message
          : "Unable to load lease filters.";
      setError(message);
    }
  }, []);

  const loadInvoices = useCallback(
    async (nextPage: number) => {
      setLoading(true);
      setError(null);

      try {
        const response = await listInvoices({
          lease_id: leaseFilter === "all" ? undefined : leaseFilter,
          status: statusFilter === "all" ? undefined : statusFilter,
          page: nextPage,
          page_size: PAGE_SIZE,
        });
        setInvoices(response.items);
        setTotal(response.total);
      } catch (apiError) {
        const message =
          apiError instanceof Error
            ? apiError.message
            : "Unable to load the rent ledger.";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [leaseFilter, statusFilter],
  );

  useEffect(() => {
    void loadLeases();
  }, [loadLeases]);

  useEffect(() => {
    void loadInvoices(page);
  }, [loadInvoices, page]);

  const handleFilterChange = (
    nextLease: string,
    nextStatus: InvoiceStatus | "all",
  ) => {
    setLeaseFilter(nextLease);
    setStatusFilter(nextStatus);
    setPage(1);
  };

  const columns = useMemo<Column<Invoice>[]>(
    () => [
      {
        key: "lease_id",
        header: "Lease",
        sortable: true,
        accessor: (invoice) => invoice.lease_id,
        render: (invoice) => {
          const lease = leaseById[invoice.lease_id];
          return (
            <div>
              <div className="font-medium text-slate-900">
                {lease
                  ? leaseLabel(lease)
                  : `Lease ${shortId(invoice.lease_id)}`}
              </div>
              <div className="mt-0.5 font-mono text-xs text-slate-500">
                {invoice.lease_id}
              </div>
            </div>
          );
        },
      },
      {
        key: "period_start",
        header: "Billing period",
        sortable: true,
        accessor: (invoice) => invoice.period_start,
        render: (invoice) => (
          <span>
            {formatDate(invoice.period_start)} –{" "}
            {formatDate(invoice.period_end)}
          </span>
        ),
      },
      {
        key: "due_date",
        header: "Due date",
        sortable: true,
        accessor: (invoice) => invoice.due_date,
        render: (invoice) => <span>{formatDate(invoice.due_date)}</span>,
      },
      {
        key: "amount_due",
        header: "Amount due",
        sortable: true,
        accessor: (invoice) => Number(invoice.amount_due),
        render: (invoice) => (
          <div>
            <div className="font-semibold text-slate-900">
              {formatMoney(invoice.amount_due)}
            </div>
            {invoice.late_fee_amount ? (
              <div className="mt-0.5 text-xs text-rose-600">
                Includes {formatMoney(invoice.late_fee_amount)} late fee
              </div>
            ) : null}
          </div>
        ),
      },
      {
        key: "status",
        header: "Status",
        sortable: true,
        accessor: (invoice) => invoice.status,
        render: (invoice) => (
          <Badge variant={statusVariants[invoice.status]}>
            {invoice.status}
          </Badge>
        ),
      },
    ],
    [leaseById],
  );

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-slate-900">Rent ledger</h1>
        <p className="mt-1 text-sm text-slate-600">
          Review invoices, due dates, late fees, and payment status across your
          leases.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]">
          <div>
            <label
              className="mb-1.5 block text-sm font-medium text-slate-700"
              htmlFor="invoice-lease-filter"
            >
              Lease
            </label>
            <select
              id="invoice-lease-filter"
              value={leaseFilter}
              onChange={(event) =>
                handleFilterChange(event.target.value, statusFilter)
              }
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            >
              <option value="all">All leases</option>
              {leases.map((lease) => (
                <option key={lease.id} value={lease.id}>
                  {leaseLabel(lease)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              className="mb-1.5 block text-sm font-medium text-slate-700"
              htmlFor="invoice-status-filter"
            >
              Status
            </label>
            <select
              id="invoice-status-filter"
              value={statusFilter}
              onChange={(event) =>
                handleFilterChange(
                  leaseFilter,
                  event.target.value as InvoiceStatus | "all",
                )
              }
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleFilterChange("all", "all")}
              disabled={leaseFilter === "all" && statusFilter === "all"}
            >
              Reset filters
            </Button>
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-lg shadow-slate-200/50 sm:p-6">
        <div className="mb-4">
          <h2 className="font-semibold text-slate-900">Invoices</h2>
          <p className="text-sm text-slate-500">
            {total} {total === 1 ? "invoice" : "invoices"} matching these
            filters
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-slate-600">
            Loading invoices...
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={invoices}
            rowKey={(invoice) => invoice.id}
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            emptyMessage="No invoices match the selected filters."
            sortKey={sortKey}
            sortDirection={sortDirection}
            onPageChange={setPage}
            onSortChange={(key, direction) => {
              setSortKey(key);
              setSortDirection(direction);
            }}
          />
        )}
      </div>
    </section>
  );
}
