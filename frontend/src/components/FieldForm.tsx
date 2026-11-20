import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  useDocumentFields,
  useExtractFields,
  useExtractionStatus,
  useSaveDocumentFields,
} from "../api/hooks";
import type { Extraction, FieldInfo, FieldValue, Language, Money } from "../api/types";

const CURRENCIES = ["EUR", "TRY", "USD", "GBP"];
const DOCUMENT_LANGUAGES = ["tr", "en", "no", "nl", "de", "fr"];

/** What the inputs hold while editing: text for every type, so an empty input means "no value". */
type Draft = Record<string, string>;

function draftOf(field: { id: string; type: string; value: FieldValue }): Draft {
  const { value } = field;
  if (value === null) {
    return field.type === "money" ? { [field.id]: "", [`${field.id}.currency`]: "EUR" } : { [field.id]: "" };
  }
  if (typeof value === "object") {
    return { [field.id]: String(value.amount), [`${field.id}.currency`]: value.currency };
  }
  return { [field.id]: String(value) };
}

function toDraft(fields: FieldInfo[]): Draft {
  return Object.assign({}, ...fields.map(draftOf)) as Draft;
}

/** The draft with the values a model read; fields it could not read keep what was entered. */
export function withExtracted(draft: Draft, extraction: Extraction): { draft: Draft; read: string[] } {
  const next = { ...draft };
  const read: string[] = [];
  for (const field of extraction.fields) {
    if (field.value === null) continue;
    Object.assign(next, draftOf(field));
    read.push(field.id);
  }
  return { draft: next, read };
}

/** Below this confidence the form asks the applicant to look at the value twice. */
const UNSURE = 0.7;

/** The stored form of each field (backend/app/rules/values.py); an empty input removes the value. */
export function toValues(fields: FieldInfo[], draft: Draft): Record<string, FieldValue> {
  const values: Record<string, FieldValue> = {};
  for (const field of fields) {
    const text = (draft[field.id] ?? "").trim();
    if (text === "") {
      values[field.id] = null;
    } else if (field.type === "int") {
      values[field.id] = Number.parseInt(text, 10);
    } else if (field.type === "bool") {
      values[field.id] = text === "true";
    } else if (field.type === "money") {
      const money: Money = {
        amount: Number(text.replace(",", ".")),
        currency: draft[`${field.id}.currency`] ?? "EUR",
      };
      values[field.id] = money;
    } else {
      values[field.id] = text;
    }
  }
  return values;
}

const input =
  "mt-1 block min-h-11 w-full rounded-xl border border-line bg-white px-3 text-sm transition-colors focus:border-brand";

