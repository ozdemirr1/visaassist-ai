import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useApplicationFiles } from "../api/hooks";
import { formatDate } from "../components/format";
import { RequireLogin } from "../components/RequireLogin";

function ApplicationList({ email }: { email: string }) {
  const { t, i18n } = useTranslation();
  const files = useApplicationFiles(true);
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("applications.title")}</h1>
          <p className="text-sm text-muted">{t("auth.loggedInAs", { email })}</p>
        </div>
        <Link
          to="/applications/new"
          className="inline-flex min-h-11 items-center rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-dark"
        >
          {t("applications.new")}
        </Link>
      </div>
      {files.data?.length === 0 && <p className="text-muted">{t("applications.empty")}</p>}
      <ul className="space-y-2">
        {files.data?.map((file) => (
          <li key={file.id}>
            <Link
              to={`/applications/${file.id}`}
              className="block rounded-xl border border-line bg-white p-4 hover:border-brand"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium">
                  {t(`destination.${file.destination}`)} · {t(`profile.${file.profile}`)}
                </span>
                <span className="rounded-full bg-ground px-2 py-0.5 text-xs font-semibold">
                  {t(`applications.step.${file.step}`)}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted">
                {t("applications.trip", {
                  start: formatDate(file.trip_start, i18n.language),
                  end: formatDate(file.trip_end, i18n.language),
                })}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ApplicationsPage() {
  return <RequireLogin>{(user) => <ApplicationList email={user.email} />}</RequireLogin>;
}
