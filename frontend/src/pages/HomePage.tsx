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

  const select = "select mt-1 block min-h-11 w-full rounded-xl border border-line bg-white px-3";
  return (
    <div className="flex flex-col gap-4">
      <section
        className="va-rise va-card relative overflow-hidden rounded-[22px] bg-navy p-6 text-navy-text"
        style={{ animationDelay: "0.08s" }}
      >
        <div aria-hidden="true" className="va-dots absolute inset-0 opacity-60" />
        <div className="relative flex flex-col gap-4">
          <div>
            <span className="font-mono text-[11px] tracking-widest text-navy-muted uppercase">
              {t("home.fromTurkiye")}
            </span>
            <h1 className="mt-1 text-[34px] leading-tight font-extrabold tracking-tight text-white">
              {t("home.title")}
            </h1>
            <p className="mt-1 max-w-2xl">{t("home.lead")}</p>
          </div>
          <form
            className="grid gap-4 text-white sm:grid-cols-2"
            onSubmit={(event) => event.preventDefault()}
          >
            <label className="text-sm font-medium">
              {t("home.destinationLabel")}
              <select
                className={`${select} text-ink`}
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
                className={`${select} text-ink`}
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
        </div>
      </section>

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
