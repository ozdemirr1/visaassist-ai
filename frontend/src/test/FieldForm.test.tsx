import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DocumentFields, FieldInfo } from "../api/types";
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
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const [url, init] = fetchMock.mock.calls[1] as [string, RequestInit];
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
