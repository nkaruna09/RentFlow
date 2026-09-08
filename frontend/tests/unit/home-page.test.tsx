import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import DashboardPage from "../../src/app/(dashboard)/page";

describe("DashboardPage", () => {
  it("renders the live dashboard instead of the old scaffold", () => {
    const html = renderToStaticMarkup(createElement(DashboardPage));

    expect(html).toContain("Dashboard");
    expect(html).toContain("Live portfolio snapshot across units and leases.");
    expect(html).not.toContain("This is a placeholder dashboard page.");
  });
});
