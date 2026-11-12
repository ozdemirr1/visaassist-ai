import { type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { useApplicationFile, useCheck, useCheckRuns, useChecklist, useKeepCheck } from "../api/hooks";
import type { ApplicationFile, CheckRun, Language, RuleResult, RuleSummary } from "../api/types";
import { issueText } from "../components/FindingsPanel";
import { RequireLogin } from "../components/RequireLogin";
import { useCountUp } from "../hooks/useCountUp";

/** How many rules passed in `run` but not in `previous`, and the other way round. */
export function runChange(run: CheckRun, previous: CheckRun): { improved: number; worsened: number } {
  const before = new Map(previous.rules.map((rule) => [rule.rule_id, rule.status]));
  let improved = 0;
  let worsened = 0;
  for (const rule of run.rules) {
    const was = before.get(rule.rule_id);
    if (was === undefined || was === rule.status) continue;
    if (rule.status === "passed") improved += 1;
    else if (was === "passed") worsened += 1;
  }
  return { improved, worsened };
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  const shown = useCountUp(value);
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-navy-muted">{label}</span>
      <span className={`text-3xl font-extrabold tracking-tighter tabular-nums ${tone ?? "text-white"}`}>
        {shown}
      </span>
    </div>
  );
}

function Group({ id, title, count, children }: { id: string; title: string; count: number; children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <section
      aria-labelledby={id}
      className="va-rise flex flex-col gap-3 rounded-[22px] border border-line bg-white p-5"
    >
      <h2 id={id} className="text-lg font-extrabold tracking-tight">
        {title} <span className="font-mono text-sm font-medium text-muted">{count}</span>
      </h2>
      {count === 0 ? <p className="text-sm text-muted">{t("findings.none")}</p> : children}
    </section>
  );
}

function SourceLine({ source }: { source: RuleSummary["source"] }) {
  const { t } = useTranslation();
  return (
    <p className="text-xs text-muted">
      {t("checklist.source")} · {source.section} ·{" "}
      <a href={source.url} target="_blank" rel="noopener noreferrer" className="font-bold text-brand underline">
        {t("checklist.openSource")}
      </a>
    </p>
  );
}

