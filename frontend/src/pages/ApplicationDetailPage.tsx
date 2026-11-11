import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import {
  useApplicationFile,
  useChecklist,
  useDeleteApplicationFile,
  useDocuments,
  useUpdateApplicationFile,
} from "../api/hooks";
import type { ApplicationFile, Language, Step } from "../api/types";
import { ChecklistView } from "../components/ChecklistView";
import { ReadinessRing } from "../components/ReadinessRing";
import { RequireLogin } from "../components/RequireLogin";
import { RouteArc } from "../components/RouteArc";
import { STEPS, StepTimeline } from "../components/StepTimeline";
import { daysUntil, formatDate } from "../components/format";
import { useCountUp } from "../hooks/useCountUp";
import { tripDays } from "../trip";

function Stat({ label, value, unit, tone }: { label: string; value: number; unit?: string; tone?: "amber" }) {
  const shown = useCountUp(value);
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-navy-muted">{label}</span>
      <span
        className={`text-3xl font-extrabold tracking-tighter tabular-nums ${
          tone === "amber" ? "text-amber" : "text-white"
        }`}
      >
        {shown}
        {unit && <span className="text-sm font-semibold tracking-normal text-navy-text"> {unit}</span>}
      </span>
    </div>
  );
}

function Detail({ file }: { file: ApplicationFile }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const update = useUpdateApplicationFile(file.id);
  const remove = useDeleteApplicationFile(file.id);
  const [confirming, setConfirming] = useState(false);
  const checklist = useChecklist(file.destination, file.profile, i18n.language as Language);
  const documents = useDocuments(file.id);

  const items = checklist.data?.items ?? [];
  const readyIds = new Set(documents.data?.map((document) => document.requirement_id));
  const ready = items.filter((item) => readyIds.has(item.id)).length;
  const next = items.find((item) => !readyIds.has(item.id));
  const percent = useCountUp(items.length ? Math.round((ready / items.length) * 100) : 0);
  const destination = t(`destination.${file.destination}`);
  const chip = "rounded-full border border-navy-line bg-navy-2 px-3 py-1 text-xs font-semibold text-white";

  return (
    <div className="flex flex-col gap-4">
      <section aria-label={t("detail.summary")} className="flex flex-wrap gap-4">
        <div
          className="va-rise va-card relative flex min-w-0 flex-[999_1_520px] flex-col gap-3.5 overflow-hidden rounded-[22px] bg-navy p-6 text-navy-text"
          style={{ animationDelay: "0.08s" }}
        >
          <div aria-hidden="true" className="va-dots absolute inset-0 opacity-60" />
          <div className="relative flex flex-col gap-1.5">
            <Link to="/applications" className="font-mono text-[11px] tracking-widest text-navy-muted uppercase">
              ← {t("applications.title")} · {t("detail.kind")}
            </Link>
            <h1 className="text-[34px] leading-tight font-extrabold tracking-tight text-white">
              {t("detail.title", { destination })}
            </h1>
            <div className="flex flex-wrap gap-2">
              <span className={chip}>{t(`profile.${file.profile}`)}</span>
              <span className={chip}>
                {t("applications.trip", {
                  start: formatDate(file.trip_start, i18n.language),
                  end: formatDate(file.trip_end, i18n.language),
                })}{" "}
                · {t("wizard.days", { count: tripDays(file.trip_start, file.trip_end) })}
              </span>
            </div>
          </div>

          <RouteArc from="TR" to={file.destination} label={t("detail.routeLabel", { destination })} />

          <div className="relative grid grid-cols-[repeat(auto-fit,minmax(130px,1fr))] gap-3">
            <Stat label={t("detail.daysLeft")} value={daysUntil(file.application_date)} unit={t("detail.days")} />
            <div className="flex flex-col gap-0.5">
              <span className="text-xs text-navy-muted">{t("detail.appointment")}</span>
              <span className="pt-2 text-lg font-bold text-white">
                {formatDate(file.application_date, i18n.language)}
              </span>
            </div>
            <Stat label={t("detail.rules")} value={checklist.data?.rules.length ?? 0} />
            <Stat label={t("detail.missing")} value={items.length - ready} tone="amber" />
          </div>
        </div>

        <div
          className="va-rise va-card flex flex-[1_1_280px] flex-col items-center justify-center gap-3.5 rounded-[22px] border border-line bg-white p-6"
          style={{ animationDelay: "0.18s" }}
        >
          <span className="self-start font-mono text-[11px] tracking-widest text-muted uppercase">
            {t("detail.readiness")}
          </span>
          <div className="relative size-44">
            <ReadinessRing
              total={items.length}
              ready={ready}
              label={t("detail.readinessLabel", { ready, total: items.length })}
            />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-[40px] font-extrabold tracking-tighter tabular-nums">%{percent}</span>
              <span className="text-xs text-muted">{t("detail.ofDocs", { ready, total: items.length })}</span>
            </div>
          </div>
          <p className="text-center text-[13px] text-muted">
            {next ? (
              <>
                {t("detail.next")} <strong className="text-ink">{next.document.title}</strong>
              </>
            ) : (
              items.length > 0 && t("detail.allReady")
            )}
          </p>
        </div>
      </section>

      <section
        aria-label={t("detail.steps")}
        className="va-rise flex flex-col gap-4 rounded-[18px] border border-line bg-white px-5 py-[18px]"
        style={{ animationDelay: "0.26s" }}
      >
        <StepTimeline file={file} />
        <label className="flex flex-wrap items-center gap-2 self-end text-sm font-medium">
          {t("detail.step")}
          <select
            className="select min-h-11 rounded-xl border border-line bg-white px-3"
            value={file.step}
            disabled={update.isPending}
            onChange={(event) => update.mutate({ step: event.target.value as Step })}
          >
            {STEPS.map((step) => (
              <option key={step} value={step}>
                {t(`applications.step.${step}`)}
              </option>
            ))}
          </select>
        </label>
        {update.error && (
          <p role="alert" className="rounded-xl bg-error-bg p-3 text-sm text-error">
            {update.error.message}
          </p>
        )}
      </section>

      {checklist.data && <ChecklistView checklist={checklist.data} readyIds={readyIds} />}
      {checklist.isError && (
        <p role="alert" className="rounded-xl bg-error-bg p-3 text-error">
          {t("checklist.error", { message: checklist.error.message })}
        </p>
      )}

      <section className="rounded-[18px] border border-error/30 bg-white p-5">
        <h2 className="font-bold">{t("detail.deleteTitle")}</h2>
        <p className="mt-1 text-sm text-muted">{t("detail.deleteText")}</p>
        {confirming ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() => remove.mutate(undefined, { onSuccess: () => navigate("/applications") })}
              className="va-btn min-h-11 rounded-xl bg-error px-4 font-semibold text-white disabled:opacity-60"
            >
              {t("detail.deleteConfirm")}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="min-h-11 rounded-xl border border-line px-4 font-semibold text-muted"
            >
              {t("detail.cancel")}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="mt-3 min-h-11 rounded-xl border border-error px-4 font-semibold text-error"
          >
            {t("detail.delete")}
          </button>
        )}
      </section>
    </div>
  );
}

function Loader({ id }: { id: string }) {
  const { t } = useTranslation();
  const file = useApplicationFile(id);
  if (file.isPending) return null;
  if (file.isError) return <p className="text-muted">{t("detail.notFound")}</p>;
  return <Detail file={file.data} />;
}

export function ApplicationDetailPage() {
  const { id = "" } = useParams();
  return <RequireLogin>{() => <Loader id={id} />}</RequireLogin>;
}
