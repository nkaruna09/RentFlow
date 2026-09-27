import { beforeEach, describe, expect, it, vi } from "vitest";

import { get, patch, post } from "@/lib/api/client";
import {
  addMaintenanceComment,
  createMaintenanceRequest,
  getMaintenanceRequest,
  listMaintenanceRequests,
  updateMaintenanceRequest,
} from "@/lib/api/maintenance";

vi.mock("@/lib/api/client", () => ({
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
}));

describe("maintenance API bindings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("binds list filters and request operations", () => {
    const input = {
      unit_id: "unit-1",
      title: "Leaking faucet",
      description: "The kitchen faucet is leaking.",
      priority: "high" as const,
    };

    void listMaintenanceRequests({
      unit_id: "unit-1",
      priority: "high",
      page: 2,
      page_size: 25,
    });
    void createMaintenanceRequest(input);
    void getMaintenanceRequest("request/1");
    void updateMaintenanceRequest("request/1", { status: "resolved" });
    void addMaintenanceComment("request/1", { body: "Repair complete" });

    expect(get).toHaveBeenCalledWith("/maintenance", {
      unit_id: "unit-1",
      priority: "high",
      page: 2,
      page_size: 25,
    });
    expect(post).toHaveBeenCalledWith("/maintenance", input);
    expect(get).toHaveBeenCalledWith("/maintenance/request%2F1");
    expect(patch).toHaveBeenCalledWith("/maintenance/request%2F1", {
      status: "resolved",
    });
    expect(post).toHaveBeenCalledWith("/maintenance/request%2F1/comments", {
      body: "Repair complete",
    });
  });
});