function RuleCard({ result, rule }: { result: RuleResult; rule: RuleSummary | undefined }) {
  const { t, i18n } = useTranslation();
  const failed = result.status === "failed";
  return (
    <li className="flex flex-col gap-2 rounded-[14px] bg-ground p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-bold">{rule?.title ?? result.rule_id}</span>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
            result.severity === "error" ? "bg-error-bg text-error" : "bg-warning-bg text-warning"
          }`}
        >
          {t(`checklist.severity.${result.severity}`)}
        </span>
      </div>
      <ul className="flex flex-col gap-1.5">
        {result.issues.map((issue, index) => (
          <li
            key={`${issue.code}-${issue.document_id}-${issue.field}-${index}`}
            className={`rounded-xl p-2.5 text-sm ${
              failed ? "bg-error-bg text-error" : "bg-warning-bg text-warning"
            }`}
          >
            {issueText(issue, i18n.language, t)}
          </li>
        ))}
      </ul>
      {rule && (
        <>
          {/* Official passages stay in their original language (NFR-10). */}
          <blockquote lang="en" className="border-l-[3px] border-brand pl-3 text-sm italic">
            {rule.source.passage}
          </blockquote>
          <SourceLine source={rule.source} />
        </>
      )}
    </li>
  );
}

function Findings({ file }: { file: ApplicationFile }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Language;
  const check = useCheck(file.id, lang);
  const checklist = useChecklist(file.destination, file.profile, lang);
  const runs = useCheckRuns(file.id);
  const keep = useKeepCheck(file.id);
  const [kept, setKept] = useState(false);

  const rules = new Map(checklist.data?.rules.map((rule) => [rule.id, rule]));
  const items = new Map(checklist.data?.items.map((item) => [item.id, item]));
  const results = check.data?.rules ?? [];
  const byStatus = (status: RuleResult["status"]) => results.filter((result) => result.status === status);
  const failed = byStatus("failed");
  const incomplete = byStatus("incomplete");
  const passed = byStatus("passed");
  const missing = check.data?.missing_documents ?? [];
  const when = (value: string) =>
    new Date(value).toLocaleString(lang === "tr" ? "tr-TR" : "en-GB", {
      dateStyle: "long",
      timeStyle: "short",
    });

  return (
    <div className="flex flex-col gap-4">
      <section
        aria-label={t("findings.title")}
        className="va-rise relative overflow-hidden rounded-[22px] bg-navy p-6 text-navy-text"
        style={{ animationDelay: "0.08s" }}
      >
        <div aria-hidden="true" className="va-dots absolute inset-0 opacity-60" />
        <div className="relative flex flex-col gap-4">
          <div>
            <Link
              to={`/applications/${file.id}`}
              className="font-mono text-[11px] tracking-widest text-navy-muted uppercase"
            >
              ← {t("findings.back")} · {t("detail.title", { destination: t(`destination.${file.destination}`) })}
            </Link>
            <h1 className="mt-1 text-[34px] leading-tight font-extrabold tracking-tight text-white">
              {t("findings.title")}
            </h1>
            <p className="mt-1 max-w-2xl">{t("findings.lead")}</p>
          </div>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(120px,1fr))] gap-3">
            <Stat label={t("findings.missing")} value={missing.length} tone="text-amber" />
            <Stat label={t("findings.failed")} value={failed.length} tone="text-amber" />
            <Stat label={t("findings.incomplete")} value={incomplete.length} />
            <Stat label={t("findings.passed")} value={passed.length} tone="text-mint" />
          </div>
          <p className="text-xs text-navy-muted">{t("check.disclaimer")}</p>
        </div>
      </section>

      {check.isError && (
        <p role="alert" className="rounded-xl bg-error-bg p-3 text-error">
          {check.error.message}
        </p>
      )}

      {check.data && (
        <>
          <Group id="findings-missing" title={t("findings.missing")} count={missing.length}>
            <ul className="flex flex-col gap-1.5">
              {missing.map((id) => (
                <li key={id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-ground px-3.5 py-2.5">
                  <span className="font-bold">{items.get(id)?.document.title ?? id}</span>
                  <span className="font-mono text-xs text-muted">{items.get(id)?.source.section}</span>
                </li>
              ))}
            </ul>
          </Group>

          <Group id="findings-failed" title={t("findings.failed")} count={failed.length}>
            <ul className="flex flex-col gap-2">
              {failed.map((result) => (
                <RuleCard key={result.rule_id} result={result} rule={rules.get(result.rule_id)} />
              ))}
            </ul>
          </Group>

          <Group id="findings-incomplete" title={t("findings.incomplete")} count={incomplete.length}>
            <ul className="flex flex-col gap-2">
              {incomplete.map((result) => (
                <RuleCard key={result.rule_id} result={result} rule={rules.get(result.rule_id)} />
              ))}
            </ul>
          </Group>

          <Group id="findings-passed" title={t("findings.passed")} count={passed.length}>
            <ul className="flex flex-col gap-1">
              {passed.map((result) => (
                <li key={result.rule_id} className="flex items-center gap-2.5 px-1 text-sm font-semibold">
                  <span aria-hidden="true" className="size-2 shrink-0 rounded-full bg-ok" />
                  {rules.get(result.rule_id)?.title ?? result.rule_id}
                </li>
              ))}
            </ul>
          </Group>

          {check.data.summary.skipped > 0 && (
            <p className="text-sm text-muted">{t("findings.skipped", { count: check.data.summary.skipped })}</p>
          )}
        </>
      )}

      <section
        aria-labelledby="findings-history"
        className="va-rise flex flex-col gap-3 rounded-[22px] border border-line bg-white p-5"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="findings-history" className="text-lg font-extrabold tracking-tight">
              {t("findings.history")}
            </h2>
            <p className="text-sm text-muted">{t("findings.historyLead")}</p>
          </div>
          <button
            type="button"
            disabled={keep.isPending || !check.data}
            onClick={() => keep.mutate(undefined, { onSuccess: () => setKept(true) })}
            className="va-btn min-h-11 rounded-xl bg-brand px-4 text-sm font-bold text-white disabled:opacity-60"
          >
            {kept ? t("findings.kept") : t("findings.keep")}
          </button>
        </div>
        {keep.error && (
          <p role="alert" className="rounded-xl bg-error-bg p-3 text-sm text-error">
            {keep.error.message}
          </p>
        )}
        {runs.data?.length === 0 && <p className="text-sm text-muted">{t("findings.historyEmpty")}</p>}
        <ol className="flex flex-col gap-1.5">
          {runs.data?.map((run, index, all) => {
            const previous = all[index + 1];
            const change = previous ? runChange(run, previous) : null;
            return (
              <li key={run.id} className="flex flex-col gap-0.5 rounded-xl bg-ground px-3.5 py-2.5 text-sm">
                <span className="font-mono text-xs text-muted">{when(run.created_at)}</span>
                <span className="font-semibold">
                  {t("findings.run", {
                    missing: run.summary.missing_documents,
                    failed: run.summary.failed,
                    incomplete: run.summary.incomplete,
                    passed: run.summary.passed,
                  })}
                </span>
                {change && change.improved > 0 && (
                  <span className="text-xs font-bold text-ok">{t("findings.improved", { count: change.improved })}</span>
                )}
                {change && change.worsened > 0 && (
                  <span className="text-xs font-bold text-error">{t("findings.worsened", { count: change.worsened })}</span>
                )}
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}

function Loader({ id }: { id: string }) {
  const { t } = useTranslation();
  const file = useApplicationFile(id);
  if (file.isPending) return null;
  if (file.isError) return <p className="text-muted">{t("detail.notFound")}</p>;
  return <Findings file={file.data} />;
}

export function FindingsPage() {
  const { id = "" } = useParams();
  return <RequireLogin>{() => <Loader id={id} />}</RequireLogin>;
}
