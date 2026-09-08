"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Property, PropertyCreate, PropertyType } from "@/types/api";

export type PropertyFormValues = PropertyCreate;

const emptyValues: PropertyFormValues = {
  name: "",
  address_line1: "",
  address_line2: "",
  city: "",
  region: "",
  postal_code: "",
  country: "",
  property_type: "single_family",
};

const propertyTypeOptions: Array<{ value: PropertyType; label: string }> = [
  { value: "single_family", label: "Single family" },
  { value: "multi_family", label: "Multi-family" },
  { value: "condo", label: "Condo" },
  { value: "commercial", label: "Commercial" },
];

type PropertyFormProps = {
  initialValues?: Partial<PropertyFormValues> | Property | null;
  submitLabel?: string;
  isSaving?: boolean;
  onSubmit: (values: PropertyFormValues) => Promise<void> | void;
  onCancel?: () => void;
};

export function PropertyForm({
  initialValues,
  submitLabel = "Save property",
  isSaving = false,
  onSubmit,
  onCancel,
}: PropertyFormProps) {
  const [values, setValues] = useState<PropertyFormValues>(
    initialValues ? { ...emptyValues, ...initialValues, address_line2: initialValues.address_line2 ?? "" } : emptyValues,
  );

  useEffect(() => {
    setValues(
      initialValues
        ? {
            ...emptyValues,
            ...initialValues,
            address_line2: initialValues.address_line2 ?? "",
          }
        : emptyValues,
    );
  }, [initialValues]);

  function updateField<K extends keyof PropertyFormValues>(field: K, value: PropertyFormValues[K]) {
    setValues((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({
      ...values,
      address_line2: values.address_line2 || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="grid gap-5 md:grid-cols-2">
        <div className="md:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="property-name">
            Property name
          </label>
          <Input
            id="property-name"
            value={values.name}
            onChange={(event) => updateField("name", event.target.value)}
            placeholder="Sunset Apartments"
            required
          />
        </div>

        <div className="md:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="property-address-1">
            Street address
          </label>
          <Input
            id="property-address-1"
            value={values.address_line1}
            onChange={(event) => updateField("address_line1", event.target.value)}
            placeholder="123 Main Street"
            required
          />
        </div>

        <div className="md:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="property-address-2">
            Address line 2
          </label>
          <Input
            id="property-address-2"
            value={values.address_line2 ?? ""}
            onChange={(event) => updateField("address_line2", event.target.value)}
            placeholder="Suite 200"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="property-city">
            City
          </label>
          <Input
            id="property-city"
            value={values.city}
            onChange={(event) => updateField("city", event.target.value)}
            placeholder="Austin"
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="property-region">
            State / region
          </label>
          <Input
            id="property-region"
            value={values.region}
            onChange={(event) => updateField("region", event.target.value)}
            placeholder="TX"
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="property-postal-code">
            Postal code
          </label>
          <Input
            id="property-postal-code"
            value={values.postal_code}
            onChange={(event) => updateField("postal_code", event.target.value)}
            placeholder="78701"
            required
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="property-country">
            Country
          </label>
          <Input
            id="property-country"
            value={values.country}
            onChange={(event) => updateField("country", event.target.value)}
            placeholder="United States"
            required
          />
        </div>

        <div className="md:col-span-2">
          <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="property-type">
            Property type
          </label>
          <select
            id="property-type"
            value={values.property_type}
            onChange={(event) => updateField("property_type", event.target.value as PropertyType)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          >
            {propertyTypeOptions.map((option) => (
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
