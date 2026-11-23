import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ApiClient } from "../api/client";
import type { BalanceDto, DispatchDto } from "../api/types";
import { bagsForDose, doseForBags, gramsToKgHa, nitrogenGrams, toTenths } from "../domain/bags";
import { formatNumber } from "../domain/format";
import { maskNationalId, parseDose, validateForm, type FieldIssue, type FieldKey, type FormValues } from "../domain/validation";
import { useI18n, type Language } from "../i18n";
import type { MessageKey } from "../i18n/es";

type Issue = FieldIssue | { text: string };
type Stage = "editing" | "reviewing" | "sending";
interface LimitInfo { available: number; needed: number; maxBags: number | null; product: string }

const EMPTY: FormValues = { order: "", product: "", dose: "", nationalId: "" };
const FIELD_IDS: Record<FieldKey, string> = { orden: "f-order", producto: "f-product", dosis_kg_ha: "f-dose", cedula_capataz: "f-id" };
const LABELS: Record<FieldKey, MessageKey> = { orden: "form.order.label", producto: "form.product.label", dosis_kg_ha: "form.dose.label", cedula_capataz: "form.id.label" };

/**
 * Resolve a field issue to text: server messages are already translated, client issues are translation keys.
 *
 * @param i - The issue, or undefined when the field is valid.
 * @param t - Translation function.
 */
function issueText(i: Issue | undefined, t: (k: MessageKey, p?: Record<string, string | number>) => string): string | undefined {
  if (!i) return undefined;
  return "text" in i ? i.text : t(i.code as MessageKey, i.params);
}

/**
 * Dispatch form with the counter's confirmation step.
 *
 * Flow: edit -> *review* (shows the bags to read aloud) -> *confirm* (POST with `bultos_confirmados`).
 * On a 409 for the nitrogen limit every field is kept (WCAG 3.3.7) and the maximum bags are offered.
 * On success the form, including the national id, is wiped.
 *
 * @param props.api - API client.
 * @param props.balance - Current balance (provides area and product rules).
 * @param props.onBalance - Called with the refreshed balance returned by a 409.
 * @param props.onRegistered - Called after a successful registration.
 * @param props.onUnauthorized - Called when the token is rejected (401).
 */
