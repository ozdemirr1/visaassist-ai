import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Checklist } from "../api/types";
import { ChecklistView } from "../components/ChecklistView";
import i18n from "../i18n";

const source = {
  source_id: "no-checklist-c-visa-tr",
  title: "Checklist for visitor's visa",
  publisher: "Norwegian Embassy in Ankara",
  url: "https://www.norway.no/example.pdf",
  section: "General rules",
  passage: "All documents must be translated into English or Norwegian.",
  basis: "stated" as const,
};

const checklist: Checklist = {
  requirement_set_id: "a".repeat(64),
  destination: "NO",
  profile: "employed",
  language: "tr",
  items: [
    {
      id: "nl-req-passport",
      layer: "national",
      document: { id: "passport", title: "Pasaport", multiple: false },
      submit_as: "original_and_copy",
      note: null,
      source,
    },
  ],
  rules: [
    {
      id: "no-rule-translation",
      title: "Tercüme",
      severity: "error",
      kind: "translation_present",
      source,
    },
  ],
  translation: { required: true, languages: ["en", "no"] },
};

describe("ChecklistView", () => {
  it("shows every document with its official source and the translation note", async () => {
    await i18n.changeLanguage("tr");
    render(<ChecklistView checklist={checklist} />);
    expect(screen.getByText("Belgeler (1)")).toBeInTheDocument();
    expect(screen.getAllByText("Pasaport")).toHaveLength(2); // table row and source panel
    expect(screen.getByText("Aslı ve fotokopisi")).toBeInTheDocument();
    expect(screen.getByText(source.passage)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Resmî kaynağı aç" });
    expect(link).toHaveAttribute("href", source.url);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByRole("note")).toHaveTextContent("İngilizce / Norveççe");
    expect(screen.queryByText("Eksik")).not.toBeInTheDocument(); // no status without uploads
  });

  it("shows the source of a rule when it is selected", async () => {
    await i18n.changeLanguage("tr");
    render(<ChecklistView checklist={checklist} />);
    fireEvent.click(screen.getByRole("button", { name: /Tercüme/ }));
    expect(screen.getByText("Kural")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tercüme" })).toBeInTheDocument();
  });

  it("shows upload status and filters by it when ready items are known", async () => {
    await i18n.changeLanguage("tr");
    const { rerender } = render(<ChecklistView checklist={checklist} readyIds={new Set()} />);
    expect(screen.getByRole("button", { name: /Pasaport/ })).toHaveTextContent("Eksik");
    fireEvent.click(screen.getByRole("button", { name: /Hazır/ }));
    expect(screen.getByText("Eşleşen belge yok.")).toBeInTheDocument();
    rerender(<ChecklistView checklist={checklist} readyIds={new Set(["nl-req-passport"])} />);
    expect(screen.getByRole("button", { name: /Pasaport/ })).toHaveTextContent("Hazır");
  });

  it("filters documents by the search text", async () => {
    await i18n.changeLanguage("tr");
    render(<ChecklistView checklist={checklist} />);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "sigorta" } });
    expect(screen.getByText("Eşleşen belge yok.")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "pasa" } });
    expect(screen.getByRole("button", { name: /Pasaport/ })).toBeInTheDocument();
  });

  it("switches the interface text to English", async () => {
    await i18n.changeLanguage("en");
    render(<ChecklistView checklist={checklist} />);
    expect(screen.getByText("Documents (1)")).toBeInTheDocument();
    expect(screen.getByText("Required")).toBeInTheDocument();
    await i18n.changeLanguage("tr");
  });
});
