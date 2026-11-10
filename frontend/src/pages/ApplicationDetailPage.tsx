import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import {
  useApplicationFile,
  useChecklist,
  useDeleteApplicationFile,
  useUpdateApplicationFile,
} from "../api/hooks";
import type { ApplicationFile, Language, Step } from "../api/types";
import { ChecklistView } from "../components/ChecklistView";
import { RequireLogin } from "../components/RequireLogin";
import { formatDate } from "../components/format";

const STEPS: Step[] = ["draft", "appointment", "documents", "submitted", "decided"];

function Detail({ file }: { file: ApplicationFile }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const update = useUpdateApplicationFile(file.id);
  const remove = useDeleteApplicationFile(file.id);
  const [confirming, setConfirming] = useState(false);
  const checklist = useChecklist(file.destination, file.profile, i18n.language as Language);

  return (
    <div className="space-y-6">
      <Link to="/applications" className="text-sm font-semibold text-brand">
        ← {t("applications.title")}
      </Link>
      <section className="rounded-xl border border-line bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">
              {t(`destination.${file.destination}`)} · {t(`profile.${file.profile}`)}
            </h1>
            <p className="mt-1 text-sm text-muted">
              {t("applications.trip", {
                start: formatDate(file.trip_start, i18n.language),
                end: formatDate(file.trip_end, i18n.language),
              })}{" "}
              · {t("detail.referenceDate", { date: formatDate(file.application_date, i18n.language) })}
            </p>
          </div>
          <label className="text-sm font-medium">
            {t("detail.step")}
            <select
              className="select mt-1 block min-h-11 rounded-lg border border-line bg-white px-3"
              value={file.step}
              disabled={update.isPending}
              onChange={(e) => update.mutate({ step: e.target.value as Step })}
            >
              {STEPS.map((step) => (
                <option key={step} value={step}>
                  {t(`applications.step.${step}`)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <ol className="mt-4 flex flex-wrap gap-2 text-xs" aria-label={t("detail.history")}>
          {file.events.map((event) => (
            <li key={`${event.step}-${event.occurred_at}`} className="rounded-full bg-ground px-2 py-1">
              {t(`applications.step.${event.step}`)} ·{" "}
              {new Date(event.occurred_at).toLocaleDateString(i18n.language === "tr" ? "tr-TR" : "en-GB")}
            </li>
          ))}
        </ol>
        {update.error && (
          <p role="alert" className="mt-3 rounded-lg bg-error-bg p-3 text-sm text-error">
            {update.error.message}
          </p>
        )}
      </section>

      {checklist.data && <ChecklistView checklist={checklist.data} />}
      {checklist.isError && (
        <p role="alert" className="rounded-lg bg-error-bg p-3 text-error">
          {t("checklist.error", { message: checklist.error.message })}
        </p>
      )}

      <section className="rounded-xl border border-error/30 bg-white p-5">
        <h2 className="font-semibold">{t("detail.deleteTitle")}</h2>
        <p className="mt-1 text-sm text-muted">{t("detail.deleteText")}</p>
        {confirming ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() => remove.mutate(undefined, { onSuccess: () => navigate("/applications") })}
              className="min-h-11 rounded-lg bg-error px-4 font-semibold text-white disabled:opacity-60"
            >
              {t("detail.deleteConfirm")}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="min-h-11 rounded-lg border border-line px-4 font-semibold text-muted"
            >
              {t("detail.cancel")}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="mt-3 min-h-11 rounded-lg border border-error px-4 font-semibold text-error"
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
