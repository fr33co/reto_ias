import type { BalanceDto } from "../api/types";
import { formatDateTime, formatNumber } from "../domain/format";
import { useI18n } from "../i18n";

/**
 * Cycle history (newest first) with pagination. It is presentation only: the cycle's nitrogen comes from the API, never from these rows.
 *
 * @param props.balance - Balance holding the current history page.
 * @param props.onPage - Called with the page number to load.
 */
export function HistoryTable({ balance, onPage }: { balance: BalanceDto; onPage: (page: number) => void }) {
  const { t, lang } = useI18n();
  const { pagina, paginas, despachos } = balance.historial;
  return (
    <section aria-labelledby="history-title" className="card">
      <h2 id="history-title">{t("history.title")}</h2>
      {despachos.length === 0 ? (
        <p>{t("history.empty")}</p>
      ) : (
        <div className="table-wrap" tabIndex={0} role="region" aria-labelledby="history-title">
          <table>
            <caption className="sr-only">{t("history.caption")}</caption>
            <thead>
              <tr>
                {(["date", "order", "product", "bags", "n", "foreman", "counter"] as const).map((c) => (
                  <th key={c} scope="col">{t(`history.col.${c}` as const)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {despachos.map((d) => (
                <tr key={d.id}>
                  <td>{formatDateTime(d.registrado_en, lang)}</td>
                  <td>{d.orden}</td>
                  <td>{d.producto}</td>
                  <td className="num">{d.bultos}</td>
                  <td className="num">{formatNumber(d.n_despacho_kg_ha, lang)}</td>
                  <td>{d.capataz}</td>
                  <td>{d.ventanilla}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <nav aria-label={t("history.title")} className="pager">
        <button type="button" onClick={() => onPage(pagina - 1)} disabled={pagina <= 1}>{t("history.prev")}</button>
        <span aria-live="polite">{t("history.page", { page: pagina, pages: paginas })}</span>
        <button type="button" onClick={() => onPage(pagina + 1)} disabled={pagina >= paginas}>{t("history.next")}</button>
      </nav>
    </section>
  );
}
