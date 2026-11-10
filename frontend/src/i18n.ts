// Interface text comes only from the translation files (NFR-10). The chosen language is kept in
// the browser as a convenience; storage may be unavailable, so every access is guarded.
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import type { Language } from "./api/types";
import en from "./locales/en.json";
import tr from "./locales/tr.json";

export const LANGUAGES: Language[] = ["tr", "en"];
const STORAGE_KEY = "visaassist.language";

function storedLanguage(): Language {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (value === "tr" || value === "en") return value;
  } catch {
    // storage blocked: fall back to Turkish
  }
  return "tr";
}

export function setLanguage(language: Language): void {
  void i18n.changeLanguage(language);
  document.documentElement.lang = language;
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // ignore
  }
}

void i18n.use(initReactI18next).init({
  resources: { tr: { translation: tr }, en: { translation: en } },
  lng: storedLanguage(),
  fallbackLng: "tr",
  interpolation: { escapeValue: false }, // React escapes already
  showSupportNotice: false,
});

export default i18n;
