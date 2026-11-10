import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useApplicationFiles, useCurrentUser } from "../api/hooks";

export function ApplicationsPage() {
  const { t, i18n } = useTranslation();
  const user = useCurrentUser();
  const files = useApplicationFiles(Boolean(user.data));
  const date = (value: string) =>
    new Date(`${value}T00:00:00`).toLocaleDateString(i18n.language === "tr" ? "tr-TR" : "en-GB");

  if (user.isPending) return null;
  if (!user.data) {
    return (
      <p className="text-muted">
        {t("applications.loginRequired")}{" "}
        <Link to="/login" className="font-semibold text-brand">
          {t("nav.login")}
        </Link>
      </p>
    );
  }
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{t("applications.title")}</h1>
        <p className="text-sm text-muted">{t("auth.loggedInAs", { email: user.data.email })}</p>
      </div>
      {files.data?.length === 0 && <p className="text-muted">{t("applications.empty")}</p>}
      <ul className="space-y-2">
        {files.data?.map((file) => (
          <li key={file.id} className="rounded-xl border border-line bg-white p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-medium">
                {t(`destination.${file.destination}`)} · {t(`profile.${file.profile}`)}
              </span>
              <span className="rounded-full bg-ground px-2 py-0.5 text-xs font-semibold">
                {t(`applications.step.${file.step}`)}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">
              {t("applications.trip", { start: date(file.trip_start), end: date(file.trip_end) })}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
