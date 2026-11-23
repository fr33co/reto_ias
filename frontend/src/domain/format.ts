import type { Language } from "../i18n";

const LOCALE: Record<Language, string> = { es: "es-CO", en: "en-US" };

/** Format a number for the active language (comma decimals in Spanish, point in English). */
export const formatNumber = (n: number, lang: Language, digits = 2): string =>
  new Intl.NumberFormat(LOCALE[lang], { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(n);

/** Format an ISO timestamp in the America/Bogota timezone. */
export const formatDateTime = (iso: string, lang: Language): string =>
  new Intl.DateTimeFormat(LOCALE[lang], { dateStyle: "short", timeStyle: "short", timeZone: "America/Bogota" }).format(new Date(iso));
