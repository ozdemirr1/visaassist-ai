import { render, screen } from "@testing-library/react";
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
    expect(screen.getByText("Pasaport")).toBeInTheDocument();
    expect(screen.getByText(/Aslı ve fotokopisi/)).toBeInTheDocument();
    expect(screen.getAllByText(source.passage)).toHaveLength(2);
    const links = screen.getAllByRole("link", { name: "Resmî kaynağı aç" });
    expect(links[0]).toHaveAttribute("href", source.url);
    expect(links[0]).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByRole("note")).toHaveTextContent("İngilizce / Norveççe");
  });

  it("switches the interface text to English", async () => {
    await i18n.changeLanguage("en");
    render(<ChecklistView checklist={checklist} />);
    expect(screen.getByText("Documents (1)")).toBeInTheDocument();
    expect(screen.getByText("Required")).toBeInTheDocument();
    await i18n.changeLanguage("tr");
  });
});
