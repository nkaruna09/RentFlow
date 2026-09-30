"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { MaintenancePriority } from "@/types/api";

export interface MaintenanceFormValues {
  title: string;
  description: string;
  priority: MaintenancePriority;
}

interface MaintenanceFormProps {
  unitLabel: string;
  isSaving?: boolean;
  error?: string | null;
  onSubmit: (values: MaintenanceFormValues) => Promise<void> | void;
  onCancel: () => void;
}

const priorityOptions: Array<{ value: MaintenancePriority; label: string }> = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "emergency", label: "Emergency" },
];

export function MaintenanceForm({
  unitLabel,
  isSaving = false,
  error = null,
  onSubmit,
  onCancel,
}: MaintenanceFormProps) {
  const [values, setValues] = useState<MaintenanceFormValues>({
    title: "",
    description: "",
    priority: "medium",
  });

  function updateField<K extends keyof MaintenanceFormValues>(
    field: K,
    value: MaintenanceFormValues[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onSubmit({
      ...values,
      title: values.title.trim(),
      description: values.description.trim(),
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-5 rounded-2xl border border-sky-200 bg-sky-50/40 p-5 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-slate-900">
            Submit maintenance request
          </h2>
          <p className="mt-1 text-sm text-slate-600">For {unitLabel}</p>
        </div>
        <button
          type="button"
          className="text-sm font-medium text-slate-500 hover:text-slate-800"
          onClick={onCancel}
          disabled={isSaving}
        >
          Close
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label
            className="mb-1.5 block text-sm font-medium text-slate-700"
            htmlFor="maintenance-title"
          >
            Title
          </label>
          <Input
            id="maintenance-title"
            value={values.title}
            onChange={(event) => updateField("title", event.target.value)}
            placeholder="Briefly describe the issue"
            maxLength={200}
            required
          />
        </div>

        <div>
          <label
            className="mb-1.5 block text-sm font-medium text-slate-700"
            htmlFor="maintenance-priority"
          >
            Priority
          </label>
          <select
            id="maintenance-priority"
            value={values.priority}
            onChange={(event) =>
              updateField("priority", event.target.value as MaintenancePriority)
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

        <div className="md:col-span-2">
          <label
            className="mb-1.5 block text-sm font-medium text-slate-700"
            htmlFor="maintenance-description"
          >
            Description
          </label>
          <textarea
            id="maintenance-description"
            value={values.description}
            onChange={(event) => updateField("description", event.target.value)}
            placeholder="Include where the issue is and any relevant details"
            rows={5}
            maxLength={4000}
            required
            className="w-full resize-y rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          />
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={onCancel}
          disabled={isSaving}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={isSaving}>
          {isSaving ? "Submitting..." : "Submit request"}
        </Button>
      </div>
    </form>
  );
}
