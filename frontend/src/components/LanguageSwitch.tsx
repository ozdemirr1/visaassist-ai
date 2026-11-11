import { useTranslation } from "react-i18next";

import type { Language } from "../api/types";
import { LANGUAGES, setLanguage } from "../i18n";

export function LanguageSwitch() {
  const { t, i18n } = useTranslation();
  return (
    <div
      role="group"
      aria-label={t("nav.language")}
      className="flex rounded-xl border border-line bg-white p-[3px]"
    >
      {LANGUAGES.map((language: Language) => (
        <button
          key={language}
          type="button"
          onClick={() => setLanguage(language)}
          aria-pressed={i18n.language === language}
          className={`min-h-[38px] min-w-11 rounded-lg px-2 text-xs font-bold transition-colors ${
            i18n.language === language ? "bg-navy text-white" : "text-muted hover:bg-ground"
          }`}
        >
          {language.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