function Inputs({
  applicationFileId,
  documentId,
  fields,
}: {
  applicationFileId: string;
  documentId: string;
  fields: FieldInfo[];
}) {
  const { t, i18n } = useTranslation();
  const save = useSaveDocumentFields(applicationFileId, documentId, i18n.language as Language);
  const [draft, setDraft] = useState<Draft>(() => toDraft(fields));
  const [saved, setSaved] = useState(false);
  const status = useExtractionStatus();
  const extract = useExtractFields(documentId, i18n.language as Language);
  // Fields filled by the model and not edited since, with the model's confidence.
  const [fromModel, setFromModel] = useState<Record<string, number>>({});
  const set = (id: string, value: string) => {
    setDraft((current) => ({ ...current, [id]: value }));
    setSaved(false);
    const fieldId = id.split(".")[0];
    setFromModel((current) => {
      if (!(fieldId in current)) return current;
      const next = { ...current };
      delete next[fieldId];
      return next;
    });
  };
  const readDocument = () => {
    extract.mutate(undefined, {
      onSuccess: (extraction) => {
        const result = withExtracted(draft, extraction);
        setDraft(result.draft);
        setSaved(false);
        const confidence = Object.fromEntries(extraction.fields.map((f) => [f.id, f.confidence]));
        setFromModel(Object.fromEntries(result.read.map((id) => [id, confidence[id] ?? 0])));
      },
    });
  };
  const modelNote = (id: string) =>
    id in fromModel ? (
      <span className="ml-1 rounded-md bg-brand-soft px-1.5 py-0.5 text-[11px] font-semibold text-ink">
        {t(fromModel[id] < UNSURE ? "extract.unsure" : "extract.read")}
      </span>
    ) : null;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    save.mutate(toValues(fields, draft), { onSuccess: () => setSaved(true) });
  };
  const filled = fields.filter((field) => (draft[field.id] ?? "").trim() !== "").length;

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 rounded-xl bg-white p-3">
      <p className="text-xs text-muted">{t("fields.lead")}</p>
      {status.data?.available && (
        <div className="flex flex-col gap-2 rounded-xl border border-line p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-muted">{t("extract.lead")}</span>
            <button
              type="button"
              onClick={readDocument}
              disabled={extract.isPending}
              className="va-btn min-h-11 rounded-xl border border-brand px-4 text-sm font-bold text-brand disabled:opacity-60"
            >
              {extract.isPending ? t("extract.reading") : t("extract.button")}
            </button>
          </div>
          {extract.data && (
            <p role="status" className="text-xs text-ink">
              {t("extract.done", { count: Object.keys(fromModel).length, model: extract.data.model })}
              {extract.data.invalid.length > 0 &&
                ` ${t("extract.invalid", { count: extract.data.invalid.length })}`}
            </p>
          )}
          {extract.error && (
            <p role="alert" className="text-xs text-error">
              {extract.error.message}
            </p>
          )}
        </div>
      )}
      {fields.map((field) => {
        const name = `${documentId}-${field.id}`;
        if (field.type === "bool") {
          return (
            <fieldset key={field.id} className="text-sm font-semibold">
              <legend>
                {field.title}
                {modelNote(field.id)}
              </legend>
              <div className="mt-1 flex gap-2">
                {(["true", "false"] as const).map((option) => (
                  <label
                    key={option}
                    className={`flex min-h-11 flex-1 cursor-pointer items-center justify-center rounded-xl border px-3 font-semibold has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-brand ${
                      draft[field.id] === option
                        ? "border-brand bg-brand-soft text-ink"
                        : "border-line bg-white text-muted"
                    }`}
                  >
                    <input
                      type="radio"
                      name={name}
                      checked={draft[field.id] === option}
                      onChange={() => set(field.id, option)}
                      className="sr-only"
                    />
                    {t(option === "true" ? "fields.yes" : "fields.no")}
                  </label>
                ))}
              </div>
            </fieldset>
          );
        }
        if (field.type === "money") {
          return (
            <div key={field.id} className="flex gap-2">
              <label className="flex-1 text-sm font-semibold">
                {field.title}
                {modelNote(field.id)}
                <input
                  className={input}
                  type="number"
                  min="0"
                  step="any"
                  inputMode="decimal"
                  value={draft[field.id] ?? ""}
                  onChange={(event) => set(field.id, event.target.value)}
                />
              </label>
              <label className="w-24 text-sm font-semibold">
                {t("fields.currency")}
                <select
                  className={`select ${input}`}
                  value={draft[`${field.id}.currency`] ?? "EUR"}
                  onChange={(event) => set(`${field.id}.currency`, event.target.value)}
                >
                  {CURRENCIES.map((code) => (
                    <option key={code}>{code}</option>
                  ))}
                </select>
              </label>
            </div>
          );
        }
        if (field.type === "language") {
          return (
            <label key={field.id} className="text-sm font-semibold">
              {field.title}
              {field.optional && <span className="font-normal text-muted"> ({t("fields.optional")})</span>}
              {modelNote(field.id)}
              <select
                className={`select ${input}`}
                value={draft[field.id] ?? ""}
                onChange={(event) => set(field.id, event.target.value)}
              >
                <option value="">{t("fields.choose")}</option>
                {DOCUMENT_LANGUAGES.map((code) => (
                  <option key={code} value={code}>
                    {t(`languageNames.${code}`, { defaultValue: code })}
                  </option>
                ))}
              </select>
            </label>
          );
        }
        return (
          <label key={field.id} className="text-sm font-semibold">
            {field.title}
            {modelNote(field.id)}
            <input
              className={input}
              type={field.type === "date" ? "date" : field.type === "int" ? "number" : "text"}
              {...(field.type === "int" ? { min: 0, step: 1, inputMode: "numeric" as const } : {})}
              {...(field.type === "text" ? { maxLength: 200 } : {})}
              value={draft[field.id] ?? ""}
              onChange={(event) => set(field.id, event.target.value)}
            />
          </label>
        );
      })}
      {save.error && (
        <p role="alert" className="rounded-xl bg-error-bg p-3 text-sm text-error">
          {save.error.message}
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-muted">
          {t("fields.progress", { filled, total: fields.length })}
        </span>
        <button
          type="submit"
          disabled={save.isPending}
          className="va-btn min-h-11 rounded-xl bg-brand px-4 text-sm font-bold text-white disabled:opacity-60"
        >
          {saved ? t("fields.saved") : t("fields.save")}
        </button>
      </div>
    </form>
  );
}

/** Entering and confirming the key fields of one uploaded document (FR-08); a model may propose
 * the values first (FR-13), but only what the applicant saves is checked. */
export function FieldForm({ applicationFileId, documentId }: { applicationFileId: string; documentId: string }) {
  const { t, i18n } = useTranslation();
  const fields = useDocumentFields(documentId, i18n.language as Language);
  if (fields.isPending) return <p className="text-sm text-muted">{t("fields.loading")}</p>;
  if (fields.isError) {
    return (
      <p role="alert" className="text-sm text-error">
        {fields.error.message}
      </p>
    );
  }
  return (
    <Inputs
      applicationFileId={applicationFileId}
      documentId={documentId}
      fields={fields.data.fields}
    />
  );
}
