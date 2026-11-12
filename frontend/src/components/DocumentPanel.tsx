import { type ChangeEvent, type DragEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { API_BASE, ApiError } from "../api/client";
import { useDeleteDocument, useGiveConsent, useUploadDocument, useWithdrawConsent } from "../api/hooks";
import type { ChecklistItem, ConsentState, DocumentInfo } from "../api/types";
import { ACCEPTED_TYPES, MAX_UPLOAD_MB, formatSize, uploadProblem } from "../upload";
import { FieldForm } from "./FieldForm";
import { formatDate, formatShortDate } from "./format";
import { IconCheck, IconDownload, IconFile, IconLock, IconUpload } from "./icons";

const CONSENT_POINTS = ["purpose", "storage", "photos", "retention", "withdraw"] as const;
const SERVER_ERRORS: Record<number, string> = { 403: "consent", 413: "tooLarge", 415: "type" };

const card = "va-rise flex min-w-0 flex-col gap-3.5 rounded-[22px] border border-line bg-white p-5";
const kicker = "font-mono text-[10px] tracking-[0.12em] text-muted uppercase";
const quiet = "min-h-11 rounded-xl border border-line px-3 text-sm font-semibold text-muted";

/** The consent text; uploading is possible only after accepting it (ADR 0005). */
function ConsentCard({ version }: { version: string }) {
  const { t } = useTranslation();
  const give = useGiveConsent();
  return (
    <section aria-labelledby="consent-heading" className={card}>
      <span className="flex size-11 items-center justify-center rounded-2xl bg-brand-soft text-brand">
        <IconLock />
      </span>
      <div>
        <h2 id="consent-heading" className="text-lg font-extrabold tracking-tight">
          {t("consent.title")}
        </h2>
        <p className="mt-1 text-sm text-muted">{t("consent.intro")}</p>
      </div>
      <ul className="flex flex-col gap-2 text-sm">
        {CONSENT_POINTS.map((point) => (
          <li key={point} className="flex gap-2.5">
            <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-brand-soft text-brand">
              <IconCheck />
            </span>
            {t(`consent.points.${point}`)}
          </li>
        ))}
      </ul>
      {give.error && (
        <p role="alert" className="rounded-xl bg-error-bg p-3 text-sm text-error">
          {give.error.message}
        </p>
      )}
      <button
        type="button"
        disabled={give.isPending}
        onClick={() => give.mutate()}
        className="va-btn min-h-11 rounded-xl bg-brand px-4 font-bold text-white disabled:opacity-60"
      >
        {t("consent.accept")}
      </button>
      <span className="font-mono text-[11px] text-muted">{t("consent.version", { version })}</span>
    </section>
  );
}

function DocumentRow({ applicationFileId, document }: { applicationFileId: string; document: DocumentInfo }) {
  const { t, i18n } = useTranslation();
  const remove = useDeleteDocument(applicationFileId);
  const [confirming, setConfirming] = useState(false);
  const [entering, setEntering] = useState(false);
  return (
    <li className="flex flex-col gap-2 rounded-[14px] bg-ground p-3">
      <div className="flex items-center gap-2.5">
        <span className="text-brand">
          <IconFile />
        </span>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-bold">{document.original_name}</span>
          <span className="font-mono text-[11px] text-muted">
            {ACCEPTED_TYPES[document.mime_type] ?? document.mime_type} ·{" "}
            {formatSize(document.size_bytes, i18n.language)} ·{" "}
            {formatShortDate(document.uploaded_at, i18n.language)}
          </span>
        </span>
      </div>
      {remove.error && (
        <p role="alert" className="text-sm text-error">
          {remove.error.message}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {confirming ? (
          <>
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() => remove.mutate(document.id)}
              className="va-btn min-h-11 rounded-xl bg-error px-3 text-sm font-bold text-white disabled:opacity-60"
            >
              {t("upload.deleteConfirm")}
            </button>
            <button type="button" onClick={() => setConfirming(false)} className={`${quiet} bg-white`}>
              {t("detail.cancel")}
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              aria-expanded={entering}
              onClick={() => setEntering(!entering)}
              className="va-btn min-h-11 rounded-xl bg-brand px-3 text-sm font-bold text-white"
            >
              {t(entering ? "fields.close" : "fields.open")}
            </button>
            <a
              href={`${API_BASE}/documents/${document.id}/content`}
              aria-label={`${t("upload.download")}: ${document.original_name}`}
              className="va-btn flex min-h-11 items-center gap-1.5 rounded-xl border border-line bg-white px-3 text-sm font-bold text-brand"
            >
              <IconDownload />
              {t("upload.download")}
            </a>
            <button
              type="button"
              aria-label={`${t("upload.delete")}: ${document.original_name}`}
              onClick={() => setConfirming(true)}
              className="min-h-11 rounded-xl border border-error/40 bg-white px-3 text-sm font-semibold text-error"
            >
              {t("upload.delete")}
            </button>
          </>
        )}
      </div>
      {entering && <FieldForm applicationFileId={applicationFileId} documentId={document.id} />}
    </li>
  );
}

interface Props {
  applicationFileId: string;
  item: ChecklistItem;
  /** The documents already uploaded for this checklist item. */
  documents: DocumentInfo[];
  consent: ConsentState | undefined;
}

/** Upload, download and delete the documents of one checklist item (FR-07, FR-11). */
export function DocumentPanel({ applicationFileId, item, documents, consent }: Props) {
  const { t, i18n } = useTranslation();
  const upload = useUploadDocument(applicationFileId);
  const withdraw = useWithdrawConsent();
  const [problem, setProblem] = useState<string | null>(null);
  const [over, setOver] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);

  if (!consent) return null;
  if (!consent.given) return <ConsentCard version={consent.version} />;

  const send = (file: File | undefined) => {
    if (!file || upload.isPending) return;
    const found = uploadProblem(file);
    setProblem(found ? t(`upload.error.${found}`, { max: MAX_UPLOAD_MB }) : null);
    if (found) return;
    upload.mutate(
      { requirementId: item.id, file },
      {
        onError: (error) => {
          const known = error instanceof ApiError ? SERVER_ERRORS[error.status] : undefined;
          setProblem(known ? t(`upload.error.${known}`, { max: MAX_UPLOAD_MB }) : error.message);
        },
      },
    );
  };
  const choose = (event: ChangeEvent<HTMLInputElement>) => {
    send(event.target.files?.[0]);
    event.target.value = ""; // the same file can be chosen again
  };
  const drop = (event: DragEvent) => {
    event.preventDefault();
    setOver(false);
    send(event.dataTransfer.files[0]);
  };

  return (
    <section aria-labelledby="upload-heading" className={card} style={{ animationDelay: "0.1s" }}>
      <h2 id="upload-heading" className={kicker}>
        {t("upload.kicker")}
      </h2>

      <label
        onDragOver={(event) => {
          event.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
        className={`relative flex min-h-36 cursor-pointer flex-col items-center justify-center gap-1.5 overflow-hidden rounded-[14px] border-2 border-dashed p-4 text-center transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-brand ${
          over ? "border-brand bg-brand-soft" : "border-[#c9d1df] bg-ground hover:border-brand"
        }`}
      >
        {upload.isPending && (
          <span
            aria-hidden="true"
            className="va-scan absolute inset-x-0 top-0 h-10 bg-linear-to-b from-transparent via-brand/15 to-transparent"
          />
        )}
        <input
          type="file"
          accept={Object.keys(ACCEPTED_TYPES).join(",")}
          disabled={upload.isPending}
          onChange={choose}
          className="sr-only"
        />
        <span className="relative flex size-11 items-center justify-center rounded-2xl bg-white text-brand">
          <IconUpload />
        </span>
        <span className="relative text-sm font-bold">
          {upload.isPending ? t("upload.working") : t("upload.drop")}
        </span>
        <span className="relative text-xs text-muted">{t("upload.hint", { max: MAX_UPLOAD_MB })}</span>
      </label>

      {problem && (
        <p role="alert" className="rounded-xl bg-error-bg p-3 text-sm text-error">
          {problem}
        </p>
      )}

      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-bold">{t("upload.uploaded")}</h3>
        {documents.length === 0 ? (
          <p className="text-sm text-muted">{t("upload.none")}</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {documents.map((document) => (
              <DocumentRow key={document.id} applicationFileId={applicationFileId} document={document} />
            ))}
          </ul>
        )}
        {documents.length > 0 && (
          <p className="text-xs text-muted">
            {t("upload.retention", {
              date: formatDate(documents[0].delete_after.slice(0, 10), i18n.language),
            })}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2 border-t border-line pt-3">
        {withdrawing ? (
          <>
            <p className="text-sm text-muted">{t("consent.withdrawWarning")}</p>
            {withdraw.error && (
              <p role="alert" className="text-sm text-error">
                {withdraw.error.message}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={withdraw.isPending}
                onClick={() => withdraw.mutate()}
                className="va-btn min-h-11 rounded-xl bg-error px-3 text-sm font-bold text-white disabled:opacity-60"
              >
                {t("consent.withdrawConfirm")}
              </button>
              <button type="button" onClick={() => setWithdrawing(false)} className={quiet}>
                {t("detail.cancel")}
              </button>
            </div>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setWithdrawing(true)}
            className="min-h-11 self-start text-xs font-semibold text-muted underline"
          >
            {t("consent.withdraw")}
          </button>
        )}
      </div>
    </section>
  );
}
