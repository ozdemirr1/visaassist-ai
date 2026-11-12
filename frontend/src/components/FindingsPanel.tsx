import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";

import type { CheckIssue, RuleResult } from "../api/types";
import { formatDate } from "./format";

const STATUS_STYLE = {
  passed: "bg-ok-bg text-ok",
  failed: "bg-error-bg text-error",
  incomplete: "bg-warning-bg text-warning",
  skipped: "bg-ground text-muted",
} as const;

/** A value of an issue as text: dates and months in the interface language, money with its currency. */
export function issueValue(value: unknown, language: string, t: TFunction): string {
  const locale = language === "tr" ? "tr-TR" : "en-GB";
  if (typeof value === "string") {
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return formatDate(value, language);
    if (/^\d{4}-\d{2}$/.test(value)) {
      return new Date(`${value}-01T00:00:00`).toLocaleDateString(locale, { month: "long", year: "numeric" });
    }
    if (/^[a-z]{2}$/.test(value)) return t(`languageNames.${value}`, { defaultValue: value });
    return value;
  }
  if (typeof value === "number") return value.toLocaleString(locale);
  if (typeof value === "boolean") return t(value ? "fields.yes" : "fields.no");
  if (Array.isArray(value)) return value.map((entry) => issueValue(entry, language, t)).join(" / ");
  if (value && typeof value === "object" && "amount" in value && "currency" in value) {
    const money = value as { amount: number; currency: string };
    return `${money.amount.toLocaleString(locale)} ${money.currency}`;
  }
  return "";
}

export function issueText(issue: CheckIssue, language: string, t: TFunction): string {
  return t(`check.issue.${issue.code}`, {
    defaultValue: issue.code,
    document: issue.document_title ?? issue.document_type ?? "",
    field: issue.field_title ?? issue.field ?? "",
    value: issueValue(issue.value, language, t),
    expected: issueValue(issue.expected, language, t),
  });
}

/** What the check found for one rule: its state and, if it did not pass, why (FR-10). */
export function FindingsPanel({ result }: { result: RuleResult }) {
  const { t, i18n } = useTranslation();
  return (
    <section
      aria-labelledby="findings-heading"
      className="va-rise flex min-w-0 flex-col gap-3 rounded-[22px] border border-line bg-white p-5"
      style={{ animationDelay: "0.1s" }}
    >
      <div className="flex items-center justify-between gap-3">
        <h2 id="findings-heading" className="font-mono text-[10px] tracking-[0.12em] text-muted uppercase">
          {t("check.kicker")}
        </h2>
        <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${STATUS_STYLE[result.status]}`}>
          {t(`check.status.${result.status}`)}
        </span>
      </div>
      <p className="text-sm text-muted">{t(`check.explain.${result.status}`)}</p>
      {result.issues.length > 0 && (
        <ul className="flex flex-col gap-2">
          {result.issues.map((issue, index) => (
            <li
              key={`${issue.code}-${issue.document_id}-${issue.field}-${index}`}
              className={`rounded-[14px] p-3 text-sm ${
                result.status === "failed" ? "bg-error-bg text-error" : "bg-warning-bg text-warning"
              }`}
            >
              {issueText(issue, i18n.language, t)}
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-muted">{t("check.disclaimer")}</p>
    </section>
  );
}
