import { describe, expect, it } from "vitest";

import { formatPercent } from "../components/format";

describe("formatPercent", () => {
  it("puts the sign before the number in Turkish and after it in English", () => {
    expect(formatPercent(89, "tr")).toBe("%89");
    expect(formatPercent(89, "en")).toBe("89%");
    expect(formatPercent(100, "en")).toBe("100%");
  });
});
