import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ChecklistItem, ConsentState, DocumentInfo } from "../api/types";
import { DocumentPanel } from "../components/DocumentPanel";
import i18n from "../i18n";
import { formatSize, uploadProblem } from "../upload";

const item: ChecklistItem = {
  id: "eu-req-bank-statement",
  layer: "eu",
  document: { id: "bank_statement", title: "Banka dökümü", multiple: true },
  submit_as: "original",
  note: null,
  source: {
    source_id: "s",
    title: "t",
    publisher: "p",
    url: "https://example.org",
    section: "1",
    passage: "x",
    basis: "stated",
  },
};

const uploaded: DocumentInfo = {
  id: "d1",
  application_file_id: "f1",
  requirement_id: item.id,
  document_type_id: "bank_statement",
  original_name: "dokum.pdf",
  mime_type: "application/pdf",
  size_bytes: 2_621_440,
  uploaded_at: "2026-11-11T10:00:00Z",
  delete_after: "2027-05-20T00:00:00Z",
};

function renderPanel(consent: ConsentState, documents: DocumentInfo[] = []) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <DocumentPanel applicationFileId="f1" item={item} documents={documents} consent={consent} />
    </QueryClientProvider>,
  );
}

function stubFetch(status: number, body: unknown) {
  const fetchMock = vi
    .fn()
    .mockResolvedValue(new Response(status === 204 ? null : JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function fileOf(type: string, size: number): File {
  const file = new File(["x"], "belge", { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

const given: ConsentState = { version: "consent-v1", given: true };
const input = () => screen.getByLabelText(/Dosyayı buraya bırakın/);

afterEach(() => vi.unstubAllGlobals());

describe("document panel", () => {
  it("asks for consent before any upload control is shown", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubFetch(200, given);
    renderPanel({ version: "consent-v1", given: false });
    expect(screen.getByRole("heading", { name: "Belge yükleme onayı" })).toBeInTheDocument();
    expect(screen.getByText(/consent-v1/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Dosyayı buraya bırakın/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Okudum, kabul ediyorum" }));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/consent");
    expect(init.method).toBe("POST");
  });

  it("refuses a file that is too large or of another type without sending it", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubFetch(201, uploaded);
    renderPanel(given);
    fireEvent.change(input(), { target: { files: [fileOf("application/pdf", 11 * 1024 * 1024)] } });
    expect(screen.getByRole("alert")).toHaveTextContent("Dosya en fazla 10 MB olabilir.");
    fireEvent.change(input(), { target: { files: [fileOf("application/zip", 100)] } });
    expect(screen.getByRole("alert")).toHaveTextContent("Yalnızca PDF, JPEG ve PNG");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("uploads the chosen file for this checklist item", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubFetch(201, uploaded);
    renderPanel(given);
    const file = fileOf("image/jpeg", 2048);
    fireEvent.change(input(), { target: { files: [file] } });
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/applications/f1/documents");
    expect(init.body.get("requirement_id")).toBe("eu-req-bank-statement");
    expect(init.body.get("file")).toBeInstanceOf(File);
  });

  it("shows the server's refusal in the interface language", async () => {
    await i18n.changeLanguage("tr");
    stubFetch(415, { detail: "Only PDF, JPEG and PNG files can be uploaded." });
    renderPanel(given);
    fireEvent.change(input(), { target: { files: [fileOf("image/png", 2048)] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Yalnızca PDF, JPEG ve PNG");
  });

  it("lists uploaded files with a download link and asks before deleting", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = stubFetch(204, null);
    renderPanel(given, [uploaded]);
    expect(screen.getByText("dokum.pdf")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /İndir/ })).toHaveAttribute("href", "/api/documents/d1/content");
    expect(screen.getByText(/20 Mayıs 2027/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Sil/ }));
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Evet, sil" }));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/documents/d1");
    expect(init.method).toBe("DELETE");
  });
});

describe("upload checks", () => {
  it("accept the three document types up to 10 MB", () => {
    expect(uploadProblem({ type: "image/png", size: 10 * 1024 * 1024 })).toBeNull();
    expect(uploadProblem({ type: "image/png", size: 10 * 1024 * 1024 + 1 })).toBe("tooLarge");
    expect(uploadProblem({ type: "image/heic", size: 10 })).toBe("type");
  });

  it("format sizes for people", () => {
    expect(formatSize(300, "tr")).toBe("1 KB");
    expect(formatSize(2_621_440, "tr")).toBe("2,5 MB");
    expect(formatSize(2_621_440, "en")).toBe("2.5 MB");
  });
});
