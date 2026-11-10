import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useRegister } from "../api/hooks";
import type { Language } from "../api/types";
import { AuthForm } from "../components/AuthForm";

export function RegisterPage() {
  const { i18n } = useTranslation();
  const register = useRegister();
  const navigate = useNavigate();
  return (
    <AuthForm
      mode="register"
      pending={register.isPending}
      error={register.error?.message ?? null}
      onSubmit={(email, password) =>
        register.mutate(
          { email, password, language: i18n.language as Language },
          { onSuccess: () => navigate("/applications") },
        )
      }
    />
  );
}
