import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

interface Props {
  mode: "login" | "register";
  pending: boolean;
  error: string | null;
  onSubmit: (email: string, password: string) => void;
}

export function AuthForm({ mode, pending, error, onSubmit }: Props) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const register = mode === "register";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit(email, password);
  };
  const input = "mt-1 block min-h-11 w-full rounded-lg border border-line bg-white px-3";

  return (
    <form onSubmit={submit} className="mx-auto max-w-sm space-y-4 rounded-xl bg-white p-6 shadow-sm">
      <h1 className="text-xl font-bold">{t(register ? "auth.registerTitle" : "auth.loginTitle")}</h1>
      <label className="block text-sm font-medium">
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
      <label className="block text-sm font-medium">
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
        {register && <span className="text-xs text-muted">{t("auth.passwordHint")}</span>}
      </label>
      {error && (
        <p role="alert" className="rounded-lg bg-error-bg p-3 text-sm text-error">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="min-h-11 w-full rounded-lg bg-brand font-semibold text-white hover:bg-brand-dark disabled:opacity-60"
      >
        {pending ? t("auth.working") : t(register ? "auth.submitRegister" : "auth.submitLogin")}
      </button>
      <p className="text-sm text-muted">
        {t(register ? "auth.haveAccount" : "auth.noAccount")}{" "}
        <Link to={register ? "/login" : "/register"} className="font-semibold text-brand">
          {t(register ? "nav.login" : "nav.register")}
        </Link>
      </p>
    </form>
  );
}
