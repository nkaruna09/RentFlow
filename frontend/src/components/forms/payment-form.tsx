"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Invoice, PaymentCreate, PaymentMethod } from "@/types/api";

export type PaymentFormValues = {
  amount: string;
  method: PaymentMethod;
  reference: string;
  paid_date: string;
};

type PaymentFormProps = {
  invoice: Invoice;
  isSaving?: boolean;
  error?: string | null;
  onSubmit: (values: PaymentCreate) => Promise<void> | void;
  onCancel: () => void;
};

const methodOptions: Array<{ value: PaymentMethod; label: string }> = [
  { value: "bank_transfer", label: "Bank transfer" },
  { value: "card", label: "Card" },
  { value: "cash", label: "Cash" },
  { value: "check", label: "Check" },
  { value: "other", label: "Other" },
];

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

export function toPaymentInput(values: PaymentFormValues): PaymentCreate {
  return {
    amount: values.amount,
    method: values.method,
    reference: values.reference.trim() || null,
    paid_at: `${values.paid_date}T12:00:00.000Z`,
  };
}

export function PaymentForm({
  invoice,
  isSaving = false,
  error = null,
  onSubmit,
  onCancel,
}: PaymentFormProps) {
  const [values, setValues] = useState<PaymentFormValues>({
    amount: "",
    method: "bank_transfer",
    reference: "",
    paid_date: utcToday(),
  });

  useEffect(() => {
    setValues({
      amount: "",
      method: "bank_transfer",
      reference: "",
      paid_date: utcToday(),
    });
  }, [invoice.id]);

  function updateField<K extends keyof PaymentFormValues>(
    field: K,
    value: PaymentFormValues[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onSubmit(toPaymentInput(values));
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-5 rounded-2xl border border-sky-200 bg-sky-50/40 p-5 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-slate-900">Record payment</h2>
          <p className="mt-1 text-sm text-slate-600">
            Invoice {invoice.id.slice(0, 8)} · amount due $
            {Number(invoice.amount_due).toFixed(2)}
          </p>
        </div>
        <button
          type="button"
          className="text-sm font-medium text-slate-500 hover:text-slate-800"
          onClick={onCancel}
        >
          Close
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <label
            className="mb-1.5 block text-sm font-medium text-slate-700"
            htmlFor="payment-amount"
          >
            Amount
          </label>
          <Input
            id="payment-amount"
            type="number"
            min="0.01"
            step="0.01"
            inputMode="decimal"
            value={values.amount}
            onChange={(event) => updateField("amount", event.target.value)}
            required
          />
        </div>

        <div>
          <label
            className="mb-1.5 block text-sm font-medium text-slate-700"
            htmlFor="payment-method"
          >
            Method
          </label>
          <select
            id="payment-method"
            value={values.method}
            onChange={(event) =>
              updateField("method", event.target.value as PaymentMethod)
            }
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          >
            {methodOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            className="mb-1.5 block text-sm font-medium text-slate-700"
            htmlFor="payment-reference"
          >
            Reference
          </label>
          <Input
            id="payment-reference"
            type="text"
            value={values.reference}
            onChange={(event) => updateField("reference", event.target.value)}
            placeholder="Optional"
          />
        </div>

        <div>
          <label
            className="mb-1.5 block text-sm font-medium text-slate-700"
            htmlFor="payment-date"
          >
            Payment date
          </label>
          <Input
            id="payment-date"
            type="date"
            value={values.paid_date}
            onChange={(event) => updateField("paid_date", event.target.value)}
            required
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
          {isSaving ? "Recording..." : "Record payment"}
        </Button>
      </div>
    </form>
  );
}
