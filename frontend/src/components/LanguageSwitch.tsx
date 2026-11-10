import { useTranslation } from "react-i18next";

import type { Language } from "../api/types";
import { LANGUAGES, setLanguage } from "../i18n";

export function LanguageSwitch() {
  const { t, i18n } = useTranslation();
  return (
    <div role="group" aria-label={t("nav.language")} className="flex rounded-lg border border-line">
      {LANGUAGES.map((language: Language) => (
        <button
          key={language}
          type="button"
          onClick={() => setLanguage(language)}
          aria-pressed={i18n.language === language}
          className={`min-h-11 min-w-11 px-3 text-sm font-semibold first:rounded-l-lg last:rounded-r-lg ${
            i18n.language === language ? "bg-brand text-white" : "text-muted hover:bg-ground"
          }`}
        >
          {language.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
