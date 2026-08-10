import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomePage from "../../src/app/page";

describe("HomePage", () => {
  it("renders the RentFlow application shell", () => {
    const html = renderToStaticMarkup(createElement(HomePage));

    expect(html).toContain("RentFlow");
    expect(html).toContain("Modern property management built with Next.js");
  });
});
