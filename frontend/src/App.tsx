import { useCallback, useMemo, useRef, useState } from "react";
import { createApiClient } from "./api/client";
import type { SessionInfo } from "./api/session";
import type { BalanceDto } from "./api/types";
import { BalancePanel } from "./components/BalancePanel";
import { DispatchForm } from "./components/DispatchForm";
import { HistoryTable } from "./components/HistoryTable";
import { LoginGate } from "./components/LoginGate";
import { PlotSearch } from "./components/PlotSearch";
import { useIdleTimeout } from "./hooks/useIdleTimeout";
import { useI18n } from "./i18n";

/** Inactivity time (ms) after which the session is closed and the screen wiped. */
export const IDLE_MS = 10 * 60 * 1000;

/**
 * Root component of the counter screen.
 *
 * Holds the in-memory session (token never stored in the browser), the loaded balance and the
 * plot lookup, and renders either the sign-in gate or the balance, history and dispatch form.
 *
 * @param props.idleMs - Inactivity limit in ms (injectable for tests; defaults to 10 minutes).
 */
export function App({ idleMs = IDLE_MS }: { idleMs?: number }) {
  const { t, lang, toggle } = useI18n();
  const tokenRef = useRef<string | null>(null);   // memory only: never storage
  const langRef = useRef(lang);
  langRef.current = lang;
  const api = useMemo(() => createApiClient(() => tokenRef.current, () => langRef.current), []);

  const [session, setSession] = useState<SessionInfo | null>(null);
  const [notice, setNotice] = useState<string | undefined>();
  const [balance, setBalance] = useState<BalanceDto | null>(null);
  const [plotError, setPlotError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  /**
   * Sign out: wipe the token, balance and any sensitive state held in memory.
   *
   * @param message - Optional notice key explaining why the session ended.
   */
  const logout = useCallback((message?: "session.expired" | "session.idle") => {
    tokenRef.current = null;       // wipe everything sensitive held in memory
    setSession(null); setBalance(null); setPlotError(undefined);
    setNotice(message ? t(message) : undefined);
  }, [t]);
  const idle = useCallback(() => logout("session.idle"), [logout]);
  useIdleTimeout(session !== null, idleMs, idle);

  /**
   * Load a plot's balance and history page into state.
   *
   * Maps 401 to a session-expired sign-out and 403/404/network errors to a message under the plot field.
   *
   * @param code - Plot code (`S-NNN`).
   * @param page - 1-based history page (defaults to 1).
   */
  async function load(code: string, page = 1) {
    setBusy(true);
    const r = await api.getBalance(code, page);
    setBusy(false);
    if (r.kind === "ok") { setBalance(r.balance); setPlotError(undefined); return; }
    if (r.kind === "unauthorized") return logout("session.expired");
    setBalance(null);
    setPlotError(r.kind === "not_found" ? t("plot.not_found") : r.kind === "forbidden" ? t("plot.forbidden") : r.kind === "network" ? t("error.network") : t("error.generic"));
  }

  return (
    <>
      <a href="#main" className="skip">{lang === "es" ? "Saltar al contenido" : "Skip to content"}</a>
      <header className="top">
        <h1>{t("app.title")}</h1>
        <div className="top-actions">
          {session && <span>{t("header.session", { warehouse: session.warehouse, counter: session.counter })}</span>}
          <button type="button" onClick={toggle} lang={lang === "es" ? "en" : "es"} aria-label={t("lang.switchLabel")}>{t("lang.switch")}</button>
          {session && <button type="button" onClick={() => logout()}>{t("header.logout")}</button>}
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {!session ? (
          <LoginGate notice={notice} onLogin={(token, info) => { tokenRef.current = token; setNotice(undefined); setSession(info); }} />
        ) : (
          <div className="layout">
            <div className="col">
              <PlotSearch onSearch={(c) => load(c)} error={plotError} busy={busy} />
              {balance && <BalancePanel balance={balance} />}
              {balance && <HistoryTable balance={balance} onPage={(p) => load(balance.suerte, p)} />}
            </div>
            <div className="col">
              {balance && (
                <DispatchForm key={balance.suerte} api={api} balance={balance} onBalance={setBalance}
                              onRegistered={() => load(balance.suerte, 1)} onUnauthorized={() => logout("session.expired")} />
              )}
            </div>
          </div>
        )}
      </main>
    </>
  );
}
