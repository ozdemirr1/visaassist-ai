import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useNavigate } from "react-router";

import { useCurrentUser, useLogout } from "../api/hooks";
import { LanguageSwitch } from "./LanguageSwitch";

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-ground text-brand" : "text-muted hover:text-ink"}`;

export function Layout() {
  const { t } = useTranslation();
  const { data: user } = useCurrentUser();
  const logout = useLogout();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2 px-4 py-3">
          <NavLink to="/" className="mr-auto text-lg font-bold text-brand">
            {t("app.name")}
          </NavLink>
          <nav className="flex flex-wrap items-center gap-1">
            <NavLink to="/" end className={link}>
              {t("nav.home")}
            </NavLink>
            <NavLink to="/applications" className={link}>
              {t("nav.applications")}
            </NavLink>
            {user ? (
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm font-medium text-muted hover:text-ink"
                onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/") })}
              >
                {t("nav.logout")}
              </button>
            ) : (
              <NavLink to="/login" className={link}>
                {t("nav.login")}
              </NavLink>
            )}
          </nav>
          <LanguageSwitch />
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      <footer className="border-t border-line bg-white">
        <p className="mx-auto max-w-5xl px-4 py-4 text-xs text-muted">{t("app.disclaimer")}</p>
      </footer>
    </div>
  );
}
