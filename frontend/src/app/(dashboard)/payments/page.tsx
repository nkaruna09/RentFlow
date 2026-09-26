"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { PaymentForm } from "@/components/forms/payment-form";
import {
  DataTable,
  type Column,
  type SortDirection,
} from "@/components/tables/data-table";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listLeases } from "@/lib/api/leases";
import { listArrears, listInvoices, recordPayment } from "@/lib/api/payments";
import { listTenants } from "@/lib/api/tenants";
import { listAllPages, MAX_API_PAGE_SIZE } from "@/lib/dashboard";
import type {
  ArrearsItem,
  Invoice,
  InvoiceStatus,
  Lease,
  PaymentCreate,
  Tenant,
} from "@/types/api";

const PAGE_SIZE = 10;
const ARREARS_PAGE_SIZE = 100;

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
  const [arrears, setArrears] = useState<ArrearsItem[]>([]);
  const [outstandingTotal, setOutstandingTotal] = useState("0.00");
  const [leases, setLeases] = useState<Lease[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [leaseFilter, setLeaseFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "all">(
    "all",
  );
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [arrearsLoading, setArrearsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [paymentSaving, setPaymentSaving] = useState(false);
  const [sortKey, setSortKey] = useState<string | null>("due_date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const leaseById = useMemo(
    () => Object.fromEntries(leases.map((lease) => [lease.id, lease])),
    [leases],
  );
  const tenantById = useMemo(
    () => Object.fromEntries(tenants.map((tenant) => [tenant.id, tenant])),
    [tenants],
  );

  const loadReferenceData = useCallback(async () => {
    try {
      const [allLeases, allTenants] = await Promise.all([
        listAllPages<Lease>((nextPage) =>
          listLeases({ page: nextPage, page_size: MAX_API_PAGE_SIZE }),
        ),
        listAllPages<Tenant>((nextPage) =>
          listTenants({ page: nextPage, page_size: MAX_API_PAGE_SIZE }),
        ),
      ]);
      setLeases(allLeases);
      setTenants(allTenants);
    } catch (apiError) {
      const message =
        apiError instanceof Error
          ? apiError.message
          : "Unable to load billing references.";
      setError(message);
    }
  }, []);

  const loadArrears = useCallback(async () => {
    setArrearsLoading(true);

    try {
      const firstPage = await listArrears({
        page: 1,
        page_size: ARREARS_PAGE_SIZE,
      });
      const allItems = [...firstPage.items];
      const pageCount = Math.ceil(firstPage.total / ARREARS_PAGE_SIZE);

      for (let nextPage = 2; nextPage <= pageCount; nextPage += 1) {
        const response = await listArrears({
          page: nextPage,
          page_size: ARREARS_PAGE_SIZE,
        });
        allItems.push(...response.items);
      }

      setArrears(allItems);
      setOutstandingTotal(firstPage.outstanding_total);
    } catch (apiError) {
      const message =
        apiError instanceof Error
          ? apiError.message
          : "Unable to load arrears.";
      setError(message);
    } finally {
      setArrearsLoading(false);
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
    void loadReferenceData();
    void loadArrears();
  }, [loadArrears, loadReferenceData]);

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

  const startPayment = useCallback((invoice: Invoice) => {
    setSelectedInvoice(invoice);
    setPaymentError(null);
  }, []);

  const closePayment = useCallback(() => {
    setSelectedInvoice(null);
    setPaymentError(null);
  }, []);

  const handleRecordPayment = async (values: PaymentCreate) => {
    if (!selectedInvoice) return;

    setPaymentSaving(true);
    setPaymentError(null);

    try {
      await recordPayment(selectedInvoice.id, values);
      setPage(1);
      await Promise.all([loadInvoices(1), loadArrears()]);
      closePayment();
    } catch (apiError) {
      const message =
        apiError instanceof Error
          ? apiError.message
          : "Unable to record payment.";
      setPaymentError(message);
    } finally {
      setPaymentSaving(false);
    }
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
      {
        key: "actions",
        header: "Actions",
        sortable: false,
        render: (invoice) =>
          invoice.status === "paid" || invoice.status === "void" ? (
            <span className="text-xs text-slate-400">No payment due</span>
          ) : (
            <button
              type="button"
              className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-semibold text-sky-700 transition hover:bg-sky-100"
              onClick={() => startPayment(invoice)}
            >
              Record payment
            </button>
          ),
      },
    ],
    [leaseById, startPayment],
  );

  const arrearsColumns = useMemo<Column<ArrearsItem>[]>(
    () => [
      {
        key: "tenant",
        header: "Tenant",
        sortable: true,
        accessor: (item) => {
          const lease = leaseById[item.lease_id];
          return lease ? tenantById[lease.tenant_id]?.full_name : "";
        },
        render: (item) => {
          const lease = leaseById[item.lease_id];
          return (
            <span className="font-medium text-slate-900">
              {lease
                ? (tenantById[lease.tenant_id]?.full_name ?? "Unknown tenant")
                : "Unknown tenant"}
            </span>
          );
        },
      },
      {
        key: "lease_id",
        header: "Lease",
        sortable: true,
        accessor: (item) => item.lease_id,
        render: (item) => {
          const lease = leaseById[item.lease_id];
          return (
            <span>
              {lease ? leaseLabel(lease) : `Lease ${shortId(item.lease_id)}`}
            </span>
          );
        },
      },
      {
        key: "outstanding_balance",
        header: "Outstanding",
        sortable: true,
        accessor: (item) => Number(item.outstanding_balance),
        render: (item) => (
          <span className="font-semibold text-rose-700">
            {formatMoney(item.outstanding_balance)}
          </span>
        ),
      },
    ],
    [leaseById, tenantById],
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

      {selectedInvoice ? (
        <PaymentForm
          invoice={selectedInvoice}
          isSaving={paymentSaving}
          error={paymentError}
          onSubmit={handleRecordPayment}
          onCancel={closePayment}
        />
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

      <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-lg shadow-slate-200/50 sm:p-6">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-semibold text-slate-900">
              Arrears by tenant and lease
            </h2>
            <p className="text-sm text-slate-500">
              Outstanding balances across all leases in your portfolio.
            </p>
          </div>
          <div className="rounded-2xl bg-rose-50 px-4 py-3 text-right">
            <div className="text-xs font-semibold uppercase tracking-wide text-rose-600">
              Total outstanding
            </div>
            <div className="mt-0.5 text-2xl font-semibold text-rose-800">
              {formatMoney(outstandingTotal)}
            </div>
          </div>
        </div>

        {arrearsLoading ? (
          <div className="flex items-center justify-center py-12 text-sm text-slate-600">
            Loading arrears...
          </div>
        ) : (
          <DataTable
            columns={arrearsColumns}
            data={arrears}
            rowKey={(item) => item.lease_id}
            emptyMessage="No outstanding balances."
          />
        )}
      </div>
    </section>
  );
}
