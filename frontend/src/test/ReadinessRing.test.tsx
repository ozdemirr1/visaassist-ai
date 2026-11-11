import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReadinessRing } from "../components/ReadinessRing";
import { daysUntil } from "../components/format";

describe("ReadinessRing", () => {
  it("draws one segment per document and lights the ready ones", () => {
    const { container, getByRole } = render(<ReadinessRing total={12} ready={5} label="5 / 12" />);
    expect(getByRole("img", { name: "5 / 12" })).toBeInTheDocument();
    expect(container.querySelectorAll("circle")).toHaveLength(12);
    expect(container.querySelectorAll('circle[data-ready="true"]')).toHaveLength(5);
  });

  it("draws an empty ring before the checklist is known", () => {
    const { container } = render(<ReadinessRing total={0} ready={0} label="-" />);
    expect(container.querySelectorAll("circle")).toHaveLength(1);
    expect(container.querySelectorAll('circle[data-ready="true"]')).toHaveLength(0);
  });
});

describe("daysUntil", () => {
  it("counts whole days and never goes below zero", () => {
    const today = new Date(2026, 10, 11); // 11 November 2026
    expect(daysUntil("2027-03-01", today)).toBe(110);
    expect(daysUntil("2026-11-11", today)).toBe(0);
    expect(daysUntil("2026-11-01", today)).toBe(0);
  });
});
