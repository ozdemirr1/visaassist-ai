import { useNavigate } from "react-router";

import { useLogin } from "../api/hooks";
import { AuthForm } from "../components/AuthForm";

export function LoginPage() {
  const login = useLogin();
  const navigate = useNavigate();
  return (
    <AuthForm
      mode="login"
      pending={login.isPending}
      error={login.error?.message ?? null}
      onSubmit={(email, password) =>
        login.mutate({ email, password }, { onSuccess: () => navigate("/applications") })
      }
    />
  );
}