export function DispatchForm({ api, balance, onBalance, onRegistered, onUnauthorized }: {
  api: ApiClient; balance: BalanceDto; onBalance: (b: BalanceDto) => void; onRegistered: () => void; onUnauthorized: () => void;
}) {
  const { t, lang } = useI18n();
  const [values, setValues] = useState<FormValues>(EMPTY);
  const [issues, setIssues] = useState<Partial<Record<FieldKey, Issue>>>({});
  const [stage, setStage] = useState<Stage>("editing");
  const [limit, setLimit] = useState<LimitInfo | null>(null);
  const [success, setSuccess] = useState<{ d: DispatchDto; foreman: string } | null>(null);
  const [general, setGeneral] = useState<string | null>(null);
  const summaryRef = useRef<HTMLDivElement>(null);
  const reviewRef = useRef<HTMLHeadingElement>(null);
  const limitRef = useRef<HTMLDivElement>(null);
  const successRef = useRef<HTMLDivElement>(null);
  const doseRef = useRef<HTMLInputElement>(null);
  const issueKeys = Object.keys(issues) as FieldKey[];

  // Focus follows the flow so keyboard and screen-reader users land on what changed.
  useEffect(() => { if (issueKeys.length) summaryRef.current?.focus(); }, [issues]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (stage === "reviewing") reviewRef.current?.focus(); }, [stage]);
  useEffect(() => { if (limit) limitRef.current?.focus(); }, [limit]);
  useEffect(() => { if (success) successRef.current?.focus(); }, [success]);

  const product = balance.productos.find((p) => p.codigo === values.product);
  const areaTenths = toTenths(balance.area_neta_ha);
  const dose = parseDose(values.dose);
  const bags = product && dose.ok ? bagsForDose(dose.tenths, areaTenths, product) : 0;
  const nAdds = product ? gramsToKgHa(nitrogenGrams(bags, product), areaTenths) : 0;

  /** Create a change handler for one form field. Typing clears the previous success notice. */
  const set = (k: keyof FormValues) => (e: { target: { value: string } }) => {
    setValues((v) => ({ ...v, [k]: e.target.value }));
    setSuccess(null);
  };

  /** Validate on the client and, if valid, open the confirmation step. The barcode scanner's Enter lands here, so it never registers directly. */
  function review(e: FormEvent) {
    e.preventDefault();
    setGeneral(null);
    setLimit(null);
    const found = validateForm(values);
    if (!found.dosis_kg_ha && product && bags < 1) found.dosis_kg_ha = { code: "dose_range", params: { max: 200 } };
    setIssues(found);
    if (Object.keys(found).length === 0) setStage("reviewing");
  }

  /** Send the dispatch and react to the outcome: success (wipe form), 409 limit (keep fields, show maximum bags), duplicate order or field errors (show them on their inputs), 401 (sign out) or a general error. */
  async function confirm() {
    if (!product || !dose.ok) return;
    setStage("sending");
    const result = await api.registerDispatch(balance.suerte, {
      orden: values.order.trim(), producto: values.product, dosis_kg_ha: dose.value,
      cedula_capataz: values.nationalId.trim(), bultos_confirmados: bags,
    });
    switch (result.kind) {
      case "created":
        setSuccess({ d: result.dispatch, foreman: maskNationalId(values.nationalId) });
        setValues(EMPTY);          // the national id never outlives the dispatch
        setIssues({}); setStage("editing"); onRegistered();
        break;
      case "limit":
        // Redundant-entry rule (WCAG 3.3.7): keep every field, only the dose needs adjusting.
        onBalance(result.balance);
        setLimit({ available: result.balance.n_disponible_kg_ha, needed: result.nDispatch, maxBags: result.maxBags, product: values.product });
        setStage("editing");
        break;
      case "duplicate_order":
        setIssues({ orden: { text: result.message } }); setStage("editing"); break;
      case "invalid": {
        const mapped: Partial<Record<FieldKey, Issue>> = {};
        for (const e of result.errors) if (e.campo in FIELD_IDS) mapped[e.campo as FieldKey] = { text: e.mensaje };
        setIssues(mapped);
        if (Object.keys(mapped).length === 0) setGeneral(result.errors[0]?.mensaje ?? t("error.generic"));
        setStage("editing");
        break;
      }
      case "unauthorized": onUnauthorized(); break;
      case "network": setGeneral(t("error.network")); setStage("editing"); break;
      default: setGeneral(result.message ?? t("error.generic")); setStage("editing");
    }
  }

  /** Fill the dose with the value that yields exactly the maximum bags that fit and move focus to it. */
  function useMaxBags() {
    if (!limit?.maxBags || !product) return;
    const tenths = doseForBags(limit.maxBags, areaTenths, product);
    if (tenths === null) return;
    setValues((v) => ({ ...v, dose: (tenths / 10).toFixed(1) }));
    setLimit(null);
    doseRef.current?.focus();
  }

  /** Accessibility attributes for one field: id, `aria-invalid`, `aria-describedby` and the error text. */
  const field = (key: FieldKey) => {
    const text = issueText(issues[key], t);
    return { id: FIELD_IDS[key], "aria-invalid": !!text, "aria-describedby": `${FIELD_IDS[key]}-hint${text ? ` ${FIELD_IDS[key]}-error` : ""}`, text };
  };
  const fOrder = field("orden"), fProduct = field("producto"), fDose = field("dosis_kg_ha"), fId = field("cedula_capataz");

  return (
    <section aria-labelledby="form-title" className="card">
      <h2 id="form-title">{t("form.title")}</h2>

      {success && (
        <div ref={successRef} tabIndex={-1} role="status" className="success">
          <h3>{t("success.title")}</h3>
          <p>{t("success.body", { order: success.d.orden, bags: success.d.bultos, product: success.d.producto, plot: success.d.suerte, foreman: success.foreman })}</p>
        </div>
      )}
      {general && <p role="alert" className="error">{general}</p>}

      {issueKeys.length > 0 && (
        <div ref={summaryRef} tabIndex={-1} role="alert" className="summary">
          <h3>{t("form.errors.title", { count: issueKeys.length })}</h3>
          <ul>{issueKeys.map((k) => (
            <li key={k}><a href={`#${FIELD_IDS[k]}`} onClick={(e) => { e.preventDefault(); document.getElementById(FIELD_IDS[k])?.focus(); }}>
              {t(LABELS[k])}: {issueText(issues[k], t)}</a></li>
          ))}</ul>
        </div>
      )}

      {limit && (
        <div ref={limitRef} tabIndex={-1} role="alert" className="limit">
          <h3>{t("limit.title")}</h3>
          <p>{t("limit.body", { available: formatNumber(limit.available, lang), needed: formatNumber(limit.needed, lang) })}</p>
          <p><strong>{limit.maxBags ? t("limit.maxBags", { bags: limit.maxBags, product: limit.product }) : t("limit.noBags", { product: limit.product })}</strong></p>
          {!!limit.maxBags && product && doseForBags(limit.maxBags, areaTenths, product) !== null && (
            <button type="button" onClick={useMaxBags}>
              {t("limit.use", { bags: limit.maxBags, dose: formatNumber(doseForBags(limit.maxBags, areaTenths, product)! / 10, lang, 1) })}
            </button>
          )}
        </div>
      )}

      <form onSubmit={review} noValidate>
        <fieldset disabled={stage !== "editing"} className="plain">
          <div className="field">
            <label htmlFor={fOrder.id}>{t("form.order.label")}</label>
            <p id={`${fOrder.id}-hint`} className="hint">{t("form.order.hint")}</p>
            <input id={fOrder.id} value={values.order} onChange={set("order")} autoComplete="off" aria-invalid={fOrder["aria-invalid"]} aria-describedby={fOrder["aria-describedby"]} />
            {fOrder.text && <p id={`${fOrder.id}-error`} className="error">{fOrder.text}</p>}
          </div>
          <div className="field">
            <label htmlFor={fProduct.id}>{t("form.product.label")}</label>
            <p id={`${fProduct.id}-hint`} className="hint">{balance.productos.map((p) => p.codigo).join(" · ")}</p>
            <select id={fProduct.id} value={values.product} onChange={set("product")} aria-invalid={fProduct["aria-invalid"]} aria-describedby={fProduct["aria-describedby"]}>
              <option value="">{t("form.product.choose")}</option>
              {balance.productos.map((p) => <option key={p.codigo} value={p.codigo}>{p.codigo} ({p.nutriente_principal} {p.ley_principal}%)</option>)}
            </select>
            {fProduct.text && <p id={`${fProduct.id}-error`} className="error">{fProduct.text}</p>}
          </div>
          <div className="field">
            <label htmlFor={fDose.id}>{t("form.dose.label")}</label>
            <p id={`${fDose.id}-hint`} className="hint">{t("form.dose.hint")}</p>
            <input id={fDose.id} ref={doseRef} value={values.dose} onChange={set("dose")} inputMode="decimal" autoComplete="off" aria-invalid={fDose["aria-invalid"]} aria-describedby={fDose["aria-describedby"]} />
            {fDose.text && <p id={`${fDose.id}-error`} className="error">{fDose.text}</p>}
          </div>
          <div className="field">
            <label htmlFor={fId.id}>{t("form.id.label")}</label>
            <p id={`${fId.id}-hint`} className="hint">{t("form.id.hint")}</p>
            {/* type=password: the screen faces the worker queue; autocomplete off: shared computer */}
            <input id={fId.id} type="password" name="foreman-badge" value={values.nationalId} onChange={set("nationalId")} inputMode="numeric" autoComplete="off" maxLength={10} aria-invalid={fId["aria-invalid"]} aria-describedby={fId["aria-describedby"]} />
            {fId.text && <p id={`${fId.id}-error`} className="error">{fId.text}</p>}
          </div>
          <button type="submit" className="primary">{t("form.review")}</button>
        </fieldset>
      </form>

      {stage !== "editing" && product && (
        <div className="review" role="group" aria-labelledby="review-title">
          <h3 id="review-title" ref={reviewRef} tabIndex={-1}>{t("review.title")}</h3>
          <p>{t("review.intro")}</p>
          <dl className="facts big">
            <div><dt>{t("review.plot")}</dt><dd>{balance.suerte}</dd></div>
            <div><dt>{t("review.product")}</dt><dd>{product.codigo}</dd></div>
            <div className="highlight"><dt>{t("review.bags")}</dt><dd>{bags}</dd></div>
            <div><dt>{t("review.foreman")}</dt><dd>{maskNationalId(values.nationalId)}</dd></div>
            <div><dt>{t("review.nAdds")}</dt><dd>{formatNumber(nAdds, lang)} kg N/ha</dd></div>
            <div><dt>{t("review.nAfter")}</dt><dd>{formatNumber(balance.n_ciclo_kg_ha + nAdds, lang)} / {balance.limite_n_kg_ha}</dd></div>
          </dl>
          <div className="actions">
            <button type="button" className="primary" onClick={confirm} disabled={stage === "sending"}>
              {stage === "sending" ? t("review.sending") : t("review.confirm")}
            </button>
            <button type="button" onClick={() => setStage("editing")} disabled={stage === "sending"}>{t("review.back")}</button>
          </div>
        </div>
      )}
    </section>
  );
}

export type { Language };
