import { describe, expect, it } from "vitest";

import { tripDays, tripProblem } from "../trip";

describe("trip dates (same rules as the API)", () => {
  it("accepts a normal trip and counts both ends", () => {
    expect(tripProblem("2027-04-10", "2027-04-20")).toBeNull();
    expect(tripDays("2027-04-10", "2027-04-20")).toBe(11);
    expect(tripDays("2027-04-10", "2027-04-10")).toBe(1);
  });

  it("refuses missing dates, a return before departure and more than 90 days", () => {
    expect(tripProblem("", "2027-04-20")).toBe("missing");
    expect(tripProblem("2027-04-20", "2027-04-10")).toBe("endBeforeStart");
    expect(tripProblem("2027-04-01", "2027-06-29")).toBeNull(); // 90 days
    expect(tripProblem("2027-04-01", "2027-06-30")).toBe("tooLong"); // 91 days
  });
});
