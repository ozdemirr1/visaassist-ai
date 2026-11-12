import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useDestinations } from "../api/hooks";
import type { DestinationInfo, Language } from "../api/types";
import { formatDate } from "../components/format";

function DestinationCard({ destination, index }: { destination: DestinationInfo; index: number }) {
  const { t } = useTranslation();
  return (
    <section
      aria-labelledby={`destination-${destination.id}`}
      className="va-rise flex flex-col gap-4 rounded-[22px] border border-line bg-white p-5"
      style={{ animationDelay: `${0.16 + index * 0.08}s` }}
    >
      <div className="flex flex-wrap items-center gap-3">
        <span
          aria-hidden="true"
          className="flex size-11 items-center justify-center rounded-xl bg-navy font-mono text-xs font-semibold text-white"
        >
          {destination.id}
        </span>
        <h2 id={`destination-${destination.id}`} className="text-2xl font-extrabold tracking-tight">
          {t(`destination.${destination.id}`)}
        </h2>
        {destination.schengen && (
          <span className="rounded-full bg-brand-soft px-2.5 py-0.5 text-xs font-bold text-brand">
            {t("destinations.schengen")}
          </span>
        )}
        <Link
          to="/"
          className="va-btn ml-auto inline-flex min-h-11 items-center rounded-xl border border-line px-3 text-sm font-bold text-brand"
        >
          {t("destinations.checklist")}
        </Link>
      </div>
      <dl className="grid gap-3 md:grid-cols-2">
        {destination.facts.map((fact) => (
          <div key={fact.id} className="va-card flex flex-col gap-2 rounded-[14px] bg-ground p-4">
            <dt className="font-mono text-[10px] tracking-[0.12em] text-muted uppercase">{fact.title}</dt>
            <dd className="flex flex-1 flex-col gap-2">
              <span className="text-[15px] font-semibold">{fact.text}</span>
              <span className="mt-auto text-xs text-muted">
                {t("checklist.source")} · {fact.source.section} ·{" "}
                <a
                  href={fact.source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-bold text-brand underline"
                >
                  {fact.source.publisher}
                </a>
              </span>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** Discovery page (FR-01): the practical facts of applying, each from an official source. */
export function DestinationsPage() {
  const { t, i18n } = useTranslation();
  const destinations = useDestinations(i18n.language as Language);
  return (
    <div className="flex flex-col gap-4">
      <section
        className="va-rise relative overflow-hidden rounded-[22px] bg-navy p-6 text-navy-text"
        style={{ animationDelay: "0.08s" }}
      >
        <div aria-hidden="true" className="va-dots absolute inset-0 opacity-60" />
        <div className="relative">
          <span className="font-mono text-[11px] tracking-widest text-navy-muted uppercase">
            {t("destinations.kicker")}
          </span>
          <h1 className="mt-1 text-[34px] leading-tight font-extrabold tracking-tight text-white">
            {t("destinations.title")}
          </h1>
          <p className="mt-1 max-w-2xl">{t("destinations.lead")}</p>
          {destinations.data && (
            <p className="mt-3 font-mono text-[11px] text-navy-muted">
              {t("destinations.checked", {
                date: formatDate(destinations.data.checked_on, i18n.language),
              })}
            </p>
          )}
        </div>
      </section>
      {destinations.isPending && <p className="text-muted">{t("destinations.loading")}</p>}
      {destinations.isError && (
        <p role="alert" className="rounded-xl bg-error-bg p-3 text-error">
          {destinations.error.message}
        </p>
      )}
      {destinations.data?.destinations.map((destination, index) => (
        <DestinationCard key={destination.id} destination={destination} index={index} />
      ))}
      <p className="text-xs text-muted">{t("home.fromTurkiye")}</p>
    </div>
  );
}
