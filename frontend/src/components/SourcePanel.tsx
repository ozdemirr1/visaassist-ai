import { useTranslation } from "react-i18next";

import type { Citation } from "../api/types";

export interface SourceEntry {
  id: string;
  title: string;
  /** Short line above the title: the layer of a document, or "rule". */
  kicker: string;
  source: Citation;
}

/** The official passage behind the selected checklist item or rule (NFR-03). */
export function SourcePanel({ entry }: { entry: SourceEntry }) {
  const { t } = useTranslation();
  const { source } = entry;
  return (
    <aside
      aria-label={t("checklist.sourceOf")}
      className="va-rise flex min-w-0 flex-col gap-3.5 rounded-[22px] border border-line bg-white p-5"
      style={{ animationDelay: "0.42s" }}
    >
      <span className="font-mono text-[10px] tracking-[0.12em] text-muted uppercase">{entry.kicker}</span>
      <h2 className="text-xl font-extrabold tracking-tight">{entry.title}</h2>
      <div className="relative flex flex-col gap-2.5 overflow-hidden rounded-[14px] bg-ground p-4">
        <div
          aria-hidden="true"
          className="va-scan absolute inset-x-0 top-0 h-10 bg-linear-to-b from-transparent via-brand/8 to-transparent"
        />
        <span className="relative font-mono text-[11px] font-medium text-brand">
          {t("checklist.source")} · {source.section}
        </span>
        {/* Official passages stay in their original language (NFR-10). */}
        <blockquote lang="en" className="relative border-l-[3px] border-brand pl-3 text-[15px] italic">
          {source.passage}
        </blockquote>
        {source.basis === "derived" && (
          <span className="relative text-xs text-muted">{t("checklist.derived")}</span>
        )}
        <span className="relative text-xs text-muted">
          {source.title} · {source.publisher}
        </span>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="relative text-[13px] font-bold text-brand underline"
        >
          {t("checklist.openSource")}
        </a>
      </div>
    </aside>
  );
}
