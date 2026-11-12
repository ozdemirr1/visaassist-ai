import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useNavigate } from "react-router";

import { useApplicationFiles, useChecklist, useCurrentUser, useLogout } from "../api/hooks";
import type { Language } from "../api/types";
import { formatShortDate } from "./format";
import { IconBrand, IconFolder, IconGlobe, IconList, IconLogin, IconLogout, IconPlus } from "./icons";
import { LanguageSwitch } from "./LanguageSwitch";

const sideLink = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-11 items-center gap-3 rounded-[10px] px-2.5 font-semibold transition-colors ${
    isActive
      ? "bg-brand font-bold text-white shadow-[0_8px_20px_rgb(36_80_230/0.35)]"
      : "text-navy-text hover:bg-navy-2 hover:text-white"
  }`;

const tabLink = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-[52px] flex-col items-center justify-center gap-0.5 rounded-2xl text-[11px] font-semibold ${
    isActive ? "bg-brand font-bold text-white" : "text-navy-text"
  }`;

function Brand() {
  const { t } = useTranslation();
  return (
    <Link to="/" className="flex items-center gap-2.5 px-2">
      <span className="flex size-[34px] items-center justify-center rounded-[10px] bg-brand text-white">
        <IconBrand />
      </span>
      <span className="text-base font-extrabold tracking-tight">{t("app.name")}</span>
    </Link>
  );
}

function Sidebar({ loggedIn }: { loggedIn: boolean }) {
  const { t, i18n } = useTranslation();
  const files = useApplicationFiles(loggedIn);
  // The same query the checklist page uses; here only for the requirement set in force.
  const checklist = useChecklist("NL", "employed", i18n.language as Language);
  const label = "px-2.5 font-mono text-[10px] tracking-[0.12em] text-navy-muted uppercase";

  return (
    <aside className="va-slide hidden w-64 shrink-0 flex-col gap-6 overflow-y-auto bg-navy px-3.5 py-5 text-sm text-navy-text lg:sticky lg:top-0 lg:flex lg:h-screen">
      <div className="text-white">
        <Brand />
      </div>

      {loggedIn && (
        <div className="flex flex-col gap-2">
          <span className={label}>{t("shell.files")}</span>
          {files.data?.map((file) => (
            <NavLink
              key={file.id}
              to={`/applications/${file.id}`}
              className={({ isActive }) =>
                `flex min-h-[52px] items-center gap-2.5 rounded-xl border px-2.5 transition-colors ${
                  isActive
                    ? "border-navy-line bg-navy-2 text-white"
                    : "border-transparent hover:bg-navy-2 hover:text-white"
                }`
              }
            >
              <span className="flex size-8 items-center justify-center rounded-[9px] bg-navy-line font-mono text-[11px] font-semibold text-white">
                {file.destination}
              </span>
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="font-bold">{t(`destination.${file.destination}`)}</span>
                <span className="text-xs text-navy-muted">
                  {formatShortDate(file.trip_start, i18n.language)} –{" "}
                  {formatShortDate(file.trip_end, i18n.language)}
                </span>
              </span>
            </NavLink>
          ))}
          <Link
            to="/applications/new"
            className="flex min-h-11 items-center gap-2.5 rounded-xl border border-dashed border-[#34446b] px-2.5 font-semibold transition-colors hover:bg-navy-2 hover:text-white"
          >
            <IconPlus />
            {t("applications.new")}
          </Link>
        </div>
      )}

      <nav aria-label={t("shell.menu")} className="flex flex-col gap-0.5">
        <span className={`${label} pb-1.5`}>{t("shell.menu")}</span>
        <NavLink to="/" end className={sideLink}>
          <IconList />
          {t("nav.home")}
        </NavLink>
        <NavLink to="/destinations" className={sideLink}>
          <IconGlobe />
          {t("nav.destinations")}
        </NavLink>
        <NavLink to="/applications" end className={sideLink}>
          <IconFolder />
          {t("nav.applications")}
        </NavLink>
      </nav>

      <div className="mt-auto flex flex-col gap-2 rounded-[14px] border border-navy-line bg-navy-2 p-3.5">
        <span className="flex items-center gap-2 font-bold text-white">
          <span aria-hidden="true" className="va-live size-2 rounded-full bg-mint" />
          {t("shell.sourcesTitle")}
        </span>
        <span className="text-xs text-navy-muted">{t("shell.sourcesText")}</span>
        {checklist.data && (
          <span className="font-mono text-[11px] text-navy-muted">
            {t("shell.ruleSet", { id: checklist.data.requirement_set_id.slice(0, 12) })}
          </span>
        )}
      </div>
    </aside>
  );
}

export function Layout() {
  const { t } = useTranslation();
  const { data: user } = useCurrentUser();
  const logout = useLogout();
  const navigate = useNavigate();
  const action =
    "va-btn flex min-h-11 items-center gap-2 rounded-xl border border-line bg-white px-3 text-sm font-semibold";

  return (
    <div className="min-h-screen lg:flex">
      <Sidebar loggedIn={Boolean(user)} />

      <div className="flex min-w-0 flex-1 flex-col pb-[calc(7rem+env(safe-area-inset-bottom))] lg:pb-0">
        <header className="va-rise flex flex-wrap items-center gap-3 px-4 pt-4 lg:px-7">
          <div className="mr-auto lg:hidden">
            <Brand />
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-3">
            <LanguageSwitch />
            {user ? (
              <>
                <span className="hidden min-h-11 items-center gap-2.5 rounded-xl border border-line bg-white py-1 pr-3 pl-1.5 text-sm font-semibold sm:flex">
                  <span
                    aria-hidden="true"
                    className="flex size-8 items-center justify-center rounded-full bg-navy text-xs font-bold text-white uppercase"
                  >
                    {user.email.slice(0, 2)}
                  </span>
                  {user.email}
                </span>
                <button
                  type="button"
                  className={action}
                  onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/") })}
                >
                  <IconLogout />
                  {t("nav.logout")}
                </button>
              </>
            ) : (
              <Link to="/login" className={action}>
                <IconLogin />
                {t("nav.login")}
              </Link>
            )}
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1200px] flex-1 px-4 py-5 lg:px-7">
          <Outlet />
        </main>

        <footer className="mx-auto w-full max-w-[1200px] px-4 pb-6 text-xs text-muted lg:px-7">
          {t("app.disclaimer")}
        </footer>
      </div>

      <nav
        aria-label={t("shell.menu")}
        className="fixed inset-x-4 bottom-[calc(1rem+env(safe-area-inset-bottom))] z-10 grid grid-cols-4 gap-1 rounded-[22px] bg-navy p-1.5 shadow-[0_12px_30px_rgb(11_19_36/0.35)] lg:hidden"
      >
        <NavLink to="/" end className={tabLink}>
          <IconList />
          {t("nav.home")}
        </NavLink>
        <NavLink to="/destinations" className={tabLink}>
          <IconGlobe />
          {t("nav.destinations")}
        </NavLink>
        <NavLink to="/applications" end className={tabLink}>
          <IconFolder />
          {t("nav.applications")}
        </NavLink>
        <NavLink to="/applications/new" className={tabLink}>
          <IconPlus />
          {t("shell.newShort")}
        </NavLink>
      </nav>
    </div>
  );
}
