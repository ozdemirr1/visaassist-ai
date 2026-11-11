import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { IconCheck } from "./icons";

interface Props {
  mode: "login" | "register";
  pending: boolean;
  error: string | null;
  onSubmit: (email: string, password: string) => void;
}

const POINTS = ["sources", "documents", "decision"] as const;

export function AuthForm({ mode, pending, error, onSubmit }: Props) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const register = mode === "register";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit(email, password);
  };
  const input =
    "mt-1.5 block min-h-12 w-full rounded-xl border border-line bg-white px-3.5 transition-colors focus:border-brand";

  return (
    <div className="mx-auto grid max-w-[980px] gap-4 lg:grid-cols-[1.05fr_1fr]">
      <aside
        className="va-rise relative order-2 flex flex-col gap-6 overflow-hidden rounded-[22px] bg-navy p-7 text-navy-text lg:order-1"
        style={{ animationDelay: "0.08s" }}
      >
        <div aria-hidden="true" className="va-dots absolute inset-0 opacity-60" />
        <div className="relative flex flex-col gap-2">
          <span className="font-mono text-[11px] tracking-widest text-navy-muted uppercase">
            {t("app.name")}
          </span>
          <h2 className="text-[28px] leading-tight font-extrabold tracking-tight text-white">
            {t("auth.sideTitle")}
          </h2>
        </div>
        <ul className="relative flex flex-col gap-3">
          {POINTS.map((point, index) => (
            <li
              key={point}
              className="va-rise flex gap-3 rounded-[14px] border border-navy-line bg-navy-2 p-3.5 text-sm"
              style={{ animationDelay: `${0.2 + index * 0.08}s` }}
            >
              <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-brand text-white">
                <IconCheck />
              </span>
              {t(`auth.points.${point}`)}
            </li>
          ))}
        </ul>
        <span className="relative mt-auto flex items-center gap-2 text-xs text-navy-muted">
          <span aria-hidden="true" className="va-live size-2 rounded-full bg-mint" />
          {t("home.fromTurkiye")}
        </span>
      </aside>

      <form
        onSubmit={submit}
        className="va-rise order-1 flex flex-col gap-5 rounded-[22px] border border-line bg-white p-7 lg:order-2"
        style={{ animationDelay: "0.16s" }}
      >
        <div>
          <span className="font-mono text-[11px] tracking-widest text-muted uppercase">
            {t(register ? "nav.register" : "nav.login")}
          </span>
          <h1 className="mt-1 text-[28px] leading-tight font-extrabold tracking-tight">
            {t(register ? "auth.registerTitle" : "auth.loginTitle")}
          </h1>
        </div>
        <label className="block text-sm font-semibold">
          {t("auth.email")}
          <input
            className={input}
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="block text-sm font-semibold">
          {t("auth.password")}
          <input
            className={input}
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            required
            minLength={register ? 10 : undefined}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {register && (
            <span className="mt-1 block text-xs font-normal text-muted">{t("auth.passwordHint")}</span>
          )}
        </label>
        {error && (
          <p role="alert" className="rounded-xl bg-error-bg p-3 text-sm text-error">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={pending}
          className="va-btn min-h-12 w-full rounded-xl bg-brand font-bold text-white shadow-[0_8px_20px_rgb(36_80_230/0.3)] disabled:opacity-60"
        >
          {pending ? t("auth.working") : t(register ? "auth.submitRegister" : "auth.submitLogin")}
        </button>
        <p className="text-sm text-muted">
          {t(register ? "auth.haveAccount" : "auth.noAccount")}{" "}
          <Link to={register ? "/login" : "/register"} className="font-bold text-brand">
            {t(register ? "nav.login" : "nav.register")}
          </Link>
        </p>
      </form>
    </div>
  );
}
