"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Tenant, TenantCreate } from "@/types/api";

export type TenantFormValues = TenantCreate;

type TenantFormProps = {
  initialValues?: Partial<TenantFormValues> | Tenant | null;
  submitLabel?: string;
  isSaving?: boolean;
  onSubmit: (values: TenantFormValues) => Promise<void> | void;
  onCancel?: () => void;
};

const emptyValues: TenantFormValues = {
  user_id: null,
  full_name: "",
  email: "",
  phone: "",
  emergency_contact: null,
};

function normalizeEmergencyContact(value: Record<string, unknown> | null | undefined) {
  if (!value) {
    return null;
  }

  if (typeof value === "object" && !Array.isArray(value)) {
    return value;
  }

  return null;
}

export function TenantForm({
  initialValues,
  submitLabel = "Save tenant",
  isSaving = false,
  onSubmit,
  onCancel,
}: TenantFormProps) {
  const [values, setValues] = useState<TenantFormValues>(
    initialValues
      ? {
          ...emptyValues,
          ...initialValues,
          user_id: initialValues.user_id ?? null,
          emergency_contact: normalizeEmergencyContact(initialValues.emergency_contact),
        }
      : emptyValues,
  );

  useEffect(() => {
    setValues(
      initialValues
        ? {
            ...emptyValues,
            ...initialValues,
            user_id: initialValues.user_id ?? null,
            emergency_contact: normalizeEmergencyContact(initialValues.emergency_contact),
          }
        : emptyValues,
    );
  }, [initialValues]);

  function updateField<K extends keyof TenantFormValues>(field: K, value: TenantFormValues[K]) {
    setValues((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    await onSubmit({
      ...values,
      user_id: values.user_id || null,
      emergency_contact: values.emergency_contact ?? null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="grid gap-5 md:grid-cols-2">
        <div className="md:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="tenant-name">
            Full name
          </label>
          <Input
            id="tenant-name"
            value={values.full_name}
            onChange={(event) => updateField("full_name", event.target.value)}
            placeholder="Jordan Smith"
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="tenant-email">
            Email
          </label>
          <Input
            id="tenant-email"
            type="email"
            value={values.email}
            onChange={(event) => updateField("email", event.target.value)}
            placeholder="jordan@example.com"
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="tenant-phone">
            Phone
          </label>
          <Input
            id="tenant-phone"
            value={values.phone}
            onChange={(event) => updateField("phone", event.target.value)}
            placeholder="(555) 123-4567"
            required
          />
        </div>

        <div className="md:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="tenant-user-id">
            Linked user ID (optional)
          </label>
          <Input
            id="tenant-user-id"
            value={values.user_id ?? ""}
            onChange={(event) => updateField("user_id", event.target.value || null)}
            placeholder="uuid or leave blank"
          />
        </div>

        <div className="md:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="tenant-emergency-contact">
            Emergency contact (JSON)
          </label>
          <textarea
            id="tenant-emergency-contact"
            value={values.emergency_contact ? JSON.stringify(values.emergency_contact, null, 2) : ""}
            onChange={(event) => {
              const raw = event.target.value.trim();
              if (!raw) {
                updateField("emergency_contact", null);
                return;
              }

              try {
                const parsed = JSON.parse(raw) as Record<string, unknown>;
                updateField("emergency_contact", typeof parsed === "object" && parsed !== null ? parsed : null);
              } catch {
                updateField("emergency_contact", { raw_value: event.target.value } as Record<string, unknown>);
              }
            }}
            placeholder='{"name": "Alex Smith", "phone": "555-0000"}'
            className="min-h-[110px] w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          />
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
