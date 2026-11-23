import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DocumentFields, Extraction, FieldInfo } from "../api/types";
import { FieldForm, toValues } from "../components/FieldForm";
import i18n from "../i18n";

const fields: FieldInfo[] = [
  { id: "insured_name", type: "text", title: "Sigortalı", optional: false, value: "Ayşe Yılmaz" },
  { id: "coverage_start", type: "date", title: "Teminat başlangıcı", optional: false, value: null },
  { id: "coverage_amount", type: "money", title: "Tedavi teminat tutarı", optional: false, value: null },
  { id: "covers_all_schengen", type: "bool", title: "Tüm Schengen ülkelerinde geçerli", optional: false, value: null },
  { id: "blank_pages", type: "int", title: "Boş vize sayfası", optional: false, value: null },
];
const body: DocumentFields = { document_id: "d1", document_type_id: "travel_insurance", fields };

function stubFetch() {
  const fetchMock = vi.fn((..._request: unknown[]) =>
    Promise.resolve(new Response(JSON.stringify(body), { status: 200 })),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderForm() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <FieldForm applicationFileId="f1" documentId="d1" />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("field form", () => {
  it("shows the fields of the document with the values entered so far", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubFetch();
    renderForm();
    expect(await screen.findByLabelText("Sigortalı")).toHaveValue("Ayşe Yılmaz");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/documents/d1/fields?lang=tr");
    expect(screen.getByLabelText("Teminat başlangıcı")).toHaveAttribute("type", "date");
    expect(screen.getByRole("group", { name: "Tüm Schengen ülkelerinde geçerli" })).toBeInTheDocument();
    expect(screen.getByText("1 / 5 alan dolu")).toBeInTheDocument();
  });

  it("sends every field in its stored form and empty inputs as null", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubFetch();
    renderForm();
    fireEvent.change(await screen.findByLabelText("Teminat başlangıcı"), { target: { value: "2027-04-10" } });
    fireEvent.change(screen.getByLabelText("Tedavi teminat tutarı"), { target: { value: "30000" } });
    fireEvent.click(screen.getByRole("radio", { name: "Evet" }));
    fireEvent.change(screen.getByLabelText("Sigortalı"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Kaydet" }));
    const isPut = (call: unknown[]) => (call[1] as RequestInit | undefined)?.method === "PUT";
    await vi.waitFor(() => expect(fetchMock.mock.calls.some(isPut)).toBe(true));
    const [url, init] = fetchMock.mock.calls.find(isPut) as [string, RequestInit];
    expect(url).toBe("/api/documents/d1/fields?lang=tr");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({
      values: {
        insured_name: null,
        coverage_start: "2027-04-10",
        coverage_amount: { amount: 30000, currency: "EUR" },
        covers_all_schengen: true,
        blank_pages: null,
      },
    });
    expect(await screen.findByRole("button", { name: "Kaydedildi" })).toBeInTheDocument();
  });
});

describe("reading the document with a model", () => {
  const extraction: Extraction = {
    document_id: "d1",
    fields: [
      { id: "insured_name", type: "text", title: "Sigortalı", value: null, confidence: 0 },
      { id: "coverage_start", type: "date", title: "Teminat başlangıcı", value: "2027-04-10", confidence: 0.95 },
      {
        id: "coverage_amount",
        type: "money",
        title: "Tedavi teminat tutarı",
        value: { amount: 30000, currency: "EUR" },
        confidence: 0.5,
      },
      { id: "covers_all_schengen", type: "bool", title: "Tüm Schengen ülkelerinde geçerli", value: true, confidence: 0.9 },
      { id: "blank_pages", type: "int", title: "Boş vize sayfası", value: null, confidence: 0.2 },
    ],
    invalid: ["blank_pages"],
    model: "gpt-5.4-mini",
    seconds: 2.1,
    cost_usd: 0.002,
  };

  function stubRoutes(available: boolean) {
    const fetchMock = vi.fn((url: unknown, _init?: unknown) => {
      const json =
        url === "/api/extraction/status"
          ? { available, model: available ? "gpt-5.4-mini" : null }
          : String(url).includes("/extract")
            ? extraction
            : body;
      return Promise.resolve(new Response(JSON.stringify(json), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("fills the draft with the proposed values, keeps the rest and saves nothing", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubRoutes(true);
    renderForm();
    fireEvent.click(await screen.findByRole("button", { name: "Belgeden oku" }));
    expect(await screen.findByRole("status")).toHaveTextContent("gpt-5.4-mini 3 alanı doldurdu");
    expect(screen.getByRole("status")).toHaveTextContent("1 değer beklenen biçimde değildi");
    expect(screen.getByLabelText(/Teminat başlangıcı/)).toHaveValue("2027-04-10");
    expect(screen.getByLabelText(/Tedavi teminat tutarı/)).toHaveValue(30000);
    expect(screen.getByLabelText(/Tedavi teminat tutarı/)).toHaveAccessibleName(/model emin değil/);
    expect(screen.getByLabelText(/Sigortalı/)).toHaveValue("Ayşe Yılmaz"); // not read, kept
    const methods = fetchMock.mock.calls.map(([url, init]) => [
      url,
      (init as RequestInit | undefined)?.method ?? "GET",
    ]);
    expect(methods).toContainEqual(["/api/documents/d1/extract?lang=tr", "POST"]);
    expect(methods.some(([, method]) => method === "PUT")).toBe(false);
  });

  it("offers nothing when no model is configured", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubRoutes(false);
    renderForm();
    await screen.findByLabelText("Sigortalı");
    await vi.waitFor(() =>
      expect(fetchMock.mock.calls.map(([url]) => url)).toContain("/api/extraction/status"),
    );
    expect(screen.queryByRole("button", { name: "Belgeden oku" })).toBeNull();
  });
});

describe("toValues", () => {
  it("turns the text of the inputs into typed values", () => {
    expect(
      toValues(fields, {
        insured_name: "  Ayşe Yılmaz ",
        coverage_start: "",
        coverage_amount: "1500,5",
        "coverage_amount.currency": "TRY",
        covers_all_schengen: "false",
        blank_pages: "4",
      }),
    ).toEqual({
      insured_name: "Ayşe Yılmaz",
      coverage_start: null,
      coverage_amount: { amount: 1500.5, currency: "TRY" },
      covers_all_schengen: false,
      blank_pages: 4,
    });
  });
});
