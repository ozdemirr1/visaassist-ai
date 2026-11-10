import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import i18n from "../i18n";
import { NewApplicationWizard } from "../pages/NewApplicationPage";

function renderWizard() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <NewApplicationWizard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("new application wizard", () => {
  it("stops at the dates step when the return is before the departure", async () => {
    await i18n.changeLanguage("tr");
    const { container } = renderWizard();
    fireEvent.click(screen.getByRole("button", { name: "İleri" }));
    const [start, end] = container.querySelectorAll<HTMLInputElement>('input[type="date"]');
    fireEvent.change(start, { target: { value: "2027-04-20" } });
    fireEvent.change(end, { target: { value: "2027-04-10" } });
    fireEvent.submit(container.querySelector("form")!);
    expect(screen.getByRole("alert")).toHaveTextContent("Dönüş tarihi gidiş tarihinden önce olamaz.");
  });

  it("sends the chosen destination, profile and dates", async () => {
    await i18n.changeLanguage("tr");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "f1", events: [] }), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { container } = renderWizard();
    const [destination, profile] = container.querySelectorAll("select");
    fireEvent.change(destination, { target: { value: "NO" } });
    fireEvent.change(profile, { target: { value: "student" } });
    fireEvent.click(screen.getByRole("button", { name: "İleri" }));
    const [start, end] = container.querySelectorAll<HTMLInputElement>('input[type="date"]');
    fireEvent.change(start, { target: { value: "2027-04-10" } });
    fireEvent.change(end, { target: { value: "2027-04-20" } });
    fireEvent.click(screen.getByRole("button", { name: "İleri" }));
    expect(screen.getByText(/11 gün/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Başvuru dosyasını oluştur" }));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/applications");
    expect(JSON.parse(init.body)).toEqual({
      destination: "NO",
      profile: "student",
      trip_start: "2027-04-10",
      trip_end: "2027-04-20",
    });
  });
});
