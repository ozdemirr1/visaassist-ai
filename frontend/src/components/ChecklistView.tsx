import { useTranslation } from "react-i18next";

import type { Checklist, Citation } from "../api/types";

function SourceTag({ source }: { source: Citation }) {
  const { t } = useTranslation();
  return (
    <details className="mt-2 text-sm">
      <summary className="cursor-pointer font-mono text-xs text-brand">
        {t("checklist.source")}: {source.section}
      </summary>
      <div className="mt-2 rounded-lg bg-ground p-3">
        {/* Official passages stay in their original language (NFR-10). */}
        <blockquote lang="en" className="border-l-2 border-brand pl-3 italic text-ink">
          {source.passage}
        </blockquote>
        {source.basis === "derived" && (
          <p className="mt-1 text-xs text-muted">{t("checklist.derived")}</p>
        )}
        <p className="mt-2 text-xs text-muted">
          {source.title} · {source.publisher}
        </p>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-block text-xs font-semibold text-brand underline"
        >
          {t("checklist.openSource")}
        </a>
      </div>
    </details>
  );
}

export function ChecklistView({ checklist }: { checklist: Checklist }) {
  const { t } = useTranslation();
  const languages = checklist.translation.languages
    .map((code) => t(`languageNames.${code}`, { defaultValue: code }))
    .join(" / ");

  return (
    <div className="space-y-6">
      {checklist.translation.required && (
        <p role="note" className="rounded-lg bg-warning-bg p-3 text-sm text-warning">
          {t("checklist.translationRequired", { languages })}
        </p>
      )}

      <section aria-labelledby="documents-heading">
        <h2 id="documents-heading" className="mb-3 text-lg font-semibold">
          {t("checklist.documents", { count: checklist.items.length })}
        </h2>
        <ul className="space-y-2">
          {checklist.items.map((item) => (
            <li key={item.id} className="rounded-xl border border-line bg-white p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium">{item.document.title}</span>
                <span className="text-xs text-muted">
                  {t(`checklist.submitAs.${item.submit_as}`, { defaultValue: item.submit_as })} ·{" "}
                  {t(`checklist.layer.${item.layer}`)}
                </span>
              </div>
              {item.note && <p className="mt-1 text-sm text-muted">{item.note}</p>}
              <SourceTag source={item.source} />
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="rules-heading">
        <h2 id="rules-heading" className="mb-3 text-lg font-semibold">
          {t("checklist.rules", { count: checklist.rules.length })}
        </h2>
        <ul className="space-y-2">
          {checklist.rules.map((rule) => (
            <li key={rule.id} className="rounded-xl border border-line bg-white p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span>{rule.title}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                    rule.severity === "error" ? "bg-error-bg text-error" : "bg-warning-bg text-warning"
                  }`}
                >
                  {t(`checklist.severity.${rule.severity}`)}
                </span>
              </div>
              <SourceTag source={rule.source} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
