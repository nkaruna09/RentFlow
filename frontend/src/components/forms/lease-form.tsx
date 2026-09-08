"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Lease, LeaseCreate, LeaseStatus, Tenant, Unit } from "@/types/api";

export type LeaseFormValues = LeaseCreate;

type LeaseFormProps = {
  initialValues?: Partial<LeaseFormValues> | Lease | null;
  units?: Unit[];
  tenants?: Tenant[];
  submitLabel?: string;
  isSaving?: boolean;
  error?: string | null;
  onSubmit: (values: LeaseFormValues) => Promise<void> | void;
  onCancel?: () => void;
};

const emptyValues: LeaseFormValues = {
  unit_id: "",
  tenant_id: "",
  start_date: "",
  end_date: "",
  rent_amount: "",
  deposit_amount: "",
  billing_day: 1,
  status: "draft",
};

const statusOptions: Array<{ value: LeaseStatus; label: string }> = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "expired", label: "Expired" },
  { value: "terminated", label: "Terminated" },
];

export function resolveLeaseSubmitError(error: unknown): string | null {
  if (!error || typeof error !== "object") {
    return null;
  }

  const candidate = error as {
    status?: number;
    code?: string;
    message?: string;
    detail?: string;
  };

  const isOverlap =
    candidate.status === 409 &&
    (candidate.code === "lease_overlap" ||
      candidate.detail?.toLowerCase().includes("overlaps") ||
      candidate.message?.toLowerCase().includes("overlaps"));

  if (!isOverlap) {
    return null;
  }

  return (
    candidate.detail ||
    candidate.message ||
    "This lease overlaps an active lease for this unit. Please select a different unit or date range."
  );
}

export function LeaseForm({
  initialValues,
  units = [],
  tenants = [],
  submitLabel = "Save lease",
  isSaving = false,
  error = null,
  onSubmit,
  onCancel,
}: LeaseFormProps) {
  const [values, setValues] = useState<LeaseFormValues>(
    initialValues
      ? {
          ...emptyValues,
          ...initialValues,
          billing_day: initialValues.billing_day ?? 1,
        }
      : emptyValues,
  );
  const [localError, setLocalError] = useState<string | null>(error);

  useEffect(() => {
    setValues(
      initialValues
        ? {
            ...emptyValues,
            ...initialValues,
            billing_day: initialValues.billing_day ?? 1,
          }
        : emptyValues,
    );
    setLocalError(error);
  }, [error, initialValues]);

  function updateField<K extends keyof LeaseFormValues>(field: K, value: LeaseFormValues[K]) {
    setValues((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);

    try {
      await onSubmit({
        ...values,
        billing_day: Number(values.billing_day),
      });
    } catch (submitError) {
      const message = resolveLeaseSubmitError(submitError);
      setLocalError(message ?? "Unable to save lease.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      {localError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {localError}
        </div>
      ) : null}

      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="lease-unit">
            Unit
          </label>
          <select
            id="lease-unit"
            value={values.unit_id}
            onChange={(event) => updateField("unit_id", event.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            required
          >
            <option value="">Select a unit</option>
            {units.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="lease-tenant">
            Tenant
          </label>
          <select
            id="lease-tenant"
            value={values.tenant_id}
            onChange={(event) => updateField("tenant_id", event.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            required
          >
            <option value="">Select a tenant</option>
            {tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.full_name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="lease-start-date">
            Start date
          </label>
          <Input
            id="lease-start-date"
            type="date"
            value={values.start_date}
            onChange={(event) => updateField("start_date", event.target.value)}
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="lease-end-date">
            End date
          </label>
          <Input
            id="lease-end-date"
            type="date"
            value={values.end_date}
            onChange={(event) => updateField("end_date", event.target.value)}
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="lease-rent-amount">
            Rent amount
          </label>
          <Input
            id="lease-rent-amount"
            type="number"
            min="0"
            step="0.01"
            value={values.rent_amount}
            onChange={(event) => updateField("rent_amount", event.target.value)}
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="lease-deposit-amount">
            Deposit amount
          </label>
          <Input
            id="lease-deposit-amount"
            type="number"
            min="0"
            step="0.01"
            value={values.deposit_amount}
            onChange={(event) => updateField("deposit_amount", event.target.value)}
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="lease-billing-day">
            Billing day
          </label>
          <Input
            id="lease-billing-day"
            type="number"
            min="1"
            max="31"
            step="1"
            value={values.billing_day}
            onChange={(event) => updateField("billing_day", Number(event.target.value || 1))}
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="lease-status">
            Status
          </label>
          <select
            id="lease-status"
            value={values.status ?? "draft"}
            onChange={(event) => updateField("status", event.target.value as LeaseStatus)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center justify-end gap-3 pt-2">
        {onCancel ? (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
        <Button type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : submitLabel}
        </Button>
      </div>
    </form>
  );
}
