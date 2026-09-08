"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Property, Unit, UnitCreate, UnitStatus } from "@/types/api";

export type UnitFormValues = UnitCreate;

type UnitFormProps = {
  initialValues?: Partial<UnitFormValues> | Unit | null;
  properties?: Property[];
  submitLabel?: string;
  isSaving?: boolean;
  onSubmit: (values: UnitFormValues) => Promise<void> | void;
  onCancel?: () => void;
};

const emptyValues: UnitFormValues = {
  property_id: "",
  label: "",
  bedrooms: "",
  bathrooms: "",
  square_feet: null,
  market_rent: "",
  status: "vacant",
};

const statusOptions: Array<{ value: UnitStatus; label: string }> = [
  { value: "vacant", label: "Vacant" },
  { value: "occupied", label: "Occupied" },
  { value: "unavailable", label: "Unavailable" },
];

export function UnitForm({
  initialValues,
  properties = [],
  submitLabel = "Save unit",
  isSaving = false,
  onSubmit,
  onCancel,
}: UnitFormProps) {
  const [values, setValues] = useState<UnitFormValues>(
    initialValues
      ? {
          ...emptyValues,
          ...initialValues,
          square_feet: initialValues.square_feet ?? null,
        }
      : emptyValues,
  );

  useEffect(() => {
    setValues(
      initialValues
        ? {
            ...emptyValues,
            ...initialValues,
            square_feet: initialValues.square_feet ?? null,
          }
        : emptyValues,
    );
  }, [initialValues]);

  function updateField<K extends keyof UnitFormValues>(field: K, value: UnitFormValues[K]) {
    setValues((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    await onSubmit({
      ...values,
      square_feet: values.square_feet == null ? null : Number(values.square_feet),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-property">
            Property
          </label>
          <select
            id="unit-property"
            value={values.property_id}
            onChange={(event) => updateField("property_id", event.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            required
          >
            <option value="">Select a property</option>
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-label">
            Unit label
          </label>
          <Input
            id="unit-label"
            value={values.label}
            onChange={(event) => updateField("label", event.target.value)}
            placeholder="1A"
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-bedrooms">
            Bedrooms
          </label>
          <Input
            id="unit-bedrooms"
            type="number"
            min="0"
            step="1"
            value={values.bedrooms}
            onChange={(event) => updateField("bedrooms", event.target.value)}
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-bathrooms">
            Bathrooms
          </label>
          <Input
            id="unit-bathrooms"
            type="number"
            min="0"
            step="0.5"
            value={values.bathrooms}
            onChange={(event) => updateField("bathrooms", event.target.value)}
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-square-feet">
            Square feet
          </label>
          <Input
            id="unit-square-feet"
            type="number"
            min="0"
            step="1"
            value={values.square_feet ?? ""}
            onChange={(event) =>
              updateField("square_feet", event.target.value === "" ? null : Number(event.target.value))
            }
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-market-rent">
            Market rent
          </label>
          <Input
            id="unit-market-rent"
            type="number"
            min="0"
            step="0.01"
            value={values.market_rent}
            onChange={(event) => updateField("market_rent", event.target.value)}
            required
          />
        </div>

        <div className="md:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-status">
            Status
          </label>
          <select
            id="unit-status"
            value={values.status}
            onChange={(event) => updateField("status", event.target.value as UnitStatus)}
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
