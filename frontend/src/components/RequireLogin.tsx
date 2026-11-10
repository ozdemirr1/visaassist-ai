import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { useCurrentUser } from "../api/hooks";
import type { User } from "../api/types";

/** Renders its children with the logged-in user, or a link to the login page. */
export function RequireLogin({ children }: { children: (user: User) => ReactNode }) {
  const { t } = useTranslation();
  const user = useCurrentUser();
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
  return <>{children(user.data)}</>;
}
