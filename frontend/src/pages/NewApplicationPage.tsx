import { type FormEvent, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useCreateApplicationFile } from "../api/hooks";
import type { Profile } from "../api/types";
import { IconCheck } from "../components/icons";
import { RequireLogin } from "../components/RequireLogin";
import { RouteArc } from "../components/RouteArc";
import { formatDate } from "../components/format";
import { MAX_TRIP_DAYS, tripDays, tripProblem } from "../trip";

const DESTINATIONS = ["NL", "NO"] as const;
const PROFILES: Profile[] = ["employed", "student"];
const STEPS = ["purpose", "dates", "review"] as const;

function Choice({
  name,
  checked,
  onChange,
  badge,
  children,
}: {
  name: string;
  checked: boolean;
  onChange: () => void;
  badge?: string;
  children: ReactNode;
}) {
  return (
    <label
      className={`va-btn flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border px-3.5 font-semibold has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-brand ${
        checked ? "border-brand bg-brand-soft text-ink" : "border-line bg-white text-muted"
      }`}
    >
      <input type="radio" name={name} checked={checked} onChange={onChange} className="sr-only" />
      {badge && (
        <span
          aria-hidden="true"
          className={`flex size-9 shrink-0 items-center justify-center rounded-[10px] font-mono text-[11px] font-semibold text-white ${
            checked ? "bg-brand" : "bg-navy"
          }`}
        >
          {badge}
        </span>
      )}
      <span>{children}</span>
      {checked && (
        <span aria-hidden="true" className="ml-auto text-brand">
          <IconCheck />
        </span>
      )}
    </label>
  );
}

function SummaryRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-navy-line pt-2.5">
      <dt className="text-xs text-navy-muted">{label}</dt>
      <dd className="text-right font-semibold text-white">{children}</dd>
    </div>
  );
}

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

  const destinationName = t(`destination.${destination}`);
  const tripText = problem
    ? "–"
    : t("applications.trip", {
        start: formatDate(tripStart, i18n.language),
        end: formatDate(tripEnd, i18n.language),
      });
  const appointmentText = applicationDate ? formatDate(applicationDate, i18n.language) : t("wizard.today");
  const field =
    "mt-1.5 block min-h-12 w-full rounded-xl border border-line bg-white px-3.5 transition-colors focus:border-brand";
  const legend = "mb-2 text-sm font-semibold";

  return (
    <div className="flex flex-wrap gap-4">
      <form
        onSubmit={next}
        className="va-rise flex min-w-0 flex-[999_1_460px] flex-col gap-6 rounded-[22px] border border-line bg-white p-6"
        style={{ animationDelay: "0.08s" }}
      >
        <div>
          <span className="font-mono text-[11px] tracking-widest text-muted uppercase">
            {t("detail.kind")}
          </span>
          <h1 className="mt-1 text-[28px] leading-tight font-extrabold tracking-tight">{t("wizard.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("wizard.lead")}</p>
        </div>

        <ol className="grid grid-cols-3 gap-2" aria-label={t("wizard.progress")}>
          {STEPS.map((name, index) => {
            const done = index < step;
            const active = index === step;
            return (
              <li
                key={name}
                aria-current={active ? "step" : undefined}
                className="flex flex-col gap-2"
              >
                <span
                  aria-hidden="true"
                  className={`h-1.5 rounded-full ${done || active ? "bg-brand" : "bg-line"}`}
                />
                <span className="flex items-center gap-2 text-[13px]">
                  <span
                    className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      done
                        ? "bg-brand text-white"
                        : active
                          ? "va-pulse border-2 border-brand text-brand"
                          : "border-2 border-[#c9d1df] text-muted"
                    }`}
                  >
                    {done ? <IconCheck /> : index + 1}
                  </span>
                  <span
                    className={active ? "font-extrabold text-brand" : done ? "font-bold" : "font-semibold text-muted"}
                  >
                    {t(`wizard.steps.${name}`)}
                  </span>
                </span>
              </li>
            );
          })}
        </ol>

        {step === 0 && (
          <div key="purpose" className="va-rise flex flex-col gap-5">
            <fieldset>
              <legend className={legend}>{t("home.destinationLabel")}</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {DESTINATIONS.map((code) => (
                  <Choice
                    key={code}
                    name="destination"
                    badge={code}
                    checked={destination === code}
                    onChange={() => setDestination(code)}
                  >
                    {t(`destination.${code}`)}
                  </Choice>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend className={legend}>{t("home.profileLabel")}</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {PROFILES.map((value) => (
                  <Choice
                    key={value}
                    name="profile"
                    checked={profile === value}
                    onChange={() => setProfile(value)}
                  >
                    {t(`profile.${value}`)}
                  </Choice>
                ))}
              </div>
            </fieldset>
            <p className="text-xs text-muted">{t("home.fromTurkiye")}</p>
          </div>
        )}

        {step === 1 && (
          <div key="dates" className="va-rise flex flex-col gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-semibold">
                {t("wizard.tripStart")}
                <input
                  className={field}
                  type="date"
                  required
                  value={tripStart}
                  onChange={(e) => setTripStart(e.target.value)}
                />
              </label>
              <label className="text-sm font-semibold">
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
            <label className="block text-sm font-semibold">
              {t("wizard.applicationDate")}
              <input
                className={field}
                type="date"
                value={applicationDate}
                onChange={(e) => setApplicationDate(e.target.value)}
              />
              <span className="mt-1 block text-xs font-normal text-muted">
                {t("wizard.applicationDateHint")}
              </span>
            </label>
            {showProblem && problem && (
              <p role="alert" className="rounded-xl bg-error-bg p-3 text-sm text-error">
                {t(`wizard.problem.${problem}`, { max: MAX_TRIP_DAYS })}
              </p>
            )}
          </div>
        )}

        {step === 2 && (
          <dl
            key="review"
            className="va-rise grid grid-cols-[auto_1fr] gap-x-5 gap-y-3 rounded-[14px] bg-brand-soft p-4 text-sm"
          >
            <dt className="text-muted">{t("home.destinationLabel")}</dt>
            <dd className="font-semibold">{destinationName}</dd>
            <dt className="text-muted">{t("home.profileLabel")}</dt>
            <dd className="font-semibold">{t(`profile.${profile}`)}</dd>
            <dt className="text-muted">{t("wizard.trip")}</dt>
            <dd className="font-semibold">
              {tripText} ({t("wizard.days", { count: tripDays(tripStart, tripEnd) })})
            </dd>
            <dt className="text-muted">{t("wizard.applicationDate")}</dt>
            <dd className="font-semibold">{appointmentText}</dd>
          </dl>
        )}

        {create.error && (
          <p role="alert" className="rounded-xl bg-error-bg p-3 text-sm text-error">
            {create.error.message}
          </p>
        )}

        <div className="mt-auto flex justify-between gap-3">
          <button
            type="button"
            onClick={() => setStep(step - 1)}
            disabled={step === 0}
            className="min-h-11 rounded-xl border border-line px-4 font-semibold text-muted disabled:invisible"
          >
            {t("wizard.back")}
          </button>
          <button
            type="submit"
            disabled={create.isPending}
            className="va-btn min-h-11 rounded-xl bg-brand px-5 font-bold text-white shadow-[0_8px_20px_rgb(36_80_230/0.3)] disabled:opacity-60"
          >
            {step < STEPS.length - 1 ? t("wizard.next") : t("wizard.create")}
          </button>
        </div>
      </form>

      <aside
        aria-label={t("wizard.summary")}
        className="va-rise relative flex flex-[1_1_300px] flex-col gap-3 overflow-hidden rounded-[22px] bg-navy p-6 text-sm text-navy-text"
        style={{ animationDelay: "0.18s" }}
      >
        <div aria-hidden="true" className="va-dots absolute inset-0 opacity-60" />
        <div className="relative">
          <span className="font-mono text-[11px] tracking-widest text-navy-muted uppercase">
            {t("wizard.summary")}
          </span>
          <p className="mt-1 text-2xl leading-tight font-extrabold tracking-tight text-white">
            {t("detail.title", { destination: destinationName })}
          </p>
        </div>
        <RouteArc
          key={destination}
          from="TR"
          to={destination}
          label={t("detail.routeLabel", { destination: destinationName })}
        />
        <dl className="relative flex flex-col gap-2.5">
          <SummaryRow label={t("home.profileLabel")}>{t(`profile.${profile}`)}</SummaryRow>
          <SummaryRow label={t("wizard.trip")}>{tripText}</SummaryRow>
          <SummaryRow label={t("wizard.stay")}>
            {problem ? (
              "–"
            ) : (
              <>
                <span className="tabular-nums">{tripDays(tripStart, tripEnd)}</span>
                <span className="text-navy-text"> {t("detail.days")}</span>
              </>
            )}
          </SummaryRow>
          <SummaryRow label={t("detail.appointment")}>{appointmentText}</SummaryRow>
        </dl>
      </aside>
    </div>
  );
}

export function NewApplicationPage() {
  return <RequireLogin>{() => <NewApplicationWizard />}</RequireLogin>;
}
