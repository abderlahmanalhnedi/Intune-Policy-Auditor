import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { resources } from "./resources";

const storedLanguage = localStorage.getItem("ipa-language");
const initialLanguage = storedLanguage === "en" ? "en" : "de";

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage,
  fallbackLng: "en",
  supportedLngs: ["de", "en"],
  interpolation: { escapeValue: false },
  returnNull: false,
});

document.documentElement.lang = initialLanguage;

export default i18n;

