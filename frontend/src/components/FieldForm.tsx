import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { useDocumentFields, useSaveDocumentFields } from "../api/hooks";
import type { FieldInfo, FieldValue, Language, Money } from "../api/types";

const CURRENCIES = ["EUR", "TRY", "USD", "GBP"];
const DOCUMENT_LANGUAGES = ["tr", "en", "no", "nl", "de", "fr"];

/** What the inputs hold while editing: text for every type, so an empty input means "no value". */
type Draft = Record<string, string>;

function toDraft(fields: FieldInfo[]): Draft {
  const draft: Draft = {};
  for (const field of fields) {
    const { value } = field;
    if (value === null) {
      draft[field.id] = "";
      if (field.type === "money") draft[`${field.id}.currency`] = "EUR";
    } else if (typeof value === "object") {
      draft[field.id] = String(value.amount);
      draft[`${field.id}.currency`] = value.currency;
    } else {
      draft[field.id] = String(value);
    }
  }
  return draft;
}

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
  const set = (id: string, value: string) => {
    setDraft((current) => ({ ...current, [id]: value }));
    setSaved(false);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    save.mutate(toValues(fields, draft), { onSuccess: () => setSaved(true) });
  };
  const filled = fields.filter((field) => (draft[field.id] ?? "").trim() !== "").length;

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 rounded-xl bg-white p-3">
      <p className="text-xs text-muted">{t("fields.lead")}</p>
      {fields.map((field) => {
        const name = `${documentId}-${field.id}`;
        if (field.type === "bool") {
          return (
            <fieldset key={field.id} className="text-sm font-semibold">
              <legend>{field.title}</legend>
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

/** Entering and confirming the key fields of one uploaded document (FR-08). */
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
