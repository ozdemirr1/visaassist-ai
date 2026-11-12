import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Checklist, RuleResult } from "../api/types";
import { ChecklistView } from "../components/ChecklistView";
import { FindingsPanel, issueValue } from "../components/FindingsPanel";
import i18n from "../i18n";

const failed: RuleResult = {
  rule_id: "eu-rule-bank-statement-period",
  severity: "error",
  status: "failed",
  issues: [
    {
      code: "period_too_short",
      document_id: "d1",
      document_type: "bank_statement",
      document_title: "Banka hesap dökümü",
      field: "period_start",
      field_title: "Döküm başlangıcı",
      value: "2026-12-20",
      expected: "2026-11-25",
    },
  ],
};

const source = {
  source_id: "s",
  title: "t",
  publisher: "p",
  url: "https://example.org",
  section: "1",
  passage: "x",
  basis: "stated" as const,
};

const checklist: Checklist = {
  requirement_set_id: "a".repeat(64),
  destination: "NL",
  profile: "employed",
  language: "tr",
  items: [],
  rules: [
    {
      id: failed.rule_id,
      title: "Banka dökümü son 3 ayı kapsıyor",
      severity: "error",
      kind: "covers_recent_months",
      source,
    },
  ],
  translation: { required: false, languages: [] },
};

describe("findings", () => {
  it("say which document and field broke the rule, with dates in the interface language", async () => {
    await i18n.changeLanguage("tr");
    render(<FindingsPanel result={failed} />);
    expect(screen.getByText("Sorun var")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Banka hesap dökümü: Döküm başlangıcı 20 Aralık 2026; dönemin en geç 25 Kasım 2026 tarihinde başlaması gerekir.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/vize kararı hakkında bir şey söylemez/)).toBeInTheDocument();
  });

  it("show the state of each rule in the list and the finding of the selected one", async () => {
    await i18n.changeLanguage("tr");
    render(
      <ChecklistView
        checklist={checklist}
        ruleResults={new Map([[failed.rule_id, failed]])}
        rulePanel={() => <FindingsPanel result={failed} />}
      />,
    );
    const row = screen.getByRole("button", { name: /Banka dökümü son 3 ayı/ });
    expect(row).toHaveTextContent("Sorun var");
    fireEvent.click(row);
    expect(screen.getByText("Ön kontrol sonucu")).toBeInTheDocument();
  });

  it("format amounts, months, languages and lists", () => {
    const t = i18n.getFixedT("tr");
    expect(issueValue({ amount: 30000, currency: "EUR" }, "tr", t)).toBe("30.000 EUR");
    expect(issueValue("2027-01", "tr", t)).toBe("Ocak 2027");
    expect(issueValue(["en", "no"], "tr", t)).toBe("İngilizce / Norveççe");
    expect(issueValue(2, "tr", t)).toBe("2");
    expect(issueValue(null, "tr", t)).toBe("");
  });
});
