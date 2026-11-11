import { type ReactNode, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Checklist, ChecklistItem } from "../api/types";
import { IconSearch } from "./icons";
import { type SourceEntry, SourcePanel } from "./SourcePanel";

type Filter = "all" | "missing" | "ready";

interface Props {
  checklist: Checklist;
  /** Checklist items that have an uploaded document. Without it, no status is shown. */
  readyIds?: ReadonlySet<string>;
  /** Shown under the source of the selected document (the upload panel of an application). */
  itemPanel?: (item: ChecklistItem) => ReactNode;
}

/** Documents as a table, the rules below, and the official source of the selected entry. */
export function ChecklistView({ checklist, readyIds, itemPanel }: Props) {
  const { t, i18n } = useTranslation();
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const side = useRef<HTMLDivElement>(null);
  const withStatus = readyIds !== undefined;
  // On a narrow screen the side column is below the lists: bring it into view on selection.
  const select = (id: string) => {
    setSelectedId(id);
    side.current?.scrollIntoView?.({ block: "nearest" });
  };
  const isReady = (id: string) => readyIds?.has(id) ?? false;

  const languages = checklist.translation.languages
    .map((code) => t(`languageNames.${code}`, { defaultValue: code }))
    .join(" / ");

  const entries = useMemo(() => {
    const map = new Map<string, SourceEntry>();
    for (const item of checklist.items) {
      map.set(item.id, {
        id: item.id,
        title: item.document.title,
        kicker: t(`checklist.layer.${item.layer}`),
        source: item.source,
      });
    }
    for (const rule of checklist.rules) {
      map.set(rule.id, {
        id: rule.id,
        title: rule.title,
        kicker: t("checklist.ruleLayer"),
        source: rule.source,
      });
    }
    return map;
  }, [checklist, t]);

  const readyCount = checklist.items.filter((i) => isReady(i.id)).length;
  const needle = query.trim().toLocaleLowerCase(i18n.language);
  const rows = checklist.items.filter((item) => {
    const ready = isReady(item.id);
    if (filter === "ready" && !ready) return false;
    if (filter === "missing" && ready) return false;
    return !needle || item.document.title.toLocaleLowerCase(i18n.language).includes(needle);
  });

  const firstMissing = withStatus ? checklist.items.find((i) => !isReady(i.id)) : undefined;
  const selected =
    (selectedId && entries.get(selectedId)) ||
    entries.get((firstMissing ?? checklist.items[0])?.id ?? "") ||
    null;

  const selectedItem = checklist.items.find((item) => item.id === selected?.id);

  const columns = withStatus
    ? "grid-cols-[minmax(0,2.2fr)_minmax(0,1.7fr)_150px_84px]"
    : "grid-cols-[minmax(0,2.2fr)_minmax(0,1.7fr)_150px]";
  const filters: { id: Filter; count: number }[] = [
    { id: "all", count: checklist.items.length },
    { id: "missing", count: checklist.items.length - readyCount },
    { id: "ready", count: readyCount },
  ];
  const rowClass = (id: string) =>
    `va-row va-rise w-full cursor-pointer rounded-xl border-[1.5px] text-left ${
      selected?.id === id ? "border-brand bg-brand-soft" : "border-transparent hover:bg-ground"
    }`;

  return (
    <div className="flex flex-col gap-4">
      {checklist.translation.required && (
        <p role="note" className="va-rise rounded-[14px] bg-warning-bg p-3 text-sm font-medium text-warning">
          {t("checklist.translationRequired", { languages })}
        </p>
      )}

      <div className="flex flex-wrap items-start gap-4">
        <div className="flex min-w-0 flex-[999_1_520px] flex-col gap-4">
          <section
            aria-labelledby="documents-heading"
            className="va-rise flex flex-col gap-3.5 rounded-[22px] border border-line bg-white p-5"
            style={{ animationDelay: "0.34s" }}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 id="documents-heading" className="text-lg font-extrabold tracking-tight">
                {t("checklist.documents", { count: checklist.items.length })}
              </h2>
              <div className="flex flex-wrap items-center gap-2">
                <label className="relative flex items-center text-muted">
                  <span className="sr-only">{t("checklist.search")}</span>
                  <span className="absolute left-3">
                    <IconSearch />
                  </span>
                  <input
                    type="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={t("checklist.search")}
                    className="min-h-11 w-44 rounded-xl border border-line bg-white pr-3 pl-9 text-sm text-ink placeholder:text-muted"
                  />
                </label>
                {withStatus && (
                  <div
                    role="group"
                    aria-label={t("checklist.filterLabel")}
                    className="flex rounded-xl border border-line bg-ground p-[3px]"
                  >
                    {filters.map(({ id, count }) => (
                      <button
                        key={id}
                        type="button"
                        aria-pressed={filter === id}
                        onClick={() => setFilter(id)}
                        className={`min-h-[38px] rounded-lg px-3.5 text-xs font-bold transition-colors ${
                          filter === id ? "bg-navy text-white" : "text-muted"
                        }`}
                      >
                        {t(`checklist.filter.${id}`)} <span className="font-mono font-medium">{count}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="overflow-x-auto">
              <div className="flex min-w-[600px] flex-col gap-0.5">
                <div
                  aria-hidden="true"
                  className={`grid ${columns} gap-3 border-b border-line px-3.5 pb-2 font-mono text-[10px] tracking-widest text-muted uppercase`}
                >
                  <span>{t("checklist.columns.document")}</span>
                  <span>{t("checklist.columns.source")}</span>
                  <span>{t("checklist.columns.submit")}</span>
                  {withStatus && <span className="text-right">{t("checklist.columns.status")}</span>}
                </div>
                {rows.map((item, index) => {
                  const ready = isReady(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      aria-pressed={selected?.id === item.id}
                      onClick={() => select(item.id)}
                      className={`${rowClass(item.id)} grid ${columns} min-h-[52px] items-center gap-3 px-3.5 py-1.5`}
                      style={{ animationDelay: `${0.4 + index * 0.045}s` }}
                    >
                      <span className="flex min-w-0 items-center gap-2.5">
                        <span
                          aria-hidden="true"
                          className={`size-2 shrink-0 rounded-full ${
                            !withStatus ? "bg-brand" : ready ? "bg-ok" : "bg-warning"
                          }`}
                        />
                        <span className="truncate font-bold">{item.document.title}</span>
                      </span>
                      <span className="truncate font-mono text-xs text-muted">{item.source.section}</span>
                      <span className="text-[13px] text-muted">
                        {t(`checklist.submitAs.${item.submit_as}`, { defaultValue: item.submit_as })}
                      </span>
                      {withStatus && (
                        <span
                          className={`justify-self-end rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                            ready ? "bg-ok-bg text-ok" : "bg-warning-bg text-warning"
                          }`}
                        >
                          {t(`checklist.status.${ready ? "ready" : "missing"}`)}
                        </span>
                      )}
                    </button>
                  );
                })}
                {rows.length === 0 && <p className="p-3.5 text-sm text-muted">{t("checklist.noMatch")}</p>}
              </div>
            </div>
          </section>

          <section
            aria-labelledby="rules-heading"
            className="va-rise flex flex-col gap-3 rounded-[22px] border border-line bg-white p-5"
            style={{ animationDelay: "0.5s" }}
          >
            <h2 id="rules-heading" className="text-lg font-extrabold tracking-tight">
              {t("checklist.rules", { count: checklist.rules.length })}
            </h2>
            <ul className="flex flex-col gap-0.5">
              {checklist.rules.map((rule) => (
                <li key={rule.id}>
                  <button
                    type="button"
                    aria-pressed={selected?.id === rule.id}
                    onClick={() => select(rule.id)}
                    className={`${rowClass(rule.id)} flex min-h-11 items-center justify-between gap-3 px-3.5 py-1.5`}
                  >
                    <span className="text-sm font-semibold">{rule.title}</span>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        rule.severity === "error" ? "bg-error-bg text-error" : "bg-warning-bg text-warning"
                      }`}
                    >
                      {t(`checklist.severity.${rule.severity}`)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {selected && (
          <div
            ref={side}
            className="flex min-w-0 flex-[1_1_320px] flex-col gap-4 xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:overflow-y-auto"
          >
            <SourcePanel entry={selected} />
            {selectedItem && itemPanel?.(selectedItem)}
          </div>
        )}
      </div>
    </div>
  );
}
