import { describe, expect, it } from "vitest";

import en from "../locales/en.json";
import tr from "../locales/tr.json";

function keys(value: unknown, prefix = ""): string[] {
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, child]) => keys(child, `${prefix}${key}.`));
  }
  return [prefix.slice(0, -1)];
}

describe("translation files (NFR-10)", () => {
  it("have the same keys in Turkish and English", () => {
    expect(keys(en).sort()).toEqual(keys(tr).sort());
  });

  it("have no empty text", () => {
    for (const file of [tr, en]) {
      const empty = keys(file).filter((key) => {
        const text = key.split(".").reduce<unknown>((node, part) => (node as Record<string, unknown>)[part], file);
        return typeof text !== "string" || text.trim() === "";
      });
      expect(empty).toEqual([]);
    }
  });
});
