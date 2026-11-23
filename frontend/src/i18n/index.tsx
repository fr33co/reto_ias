import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { en } from "./en";
import { es, type MessageKey } from "./es";

/** Supported UI languages. */
export type Language = "es" | "en";
type Params = Record<string, string | number>;
const catalogs: Record<Language, Record<MessageKey, string>> = { es, en };

interface I18n {
  lang: Language;
  t: (key: MessageKey, params?: Params) => string;
  toggle: () => void;
}
const Ctx = createContext<I18n | null>(null);

/**
 * Replace `{name}` placeholders with the given parameters.
 *
 * @param template - Message with placeholders.
 * @param params - Values by name; a missing one leaves the placeholder visible.
 */
export function interpolate(template: string, params: Params = {}): string {
  return template.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? `{${k}}`));
}

/**
 * Provide the active language and the translation function to the tree.
 *
 * @param props.initial - Initial language (defaults to the browser's: English or Spanish).
 */
export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Language }) {
  const [lang, setLang] = useState<Language>(initial ?? (navigator.language.startsWith("en") ? "en" : "es"));
  const t = useCallback((key: MessageKey, params?: Params) => interpolate(catalogs[lang][key], params), [lang]);
  const value = useMemo(() => ({ lang, t, toggle: () => setLang((l) => (l === "es" ? "en" : "es")) }), [lang, t]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

/**
 * Access the active language, `t(key, params)` and `toggle()`.
 *
 * @throws If used outside `I18nProvider`.
 */
export function useI18n(): I18n {
  const v = useContext(Ctx);
  if (!v) throw new Error("useI18n outside I18nProvider");
  return v;
}
