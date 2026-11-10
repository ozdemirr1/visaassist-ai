import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useChecklist } from "../api/hooks";
import type { Language, Profile } from "../api/types";
import { ChecklistView } from "../components/ChecklistView";

// The pilot destinations (ADR 0001); the API answers 404 for others.
const DESTINATIONS = ["NL", "NO"] as const;
const PROFILES: Profile[] = ["employed", "student"];

export function HomePage() {
  const { t, i18n } = useTranslation();
  const [destination, setDestination] = useState<string>("NL");
  const [profile, setProfile] = useState<Profile>("employed");
  const checklist = useChecklist(destination, profile, i18n.language as Language);

  const select = "select mt-1 block min-h-11 w-full rounded-lg border border-line bg-white px-3";
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold">{t("home.title")}</h1>
        <p className="mt-1 text-muted">{t("home.lead")}</p>
        <p className="mt-1 text-xs text-muted">{t("home.fromTurkiye")}</p>
      </section>

      <form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => event.preventDefault()}>
        <label className="text-sm font-medium">
          {t("home.destinationLabel")}
          <select
            className={select}
            value={destination}
            onChange={(event) => setDestination(event.target.value)}
          >
            {DESTINATIONS.map((code) => (
              <option key={code} value={code}>
                {t(`destination.${code}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          {t("home.profileLabel")}
          <select
            className={select}
            value={profile}
            onChange={(event) => setProfile(event.target.value as Profile)}
          >
            {PROFILES.map((value) => (
              <option key={value} value={value}>
                {t(`profile.${value}`)}
              </option>
            ))}
          </select>
        </label>
      </form>

      {checklist.isPending && <p className="text-muted">{t("checklist.loading")}</p>}
      {checklist.isError && (
        <p role="alert" className="rounded-lg bg-error-bg p-3 text-error">
          {t("checklist.error", { message: checklist.error.message })}
        </p>
      )}
      {checklist.data && <ChecklistView checklist={checklist.data} />}
    </div>
  );
}
