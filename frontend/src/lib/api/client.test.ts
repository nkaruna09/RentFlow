import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch, get, post, setAccessTokenProvider } from "@/lib/api/client";

describe("API client", () => {
  beforeEach(() => {
    setAccessTokenProvider(() => "test-token");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setAccessTokenProvider(() => null);
  });

  it("adds authentication and defined query parameters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await get("/payments/invoices", {
      lease_id: "lease 1",
      status: "partial",
      ignored: undefined,
    });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(
      url.endsWith("/payments/invoices?lease_id=lease+1&status=partial"),
    ).toBe(true);
    expect(new Headers(init.headers).get("Authorization")).toBe(
      "Bearer test-token",
    );
  });

  it("serializes JSON request bodies", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "payment-1" }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await post("/payments/invoices/invoice-1/payments", { amount: "20.00" });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ amount: "20.00" }));
    expect(new Headers(init.headers).get("Content-Type")).toBe(
      "application/json",
    );
  });

  it("maps structured error responses to ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Validation failed",
            code: "invalid_payment",
            field_errors: { amount: "must be positive" },
          }),
          { status: 422 },
        ),
      ),
    );

    const request = apiFetch("/payments/invoices");

    await expect(request).rejects.toMatchObject({
      status: 422,
      message: "Validation failed",
      code: "invalid_payment",
      fieldErrors: { amount: "must be positive" },
    });
  });

  it("returns undefined for an empty 204 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );

    await expect(
      apiFetch("/resource", { method: "DELETE" }),
    ).resolves.toBeUndefined();
  });
});
