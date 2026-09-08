import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { resolveLeaseSubmitError } from "./lease-form";

describe("lease form error handling", () => {
  it("surfaces overlap conflicts as an inline message", () => {
    const error = new ApiError(409, {
      detail: "Lease overlaps an active lease for this unit",
      code: "lease_overlap",
    });

    expect(resolveLeaseSubmitError(error)).toContain("overlaps an active lease");
  });
});
