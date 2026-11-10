import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useCreateApplicationFile } from "../api/hooks";
import type { Profile } from "../api/types";
import { RequireLogin } from "../components/RequireLogin";
import { formatDate } from "../components/format";
import { MAX_TRIP_DAYS, tripDays, tripProblem } from "../trip";

const DESTINATIONS = ["NL", "NO"] as const;
const PROFILES: Profile[] = ["employed", "student"];
const STEPS = ["purpose", "dates", "review"] as const;

export function NewApplicationWizard() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const create = useCreateApplicationFile();
  const [step, setStep] = useState(0);
  const [destination, setDestination] = useState<string>("NL");
  const [profile, setProfile] = useState<Profile>("employed");
  const [tripStart, setTripStart] = useState("");
  const [tripEnd, setTripEnd] = useState("");
  const [applicationDate, setApplicationDate] = useState("");
  const [showProblem, setShowProblem] = useState(false);

  const problem = tripProblem(tripStart, tripEnd);
  const next = (event: FormEvent) => {
    event.preventDefault();
    if (step === 1 && problem) {
      setShowProblem(true);
      return;
    }
    if (step < STEPS.length - 1) {
      setStep(step + 1);
      return;
    }
    create.mutate(
      {
        destination,
        profile,
        trip_start: tripStart,
        trip_end: tripEnd,
        ...(applicationDate ? { application_date: applicationDate } : {}),
      },
      { onSuccess: (file) => navigate(`/applications/${file.id}`) },
    );
  };

  const field = "mt-1 block min-h-11 w-full rounded-lg border border-line bg-white px-3";
  return (
    <form onSubmit={next} className="mx-auto max-w-xl space-y-5 rounded-xl bg-white p-6 shadow-sm">
      <div>
        <h1 className="text-xl font-bold">{t("wizard.title")}</h1>
        <ol className="mt-3 flex gap-2 text-xs" aria-label={t("wizard.progress")}>
          {STEPS.map((name, index) => (
            <li
              key={name}
              aria-current={index === step ? "step" : undefined}
              className={`flex-1 rounded-full px-2 py-1 text-center font-semibold ${
                index === step ? "bg-brand text-white" : index < step ? "bg-ok-bg text-ok" : "bg-ground text-muted"
              }`}
            >
              {index + 1}. {t(`wizard.steps.${name}`)}
            </li>
          ))}
        </ol>
      </div>

      {step === 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium">
            {t("home.destinationLabel")}
            <select className={`select ${field}`} value={destination} onChange={(e) => setDestination(e.target.value)}>
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
              className={`select ${field}`}
              value={profile}
              onChange={(e) => setProfile(e.target.value as Profile)}
            >
              {PROFILES.map((value) => (
                <option key={value} value={value}>
                  {t(`profile.${value}`)}
                </option>
              ))}
            </select>
          </label>
          <p className="text-xs text-muted sm:col-span-2">{t("home.fromTurkiye")}</p>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium">
              {t("wizard.tripStart")}
              <input className={field} type="date" required value={tripStart} onChange={(e) => setTripStart(e.target.value)} />
            </label>
            <label className="text-sm font-medium">
              {t("wizard.tripEnd")}
              <input
                className={field}
                type="date"
                required
                min={tripStart || undefined}
                value={tripEnd}
                onChange={(e) => setTripEnd(e.target.value)}
              />
            </label>
          </div>
          <label className="block text-sm font-medium">
            {t("wizard.applicationDate")}
            <input
              className={field}
              type="date"
              value={applicationDate}
              onChange={(e) => setApplicationDate(e.target.value)}
            />
            <span className="text-xs text-muted">{t("wizard.applicationDateHint")}</span>
          </label>
          {showProblem && problem && (
            <p role="alert" className="rounded-lg bg-error-bg p-3 text-sm text-error">
              {t(`wizard.problem.${problem}`, { max: MAX_TRIP_DAYS })}
            </p>
          )}
        </div>
      )}

      {step === 2 && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-muted">{t("home.destinationLabel")}</dt>
          <dd className="font-medium">{t(`destination.${destination}`)}</dd>
          <dt className="text-muted">{t("home.profileLabel")}</dt>
          <dd className="font-medium">{t(`profile.${profile}`)}</dd>
          <dt className="text-muted">{t("wizard.trip")}</dt>
          <dd className="font-medium">
            {t("applications.trip", {
              start: formatDate(tripStart, i18n.language),
              end: formatDate(tripEnd, i18n.language),
            })}{" "}
            ({t("wizard.days", { count: tripDays(tripStart, tripEnd) })})
          </dd>
          <dt className="text-muted">{t("wizard.applicationDate")}</dt>
          <dd className="font-medium">
            {applicationDate ? formatDate(applicationDate, i18n.language) : t("wizard.today")}
          </dd>
        </dl>
      )}

      {create.error && (
        <p role="alert" className="rounded-lg bg-error-bg p-3 text-sm text-error">
          {create.error.message}
        </p>
      )}

      <div className="flex justify-between gap-3">
        <button
          type="button"
          onClick={() => setStep(step - 1)}
          disabled={step === 0}
          className="min-h-11 rounded-lg border border-line px-4 font-semibold text-muted disabled:invisible"
        >
          {t("wizard.back")}
        </button>
        <button
          type="submit"
          disabled={create.isPending}
          className="min-h-11 rounded-lg bg-brand px-5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
        >
          {step < STEPS.length - 1 ? t("wizard.next") : t("wizard.create")}
        </button>
      </div>
    </form>
  );
}

export function NewApplicationPage() {
  return <RequireLogin>{() => <NewApplicationWizard />}</RequireLogin>;
}
