import { useTranslation } from "react-i18next";
import { Route, Routes } from "react-router";

import { Layout } from "./components/Layout";
import { ApplicationDetailPage } from "./pages/ApplicationDetailPage";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { NewApplicationPage } from "./pages/NewApplicationPage";
import { RegisterPage } from "./pages/RegisterPage";

function NotFound() {
  const { t } = useTranslation();
  return <p className="text-muted">{t("notFound")}</p>;
}

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="applications" element={<ApplicationsPage />} />
        <Route path="applications/new" element={<NewApplicationPage />} />
        <Route path="applications/:id" element={<ApplicationDetailPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
