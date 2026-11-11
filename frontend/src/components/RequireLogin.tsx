import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useCurrentUser } from "../api/hooks";
import type { User } from "../api/types";
import { IconLogin } from "./icons";

/** Renders its children with the logged-in user, or a link to the login page. */
export function RequireLogin({ children }: { children: (user: User) => ReactNode }) {
  const { t } = useTranslation();
  const user = useCurrentUser();
  if (user.isPending) return null;
  if (!user.data) {
    return (
      <div className="va-rise mx-auto flex max-w-md flex-col items-center gap-4 rounded-[22px] border border-line bg-white p-8 text-center">
        <span className="flex size-12 items-center justify-center rounded-2xl bg-brand-soft text-brand">
          <IconLogin />
        </span>
        <p className="font-semibold">{t("applications.loginRequired")}</p>
        <Link
          to="/login"
          className="va-btn inline-flex min-h-11 items-center rounded-xl bg-brand px-5 font-bold text-white"
        >
          {t("nav.login")}
        </Link>
      </div>
    );
  }
  return <>{children(user.data)}</>;
}
