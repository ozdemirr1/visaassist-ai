import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useApplicationFiles } from "../api/hooks";
import type { ApplicationFile } from "../api/types";
import { daysUntil, formatDate } from "../components/format";
import { IconPlus } from "../components/icons";
import { RequireLogin } from "../components/RequireLogin";
import { STEPS } from "../components/StepTimeline";
import { useCountUp } from "../hooks/useCountUp";

export function ApplicationCard({ file, index = 0 }: { file: ApplicationFile; index?: number }) {
  const { t, i18n } = useTranslation();
  const current = STEPS.indexOf(file.step);
  const days = daysUntil(file.application_date);

  return (
    <Link
      to={`/applications/${file.id}`}
      className="va-rise va-card flex flex-col gap-4 rounded-[18px] border border-line bg-white p-5"
      style={{ animationDelay: `${0.16 + index * 0.07}s` }}
    >
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-navy font-mono text-xs font-semibold text-white"
        >
          {file.destination}
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="text-lg leading-tight font-extrabold tracking-tight">
            {t("detail.title", { destination: t(`destination.${file.destination}`) })}
          </span>
          <span className="text-sm text-muted">{t(`profile.${file.profile}`)}</span>
        </span>
      </div>

      <p className="text-sm">
        {t("applications.trip", {
          start: formatDate(file.trip_start, i18n.language),
          end: formatDate(file.trip_end, i18n.language),
        })}
      </p>

      <div>
        <div aria-hidden="true" className="flex gap-1">
          {STEPS.map((step, position) => (
            <span
              key={step}
              className={`h-1.5 flex-1 rounded-full ${position <= current ? "bg-brand" : "bg-line"}`}
            />
          ))}
        </div>
        <div className="mt-2 flex items-baseline justify-between gap-2 text-xs">
          <span className="font-bold text-brand">{t(`applications.step.${file.step}`)}</span>
          <span className="font-mono text-muted">
            {t("applications.stepOf", { current: current + 1, total: STEPS.length })}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3 text-sm">
        <span className="text-muted">{t("detail.appointment")}</span>
        <span className="flex items-center gap-2 font-semibold">
          {formatDate(file.application_date, i18n.language)}
          {days > 0 && (
            <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-bold text-brand">
              {t("wizard.days", { count: days })}
            </span>
          )}
        </span>
      </div>
    </Link>
  );
}

function ApplicationList({ email }: { email: string }) {
  const { t } = useTranslation();
  const files = useApplicationFiles(true);
  const total = useCountUp(files.data?.length ?? 0);

  return (
    <div className="flex flex-col gap-4">
      <section
        className="va-rise relative overflow-hidden rounded-[22px] bg-navy p-6 text-navy-text"
        style={{ animationDelay: "0.08s" }}
      >
        <div aria-hidden="true" className="va-dots absolute inset-0 opacity-60" />
        <div className="relative flex flex-wrap items-end justify-between gap-5">
          <div className="min-w-0">
            <span className="font-mono text-[11px] tracking-widest text-navy-muted uppercase">
              {t("auth.loggedInAs", { email })}
            </span>
            <h1 className="mt-1 text-[34px] leading-tight font-extrabold tracking-tight text-white">
              {t("applications.title")}
            </h1>
            <p className="mt-1 max-w-xl">{t("applications.lead")}</p>
          </div>
          <div className="flex items-end gap-6">
            <div className="flex flex-col gap-0.5">
              <span className="text-xs text-navy-muted">{t("applications.total")}</span>
              <span className="text-3xl font-extrabold tracking-tighter text-white tabular-nums">{total}</span>
            </div>
            <Link
              to="/applications/new"
              className="va-btn inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 font-bold text-white shadow-[0_8px_20px_rgb(36_80_230/0.35)]"
            >
              <IconPlus />
              {t("applications.new")}
            </Link>
          </div>
        </div>
      </section>

      {files.isError && (
        <p role="alert" className="rounded-xl bg-error-bg p-3 text-error">
          {files.error.message}
        </p>
      )}

      {files.data?.length === 0 ? (
        <div
          className="va-rise flex flex-col items-center gap-3 rounded-[18px] border border-dashed border-[#c9d1df] bg-white p-10 text-center"
          style={{ animationDelay: "0.16s" }}
        >
          <p className="text-lg font-bold">{t("applications.empty")}</p>
          <p className="max-w-md text-sm text-muted">{t("applications.emptyLead")}</p>
          <Link
            to="/applications/new"
            className="va-btn mt-1 inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 font-bold text-white"
          >
            <IconPlus />
            {t("applications.new")}
          </Link>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {files.data?.map((file, index) => (
            <li key={file.id} className="flex flex-col">
              <ApplicationCard file={file} index={index} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ApplicationsPage() {
  return <RequireLogin>{(user) => <ApplicationList email={user.email} />}</RequireLogin>;
}
