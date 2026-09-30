"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  MaintenanceForm,
  type MaintenanceFormValues,
} from "@/components/forms/maintenance-form";
import { MaintenanceBoard } from "@/components/maintenance/maintenance-board";
import { Button } from "@/components/ui/button";
import { getCurrentUser } from "@/lib/api/auth";
import { listLeases } from "@/lib/api/leases";
import {
  createMaintenanceRequest,
  listMaintenanceRequests,
  updateMaintenanceRequest,
} from "@/lib/api/maintenance";
import { listUnits } from "@/lib/api/units";
import { listAllPages, MAX_API_PAGE_SIZE } from "@/lib/dashboard";
import type {
  MaintenancePriority,
  MaintenanceRequest,
  MaintenanceStatus,
  Unit,
  User,
} from "@/types/api";

const priorityOptions: Array<{
  value: MaintenancePriority | "all";
  label: string;
}> = [
  { value: "all", label: "All priorities" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "emergency", label: "Emergency" },
];

export default function MaintenancePage() {
  const [requests, setRequests] = useState<MaintenanceRequest[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [knownUnitIds, setKnownUnitIds] = useState<string[]>([]);
  const [unitFilter, setUnitFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState<
    MaintenancePriority | "all"
  >("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [tenantUnitIds, setTenantUnitIds] = useState<string[]>([]);
  const [submissionUnitId, setSubmissionUnitId] = useState("");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const loadUnits = useCallback(async () => {
    try {
      const items = await listAllPages<Unit>((page) =>
        listUnits({ page, page_size: MAX_API_PAGE_SIZE }),
      );
      setUnits(items);
    } catch {
      // Tenants cannot call the manager-only units endpoint. Request unit IDs
      // still provide functional filters and fallback labels for their board.
    }
  }, []);

  const loadAccessContext = useCallback(async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
      if (user.role !== "tenant") return;

      const leases = await listAllPages((page) =>
        listLeases({
          status: "active",
          page,
          page_size: MAX_API_PAGE_SIZE,
        }),
      );
      const leasedUnitIds = [
        ...new Set(
          leases
            .filter((lease) => lease.status === "active")
            .map((lease) => lease.unit_id),
        ),
      ];
      setTenantUnitIds(leasedUnitIds);
      setKnownUnitIds((current) => [
        ...new Set([...current, ...leasedUnitIds]),
      ]);
      setSubmissionUnitId((current) =>
        leasedUnitIds.includes(current) ? current : (leasedUnitIds[0] ?? ""),
      );
    } catch (apiError) {
      setError(
        apiError instanceof Error
          ? apiError.message
          : "Unable to load your maintenance access.",
      );
    }
  }, []);

  const loadRequests = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const items = await listAllPages<MaintenanceRequest>((page) =>
        listMaintenanceRequests({
          unit_id: unitFilter === "all" ? undefined : unitFilter,
          priority: priorityFilter === "all" ? undefined : priorityFilter,
          page,
          page_size: MAX_API_PAGE_SIZE,
        }),
      );
      setRequests(items);
      setKnownUnitIds((current) => [
        ...new Set([...current, ...items.map((request) => request.unit_id)]),
      ]);
    } catch (apiError) {
      setError(
        apiError instanceof Error
          ? apiError.message
          : "Unable to load maintenance requests.",
      );
    } finally {
      setLoading(false);
    }
  }, [priorityFilter, unitFilter]);

  useEffect(() => {
    void loadUnits();
  }, [loadUnits]);

  useEffect(() => {
    void loadAccessContext();
  }, [loadAccessContext]);

  useEffect(() => {
    void loadRequests();
  }, [loadRequests]);

  const unitLabels = useMemo(
    () => Object.fromEntries(units.map((unit) => [unit.id, unit.label])),
    [units],
  );

  const unitOptions = useMemo(() => {
    const ids = new Set([...knownUnitIds, ...units.map((unit) => unit.id)]);
    return [...ids]
      .map((id) => ({ id, label: unitLabels[id] ?? `Unit ${id.slice(0, 8)}` }))
      .sort((left, right) => left.label.localeCompare(right.label));
  }, [knownUnitIds, unitLabels, units]);

  const handleStatusChange = async (
    request: MaintenanceRequest,
    status: MaintenanceStatus,
  ) => {
    const previous = request;
    setError(null);
    setUpdatingIds((current) => new Set(current).add(request.id));
    setRequests((current) =>
      current.map((item) =>
        item.id === request.id ? { ...item, status } : item,
      ),
    );

    try {
      const updated = await updateMaintenanceRequest(request.id, { status });
      setRequests((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (apiError) {
      setRequests((current) =>
        current.map((item) => (item.id === previous.id ? previous : item)),
      );
      setError(
        apiError instanceof Error
          ? apiError.message
          : "Unable to update maintenance status.",
      );
    } finally {
      setUpdatingIds((current) => {
        const next = new Set(current);
        next.delete(request.id);
        return next;
      });
    }
  };

  const handleSubmitRequest = async (values: MaintenanceFormValues) => {
    if (!submissionUnitId || !tenantUnitIds.includes(submissionUnitId)) {
      setSubmissionError("Select one of your actively leased units.");
      return;
    }

    setSubmitting(true);
    setSubmissionError(null);
    try {
      await createMaintenanceRequest({
        unit_id: submissionUnitId,
        ...values,
      });
      await loadRequests();
      setIsFormOpen(false);
    } catch (apiError) {
      setSubmissionError(
        apiError instanceof Error
          ? apiError.message
          : "Unable to submit the maintenance request.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const resetFilters = () => {
    setUnitFilter("all");
    setPriorityFilter("all");
  };

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">
            Maintenance board
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Track repair requests from intake through completion.
          </p>
        </div>

        {currentUser?.role === "tenant" ? (
          <div className="flex flex-wrap items-end gap-3">
            {tenantUnitIds.length > 1 ? (
              <div>
                <label
                  className="mb-1.5 block text-sm font-medium text-slate-700"
                  htmlFor="maintenance-submission-unit"
                >
                  Your leased unit
                </label>
                <select
                  id="maintenance-submission-unit"
                  value={submissionUnitId}
                  onChange={(event) => setSubmissionUnitId(event.target.value)}
                  className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
                >
                  {tenantUnitIds.map((unitId) => (
                    <option key={unitId} value={unitId}>
                      {unitLabels[unitId] ?? `Unit ${unitId.slice(0, 8)}`}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
            <Button
              type="button"
              onClick={() => {
                setSubmissionError(null);
                setIsFormOpen(true);
              }}
              disabled={!submissionUnitId}
            >
              Submit maintenance request
            </Button>
          </div>
        ) : null}
      </div>

      {currentUser?.role === "tenant" && tenantUnitIds.length === 0 ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          You need an active lease before submitting a maintenance request.
        </div>
      ) : null}

      {isFormOpen && submissionUnitId ? (
        <MaintenanceForm
          unitLabel={
            unitLabels[submissionUnitId] ??
            `Unit ${submissionUnitId.slice(0, 8)}`
          }
          isSaving={submitting}
          error={submissionError}
          onSubmit={handleSubmitRequest}
          onCancel={() => {
            setIsFormOpen(false);
            setSubmissionError(null);
          }}
        />
      ) : null}

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]">
          <div>
            <label
              className="mb-1.5 block text-sm font-medium text-slate-700"
              htmlFor="maintenance-unit-filter"
            >
              Unit
            </label>
            <select
              id="maintenance-unit-filter"
              value={unitFilter}
              onChange={(event) => setUnitFilter(event.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            >
              <option value="all">All units</option>
              {unitOptions.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              className="mb-1.5 block text-sm font-medium text-slate-700"
              htmlFor="maintenance-priority-filter"
            >
              Priority
            </label>
            <select
              id="maintenance-priority-filter"
              value={priorityFilter}
              onChange={(event) =>
                setPriorityFilter(
                  event.target.value as MaintenancePriority | "all",
                )
              }
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            >
              {priorityOptions.map((option) => (
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
              onClick={resetFilters}
              disabled={unitFilter === "all" && priorityFilter === "all"}
            >
              Reset filters
            </Button>
          </div>
        </div>
      </div>

      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-lg shadow-slate-200/50 sm:p-6">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="font-semibold text-slate-900">Requests</h2>
            <p className="text-sm text-slate-500">
              {requests.length} {requests.length === 1 ? "request" : "requests"}
              {unitFilter !== "all" || priorityFilter !== "all"
                ? " matching these filters"
                : " across the portfolio"}
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-slate-600">
            Loading maintenance requests...
          </div>
        ) : (
          <MaintenanceBoard
            requests={requests}
            unitLabels={unitLabels}
            updatingIds={updatingIds}
            canManageStatus={
              currentUser?.role === "landlord" ||
              currentUser?.role === "manager"
            }
            onStatusChange={handleStatusChange}
          />
        )}
      </div>
    </section>
  );
}
