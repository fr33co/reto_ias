import { useState, type FormEvent } from "react";
import { PLOT_PATTERN } from "../domain/validation";
import { useI18n } from "../i18n";

/**
 * Plot lookup by code (`S-NNN`), since the contract has no listing endpoint.
 *
 * @param props.onSearch - Called with the normalised code.
 * @param props.error - Error from the server (403/404/network) to show under the field.
 * @param props.busy - Disables the button while loading.
 */
export function PlotSearch({ onSearch, error, busy }: { onSearch: (code: string) => void; error?: string; busy: boolean }) {
  const { t } = useI18n();
  const [code, setCode] = useState("");
  const [formatError, setFormatError] = useState(false);
  const shown = formatError ? t("plot.format") : error;

  /** Normalise to upper case and validate the format before calling the server. */
  function submit(e: FormEvent) {
    e.preventDefault();
    const normalized = code.trim().toUpperCase();
    if (!PLOT_PATTERN.test(normalized)) return setFormatError(true);
    setFormatError(false);
    onSearch(normalized);
  }

  return (
    <section aria-labelledby="plot-title" className="card">
      <h2 id="plot-title">{t("plot.title")}</h2>
      <form onSubmit={submit} noValidate className="inline-form">
        <div className="field">
          <label htmlFor="plot">{t("plot.label")}</label>
          <p id="plot-hint" className="hint">{t("plot.hint")}</p>
          <input id="plot" value={code} onChange={(e) => { setCode(e.target.value); setFormatError(false); }} autoComplete="off"
                 maxLength={5} aria-invalid={!!shown} aria-describedby={shown ? "plot-hint plot-error" : "plot-hint"} />
          {shown && <p id="plot-error" className="error" role="alert">{shown}</p>}
        </div>
        <button type="submit" className="primary" disabled={busy}>{t("plot.search")}</button>
      </form>
    </section>
  );
}
