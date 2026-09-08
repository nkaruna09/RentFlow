"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { TenantForm, type TenantFormValues } from "@/components/forms/tenant-form";
import { DataTable, type Column, type SortDirection } from "@/components/tables/data-table";
import { Button } from "@/components/ui/button";
import {
  createTenant,
  deleteTenant,
  listTenantLeases,
  listTenants,
  updateTenant,
} from "@/lib/api/tenants";
import { summarizeLeaseHistory } from "@/lib/dashboard";
import type { Lease, Tenant } from "@/types/api";

const PAGE_SIZE = 10;

function toFormValues(tenant: Tenant): TenantFormValues {
  return {
    user_id: tenant.user_id ?? null,
    full_name: tenant.full_name,
    email: tenant.email,
    phone: tenant.phone,
    emergency_contact: tenant.emergency_contact ?? null,
  };
}

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [leaseHistory, setLeaseHistory] = useState<Lease[]>([]);
  const [leaseHistoryLoading, setLeaseHistoryLoading] = useState(false);
  const [sortKey, setSortKey] = useState<string | null>("full_name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const loadTenants = useCallback(
    async (nextPage: number) => {
      setLoading(true);
      setError(null);

      try {
        const response = await listTenants({ page: nextPage, page_size: PAGE_SIZE });
        setTenants(response.items);
        setTotal(response.total);
      } catch (apiError) {
        const message = apiError instanceof Error ? apiError.message : "Unable to load tenants.";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadTenants(page);
  }, [loadTenants, page]);

  const loadLeaseHistory = useCallback(async (tenant: Tenant) => {
    setSelectedTenant(tenant);
    setLeaseHistoryLoading(true);
    setError(null);

    try {
      const response = await listTenantLeases(tenant.id, { page: 1, page_size: 25 });
      setLeaseHistory(response.items);
    } catch (apiError) {
      const message =
        apiError instanceof Error ? apiError.message : "Unable to load tenant lease history.";
      setError(message);
      setLeaseHistory([]);
    } finally {
      setLeaseHistoryLoading(false);
    }
  }, []);

  const handleSortChange = (key: string, direction: SortDirection) => {
    setSortKey(key);
    setSortDirection(direction);
  };

  const startNewTenant = useCallback(() => {
    setSelectedTenant(null);
    setIsFormOpen(true);
  }, []);

  const startEdit = useCallback((tenant: Tenant) => {
    setSelectedTenant(tenant);
    setIsFormOpen(true);
  }, []);

  const handleCloseForm = useCallback(() => {
    setSelectedTenant(null);
    setIsFormOpen(false);
  }, []);

  const handleSubmit = async (values: TenantFormValues) => {
    setSubmitting(true);
    setError(null);

    try {
      if (selectedTenant) {
        await updateTenant(selectedTenant.id, values);
      } else {
        await createTenant(values);
      }

      setPage(1);
      setSortKey("full_name");
      setSortDirection("asc");
      handleCloseForm();
    } catch (apiError) {
      const message = apiError instanceof Error ? apiError.message : "Unable to save tenant.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = useCallback(
    async (tenant: Tenant) => {
      if (!window.confirm(`Delete ${tenant.full_name}? This action cannot be undone.`)) {
        return;
      }

      setDeletingId(tenant.id);
      setError(null);

      try {
        await deleteTenant(tenant.id);
        const nextPage = tenants.length === 1 && page > 1 ? page - 1 : page;
        setPage(nextPage);
        if (selectedTenant?.id === tenant.id) {
          setSelectedTenant(null);
          setLeaseHistory([]);
        }
      } catch (apiError) {
        const message = apiError instanceof Error ? apiError.message : "Unable to delete tenant.";
        setError(message);
      } finally {
        setDeletingId(null);
      }
    },
    [page, selectedTenant?.id, tenants.length],
  );

  const displayColumns = useMemo<Column<Tenant>[]>(
    () => [
      { key: "full_name", header: "Tenant", sortable: true, accessor: (row) => row.full_name },
      { key: "email", header: "Email", sortable: true, accessor: (row) => row.email },
      { key: "phone", header: "Phone", sortable: true, accessor: (row) => row.phone },
      {
        key: "actions",
        header: "Actions",
        sortable: false,
        render: (row) => (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-sky-300 hover:text-sky-700"
              onClick={() => void loadLeaseHistory(row)}
            >
              View history
            </button>
            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-sky-300 hover:text-sky-700"
              onClick={() => startEdit(row)}
            >
              Edit
            </button>
            <button
              type="button"
              className="rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => void handleDelete(row)}
              disabled={deletingId === row.id}
            >
              {deletingId === row.id ? "Deleting..." : "Delete"}
            </button>
          </div>
        ),
      },
    ],
    [deletingId, handleDelete, loadLeaseHistory, startEdit],
  );

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">Tenants</h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage residents, contact details, and lease history.
          </p>
        </div>

        <Button type="button" onClick={startNewTenant}>
          Add tenant
        </Button>
      </div>

      {isFormOpen ? (
        <TenantForm
          initialValues={selectedTenant ? toFormValues(selectedTenant) : null}
          submitLabel={selectedTenant ? "Update tenant" : "Create tenant"}
          isSaving={submitting}
          onSubmit={handleSubmit}
          onCancel={handleCloseForm}
        />
      ) : null}

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {selectedTenant ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">
                Tenant overview
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-900">{selectedTenant.full_name}</h2>
              <p className="mt-1 text-sm text-slate-600">{selectedTenant.email}</p>
              <p className="text-sm text-slate-600">{selectedTenant.phone}</p>
            </div>

            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:border-slate-300"
              onClick={() => setSelectedTenant(null)}
            >
              Clear
            </button>
          </div>

          <div className="mt-5 border-t border-slate-200 pt-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-slate-900">Lease history</h3>
              <span className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
                {leaseHistory.length} record{leaseHistory.length === 1 ? "" : "s"}
              </span>
            </div>

            {leaseHistoryLoading ? (
              <div className="py-6 text-sm text-slate-600">Loading lease history...</div>
            ) : leaseHistory.length ? (
              <div className="space-y-3">
                {leaseHistory.map((lease) => (
                  <div
                    key={lease.id}
                    className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          {lease.status ? lease.status.charAt(0).toUpperCase() + lease.status.slice(1) : "Lease"}
                        </p>
                        <p className="text-xs text-slate-500">
                          {lease.start_date ?? "n/a"} → {lease.end_date ?? "n/a"}
                        </p>
                      </div>
                      <span className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 text-xs font-medium capitalize text-slate-700">
                        {lease.status ?? "unknown"}
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-slate-600">
                      Rent: ${lease.rent_amount ? Number(lease.rent_amount).toFixed(2) : "0.00"}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-4 text-sm text-slate-600">
                {summarizeLeaseHistory(leaseHistory)}
              </p>
            )}
          </div>
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-lg shadow-slate-200/50 sm:p-6">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-slate-600">
            Loading tenants...
          </div>
        ) : (
          <DataTable
            columns={displayColumns}
            data={tenants}
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
