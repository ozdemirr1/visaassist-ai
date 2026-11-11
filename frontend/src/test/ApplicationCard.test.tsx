import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { ApplicationFile } from "../api/types";
import i18n from "../i18n";
import { ApplicationCard } from "../pages/ApplicationsPage";

const file: ApplicationFile = {
  id: "f1",
  destination: "NO",
  visa: "schengen_c",
  purpose: "tourism",
  profile: "student",
  trip_start: "2027-04-10",
  trip_end: "2027-04-20",
  application_date: "2020-01-15",
  step: "documents",
  requirement_set_id: "set-1",
  created_at: "2026-11-11T10:00:00Z",
  events: [],
};

function renderCard(value: ApplicationFile) {
  return render(
    <MemoryRouter>
      <ApplicationCard file={value} />
    </MemoryRouter>,
  );
}

describe("application card", () => {
  it("links to the file and shows its step out of five", async () => {
    await i18n.changeLanguage("tr");
    renderCard(file);
    expect(screen.getByRole("link", { name: /Norveç başvurusu/ })).toHaveAttribute("href", "/applications/f1");
    expect(screen.getByText("Belgeler")).toBeInTheDocument();
    expect(screen.getByText("Adım 3/5")).toBeInTheDocument();
  });

  it("shows the days left only while the appointment is ahead", async () => {
    await i18n.changeLanguage("tr");
    const { unmount } = renderCard(file);
    expect(screen.queryByText(/gün$/)).not.toBeInTheDocument();
    unmount();
    renderCard({ ...file, application_date: "2099-01-15" });
    expect(screen.getByText(/gün$/)).toBeInTheDocument();
  });
});
