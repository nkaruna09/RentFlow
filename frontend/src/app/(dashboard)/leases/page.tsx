"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { LeaseForm, type LeaseFormValues, resolveLeaseSubmitError } from "@/components/forms/lease-form";
import { DataTable, type Column, type SortDirection } from "@/components/tables/data-table";
import { Button } from "@/components/ui/button";
import {
  activateLease,
  createLease,
  listLeases,
  renewLease,
  terminateLease,
  updateLease,
} from "@/lib/api/leases";
import { listTenants } from "@/lib/api/tenants";
import { listUnits } from "@/lib/api/units";
import type { Lease, LeaseStatus, Tenant, Unit } from "@/types/api";

const PAGE_SIZE = 10;

function formatLeaseStatus(status: LeaseStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatLeaseTerm(startDate: string, endDate: string): string {
  return `${startDate} → ${endDate}`;
}

function getRenewalLabel(status: LeaseStatus): string {
  if (status === "active" || status === "expired") {
    return "Eligible";
  }

  return "—";
}

export default function LeasesPage() {
  const [leases, setLeases] = useState<Lease[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedLease, setSelectedLease] = useState<Lease | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<string | null>("start_date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const unitById = useMemo(
    () => Object.fromEntries(units.map((unit) => [unit.id, unit])),
    [units],
  );
  const tenantById = useMemo(
    () => Object.fromEntries(tenants.map((tenant) => [tenant.id, tenant])),
    [tenants],
  );

  const loadReferenceData = useCallback(async () => {
    const [unitResponse, tenantResponse] = await Promise.all([
      listUnits({ page: 1, page_size: 500 }),
      listTenants({ page: 1, page_size: 500 }),
    ]);

    setUnits(unitResponse.items);
    setTenants(tenantResponse.items);
  }, []);

  const loadLeases = useCallback(async (nextPage: number) => {
    setLoading(true);
    setPageError(null);

    try {
      const response = await listLeases({ page: nextPage, page_size: PAGE_SIZE });
      setLeases(response.items);
      setTotal(response.total);
    } catch (apiError) {
      const message = apiError instanceof Error ? apiError.message : "Unable to load leases.";
      setPageError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadReferenceData();
  }, [loadReferenceData]);

  useEffect(() => {
    void loadLeases(page);
  }, [loadLeases, page]);

  const startNewLease = useCallback(() => {
    setSelectedLease(null);
    setFormError(null);
    setIsFormOpen(true);
  }, []);

  const startEditLease = useCallback((lease: Lease) => {
    setSelectedLease(lease);
    setFormError(null);
    setIsFormOpen(true);
  }, []);

  const handleCloseForm = useCallback(() => {
    setSelectedLease(null);
    setFormError(null);
    setIsFormOpen(false);
  }, []);

  const handleSubmit = async (values: LeaseFormValues) => {
    setSubmitting(true);
    setPageError(null);
    setFormError(null);

    try {
      if (selectedLease) {
        await updateLease(selectedLease.id, values);
      } else {
        await createLease(values);
      }

      await loadLeases(1);
      setPage(1);
      setSortKey("start_date");
      setSortDirection("desc");
      handleCloseForm();
    } catch (apiError) {
      const overlapMessage = resolveLeaseSubmitError(apiError);
      if (overlapMessage) {
        setFormError(overlapMessage);
        return;
      }

      const message = apiError instanceof Error ? apiError.message : "Unable to save lease.";
      setPageError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleActivate = useCallback(
    async (lease: Lease) => {
      setActioningId(lease.id);
      setPageError(null);

      try {
        await activateLease(lease.id);
        await loadLeases(page);
      } catch (apiError) {
        const overlapMessage = resolveLeaseSubmitError(apiError);
        const message = overlapMessage ?? (apiError instanceof Error ? apiError.message : "Unable to activate lease.");
        setPageError(message);
      } finally {
        setActioningId(null);
      }
    },
    [loadLeases, page],
  );

  const handleRenew = useCallback(
    async (lease: Lease) => {
      setActioningId(lease.id);
      setPageError(null);

      try {
        await renewLease(lease.id);
        await loadLeases(page);
      } catch (apiError) {
        const overlapMessage = resolveLeaseSubmitError(apiError);
        const message = overlapMessage ?? (apiError instanceof Error ? apiError.message : "Unable to renew lease.");
        setPageError(message);
      } finally {
        setActioningId(null);
      }
    },
    [loadLeases, page],
  );

  const handleTerminate = useCallback(
    async (lease: Lease) => {
      const reason = window.prompt("Termination reason", "Tenant move-out");
      if (!reason || !reason.trim()) {
        return;
      }

      const endDate = window.prompt("Termination end date (YYYY-MM-DD)", lease.end_date);
      if (!endDate || !endDate.trim()) {
        return;
      }

      setActioningId(lease.id);
      setPageError(null);

      try {
        await terminateLease(lease.id, { reason, end_date: endDate });
        await loadLeases(page);
      } catch (apiError) {
        const overlapMessage = resolveLeaseSubmitError(apiError);
        const message = overlapMessage ?? (apiError instanceof Error ? apiError.message : "Unable to terminate lease.");
        setPageError(message);
      } finally {
        setActioningId(null);
      }
    },
    [loadLeases, page],
  );

  const handleSortChange = (key: string, direction: SortDirection) => {
    setSortKey(key);
    setSortDirection(direction);
  };

  const displayColumns = useMemo<Column<Lease>[]>(
    () => [
      {
        key: "unit_id",
        header: "Unit",
        sortable: true,
        accessor: (row) => unitById[row.unit_id]?.label ?? row.unit_id,
        render: (row) => <span>{unitById[row.unit_id]?.label ?? "Unknown unit"}</span>,
      },
      {
        key: "tenant_id",
        header: "Tenant",
        sortable: true,
        accessor: (row) => tenantById[row.tenant_id]?.full_name ?? row.tenant_id,
        render: (row) => <span>{tenantById[row.tenant_id]?.full_name ?? "Unknown tenant"}</span>,
      },
      {
        key: "start_date",
        header: "Term",
        sortable: true,
        accessor: (row) => `${row.start_date} ${row.end_date}`,
        render: (row) => <span>{formatLeaseTerm(row.start_date, row.end_date)}</span>,
      },
      {
        key: "rent_amount",
        header: "Rent",
        sortable: true,
        accessor: (row) => Number(row.rent_amount),
        render: (row) => <span>${Number(row.rent_amount).toFixed(2)}</span>,
      },
      {
        key: "status",
        header: "Status",
        sortable: true,
        accessor: (row) => formatLeaseStatus(row.status),
        render: (row) => (
          <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
              row.status === "active"
                ? "bg-emerald-100 text-emerald-700"
                : row.status === "draft"
                  ? "bg-slate-100 text-slate-700"
                  : row.status === "expired"
                    ? "bg-amber-100 text-amber-700"
                    : "bg-red-100 text-red-700"
            }`}
          >
            {formatLeaseStatus(row.status)}
          </span>
        ),
      },
      {
        key: "renewal",
        header: "Renewal",
        sortable: false,
        render: (row) => <span>{getRenewalLabel(row.status)}</span>,
      },
      {
        key: "actions",
        header: "Actions",
        sortable: false,
        render: (row) => (
          <div className="flex flex-wrap items-center gap-2">
            {row.status === "draft" ? (
              <button
                type="button"
                className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-sky-300 hover:text-sky-700"
                onClick={() => startEditLease(row)}
              >
                Edit
              </button>
            ) : null}
            {row.status === "draft" ? (
              <button
                type="button"
                className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={() => void handleActivate(row)}
                disabled={actioningId === row.id}
              >
                {actioningId === row.id ? "Activating..." : "Activate"}
              </button>
            ) : null}
            {(row.status === "active" || row.status === "expired") ? (
              <button
                type="button"
                className="rounded-md border border-sky-200 bg-sky-50 px-2.5 py-1.5 text-xs font-medium text-sky-700 hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={() => void handleRenew(row)}
                disabled={actioningId === row.id}
              >
                {actioningId === row.id ? "Renewing..." : "Renew"}
              </button>
            ) : null}
            {row.status === "active" ? (
              <button
                type="button"
                className="rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={() => void handleTerminate(row)}
                disabled={actioningId === row.id}
              >
                {actioningId === row.id ? "Terminating..." : "Terminate"}
              </button>
            ) : null}
          </div>
        ),
      },
    ],
    [actioningId, handleActivate, handleRenew, handleTerminate, startEditLease, tenantById, unitById],
  );

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">Leases</h1>
          <p className="mt-1 text-sm text-slate-600">
            Track occupancy, renewals, and lifecycle actions across units.
          </p>
        </div>

        <Button type="button" onClick={startNewLease}>
          Add lease
        </Button>
      </div>

      {isFormOpen ? (
        <LeaseForm
          initialValues={selectedLease ? selectedLease : null}
          units={units}
          tenants={tenants}
          submitLabel={selectedLease ? "Update lease" : "Create lease"}
          isSaving={submitting}
          error={formError}
          onSubmit={handleSubmit}
          onCancel={handleCloseForm}
        />
      ) : null}

      {pageError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {pageError}
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-lg shadow-slate-200/50 sm:p-6">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-slate-600">
            Loading leases...
          </div>
        ) : (
          <DataTable
            columns={displayColumns}
            data={leases}
            rowKey={(row) => row.id}
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            sortKey={sortKey}
            sortDirection={sortDirection}
            onPageChange={setPage}
            onSortChange={handleSortChange}
          />
        )}
      </div>
    </section>
  );
}
