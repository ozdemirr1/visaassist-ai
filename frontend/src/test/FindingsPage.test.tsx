import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CheckRun } from "../api/types";
import i18n from "../i18n";
import { DestinationsPage } from "../pages/DestinationsPage";
import { FindingsPage, runChange } from "../pages/FindingsPage";

const source = {
  source_id: "s",
  title: "Checklist",
  publisher: "NetherlandsWorldwide",
  url: "https://example.org/checklist",
  section: "Travel document",
  passage: "The passport has at least 2 empty visa pages.",
  basis: "stated",
};

const run = (id: string, bank: string, pages: string): CheckRun => ({
  id,
  created_at: "2026-11-12T10:00:00Z",
  requirement_set_id: "set",
  missing_documents: ["nl-req-photo"],
  rules: [
    { rule_id: "bank", severity: "error", status: bank as "passed", issues: [] },
    { rule_id: "pages", severity: "error", status: pages as "passed", issues: [] },
  ],
  summary: { missing_documents: 1, passed: 1, failed: 1, incomplete: 0, skipped: 0 },
});

const responses: Record<string, unknown> = {
  "/api/auth/me": { id: "u1", email: "ayse@example.com", role: "applicant", language: "tr" },
  "/api/applications/f1": {
    id: "f1",
    destination: "NL",
    visa: "schengen-c",
    purpose: "tourism",
    profile: "employed",
    trip_start: "2027-04-10",
    trip_end: "2027-04-20",
    application_date: "2027-03-01",
    step: "documents",
    requirement_set_id: "set",
    created_at: "2026-11-11T10:00:00Z",
    events: [],
  },
  "/api/applications/f1/check": {
    requirement_set_id: "set",
    missing_documents: ["nl-req-photo"],
    rules: [
      {
        rule_id: "pages",
        severity: "error",
        status: "failed",
        issues: [
          {
            code: "below_minimum",
            document_id: "d1",
            document_type: "passport",
            document_title: "Pasaport",
            field: "blank_pages",
            field_title: "Boş vize sayfası",
            value: 1,
            expected: 2,
          },
        ],
      },
      { rule_id: "bank", severity: "error", status: "passed", issues: [] },
    ],
    summary: { missing_documents: 1, passed: 1, failed: 1, incomplete: 0, skipped: 3 },
  },
  "/api/checklist": {
    requirement_set_id: "set",
    destination: "NL",
    profile: "employed",
    language: "tr",
    items: [
      {
        id: "nl-req-photo",
        layer: "national",
        document: { id: "photo", title: "Vesikalık fotoğraf", multiple: false },
        submit_as: "original",
        note: null,
        source,
      },
    ],
    rules: [
      { id: "pages", title: "Pasaportta en az 2 boş vize sayfası var", severity: "error", kind: "min_value", source },
      { id: "bank", title: "Banka dökümü son 3 ayı kapsıyor", severity: "error", kind: "covers_recent_months", source },
    ],
    translation: { required: false, languages: [] },
  },
  "/api/applications/f1/checks": [run("r2", "passed", "failed"), run("r1", "incomplete", "passed")],
  "/api/destinations": {
    checked_on: "2026-11-12",
    destinations: [
      {
        id: "NL",
        schengen: true,
        facts: [
          {
            id: "when",
            title: "Ne zaman başvurulur",
            text: "Seyahat tarihinden en erken 6 ay, en geç 15 takvim günü önce.",
            source: { ...source, section: "Step 3: Make an appointment" },
          },
        ],
      },
    ],
  },
};

function stubApi() {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const path = url.split("?")[0];
    const body = init?.method === "POST" ? run("r3", "passed", "failed") : responses[path];
    return Promise.resolve(new Response(JSON.stringify(body), { status: body === undefined ? 404 : 200 }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderAt(path: string) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="applications/:id/findings" element={<FindingsPage />} />
          <Route path="destinations" element={<DestinationsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("findings page", () => {
  it("groups the check by state and shows each problem with its official source", async () => {
    await i18n.changeLanguage("tr");
    stubApi();
    renderAt("/applications/f1/findings");
    expect(
      await screen.findByText("Pasaport: Boş vize sayfası 1; en az 2 olmalı."),
    ).toBeInTheDocument();
    expect(screen.getByText("Pasaportta en az 2 boş vize sayfası var")).toBeInTheDocument();
    expect(screen.getByText(source.passage)).toBeInTheDocument();
    expect(screen.getByText("Vesikalık fotoğraf")).toBeInTheDocument();
    expect(screen.getByText("Banka dökümü son 3 ayı kapsıyor")).toBeInTheDocument();
    expect(screen.getByText(/3 kural, belgesi yüklenmediği için/)).toBeInTheDocument();
    expect(screen.getAllByText(/vize kararı hakkında bir şey söylemez/).length).toBeGreaterThan(0);
  });

  it("lists kept checks with the change since the one before, and keeps a new one", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubApi();
    renderAt("/applications/f1/findings");
    expect(await screen.findByText("Öncekine göre 1 kural düzeldi")).toBeInTheDocument();
    expect(screen.getByText("Öncekine göre 1 kural geriledi")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Bu sonucu kaydet" }));
    expect(await screen.findByRole("button", { name: "Kaydedildi" })).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(post?.[0]).toBe("/api/applications/f1/checks");
    expect(screen.getAllByRole("listitem").filter((li) => li.textContent?.includes("eksik belge"))).toHaveLength(3);
  });
});

describe("runChange", () => {
  it("counts rules that started or stopped passing", () => {
    expect(runChange(run("b", "passed", "failed"), run("a", "incomplete", "passed"))).toEqual({
      improved: 1,
      worsened: 1,
    });
    expect(runChange(run("b", "failed", "passed"), run("a", "incomplete", "passed"))).toEqual({
      improved: 0,
      worsened: 0,
    });
  });
});

describe("destinations page", () => {
  it("shows each fact with a link to the official page it comes from", async () => {
    await i18n.changeLanguage("tr");
    stubApi();
    renderAt("/destinations");
    expect(await screen.findByRole("heading", { name: "Hollanda" })).toBeInTheDocument();
    expect(screen.getByText("Schengen üyesi")).toBeInTheDocument();
    expect(screen.getByText(/en geç 15 takvim günü önce/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "NetherlandsWorldwide" });
    expect(link).toHaveAttribute("href", source.url);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText("Resmî sayfalar 12 Kasım 2026 tarihinde okundu")).toBeInTheDocument();
  });
});
