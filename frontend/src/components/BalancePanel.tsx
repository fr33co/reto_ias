import type { BalanceDto } from "../api/types";
import { formatNumber } from "../domain/format";
import { useI18n } from "../i18n";

/**
 * Summary of a plot's nitrogen: area, cycle start, limit, used and available, with an accessible meter.
 *
 * @param props.balance - The balance returned by the API.
 */
export function BalancePanel({ balance }: { balance: BalanceDto }) {
  const { t, lang } = useI18n();
  /** Format a number with the active language's decimal separator (2 decimals). */
  const f = (n: number) => formatNumber(n, lang);
  return (
    <section aria-labelledby="balance-title" className="card">
      <h2 id="balance-title">{t("balance.title", { plot: balance.suerte })}</h2>
      <dl className="facts">
        <div><dt>{t("balance.area")}</dt><dd>{f(balance.area_neta_ha)} ha</dd></div>
        <div><dt>{t("balance.cycleStart")}</dt><dd>{balance.inicio_ciclo}</dd></div>
        <div><dt>{t("balance.limit")}</dt><dd>{f(balance.limite_n_kg_ha)} kg N/ha</dd></div>
        <div><dt>{t("balance.used")}</dt><dd>{f(balance.n_ciclo_kg_ha)} kg N/ha</dd></div>
        <div className="highlight"><dt>{t("balance.available")}</dt><dd>{f(balance.n_disponible_kg_ha)} kg N/ha</dd></div>
      </dl>
      <meter min={0} max={balance.limite_n_kg_ha} value={Math.min(balance.n_ciclo_kg_ha, balance.limite_n_kg_ha)}
             aria-label={t("balance.meter")} className="meter">{f(balance.n_ciclo_kg_ha)}</meter>
    </section>
  );
}
