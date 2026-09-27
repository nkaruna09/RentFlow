import { describe, expect, it } from "vitest";

import { toPaymentInput } from "@/components/forms/payment-form";

describe("payment form values", () => {
  it("converts the selected date and trims an empty reference", () => {
    expect(
      toPaymentInput({
        amount: "125.50",
        method: "bank_transfer",
        reference: "   ",
        paid_date: "2026-09-26",
      }),
    ).toEqual({
      amount: "125.50",
      method: "bank_transfer",
      reference: null,
      paid_at: "2026-09-26T12:00:00.000Z",
    });
  });

  it("preserves a supplied reference and payment method", () => {
    expect(
      toPaymentInput({
        amount: "20.00",
        method: "cash",
        reference: " receipt-42 ",
        paid_date: "2026-09-27",
      }),
    ).toEqual({
      amount: "20.00",
      method: "cash",
      reference: "receipt-42",
      paid_at: "2026-09-27T12:00:00.000Z",
    });
  });
});
