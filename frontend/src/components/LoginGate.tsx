import { useState, type FormEvent } from "react";
import { readSession, type SessionInfo } from "../api/session";
import { useI18n } from "../i18n";

/**
 * Sign-in gate: the operator pastes the session token (kept in memory only).
 *
 * @param props.onLogin - Called with the token and its decoded display data.
 * @param props.notice - Optional message (e.g. session closed by inactivity).
 */
export function LoginGate({ onLogin, notice }: { onLogin: (token: string, info: SessionInfo) => void; notice?: string }) {
  const { t } = useI18n();
  const [token, setToken] = useState("");
  const [error, setError] = useState(false);

  /** Decode the token for display and sign in; show an error if it is not a session token. Clears the input afterwards. */
  function submit(e: FormEvent) {
    e.preventDefault();
    const info = readSession(token.trim());
    if (!info) return setError(true);
    onLogin(token.trim(), info);
    setToken("");
  }

  return (
    <section aria-labelledby="login-title" className="card narrow">
      <h2 id="login-title">{t("session.title")}</h2>
      {notice && <p role="status" className="notice">{notice}</p>}
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="token">{t("session.token.label")}</label>
          <p id="token-hint" className="hint">{t("session.token.hint")}</p>
          <input id="token" type="password" autoComplete="off" value={token} onChange={(e) => { setToken(e.target.value); setError(false); }}
                 aria-describedby={error ? "token-hint token-error" : "token-hint"} aria-invalid={error} />
          {error && <p id="token-error" className="error">{t("session.invalid")}</p>}
        </div>
        <button type="submit" className="primary">{t("session.start")}</button>
      </form>
    </section>
  );
}
