/** Same rules as backend/app/api/schemas.py. Errors are translation keys, never raw text. */
export type FieldKey = "orden" | "producto" | "dosis_kg_ha" | "cedula_capataz";
/** A validation problem expressed as a translation key plus parameters (never raw text). */
export interface FieldIssue {
  code: string;
  params?: Record<string, string | number>;
}
/** Raw values of the dispatch form (all strings, as typed). */
export interface FormValues {
  order: string;
  product: string;
  dose: string;
  nationalId: string;
}
export const MAX_DOSE = 200;
export const PRODUCT_CODES = ["URE", "SAM", "DAP", "KCL"];

/** Result of parsing the dose text: the value and its tenths, or the issue. */
export type DoseResult = { ok: true; value: number; tenths: number } | { ok: false; issue: FieldIssue };

/**
 * Parse the dose typed by the user (comma or point as decimal separator).
 *
 * Rules (same as the server): a number, greater than 0, at most 200 and one decimal.
 *
 * @param text - The raw text.
 * @returns The parsed dose, or the issue to show.
 */
export function parseDose(text: string): DoseResult {
  const normalized = text.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(normalized)) return { ok: false, issue: { code: "dose_number" } };
  const value = Number(normalized);
  if (value <= 0 || value > MAX_DOSE) return { ok: false, issue: { code: "dose_range", params: { max: MAX_DOSE } } };
  const tenths = Math.round(value * 10);
  if (Math.abs(value * 10 - tenths) > 1e-9) return { ok: false, issue: { code: "dose_decimals" } };
  return { ok: true, value, tenths };
}

/**
 * Validate the whole form with the server's rules, using the API's field names as keys.
 *
 * @param v - Raw form values.
 * @returns One issue per wrong field (empty object when valid).
 */
export function validateForm(v: FormValues): Partial<Record<FieldKey, FieldIssue>> {
  const errors: Partial<Record<FieldKey, FieldIssue>> = {};
  if (!/^OF-\d{4}-\d{4}$/.test(v.order.trim())) errors.orden = { code: "order_format" };
  if (!PRODUCT_CODES.includes(v.product)) errors.producto = { code: "product_choice", params: { options: PRODUCT_CODES.join(", ") } };
  const dose = parseDose(v.dose);
  if (!dose.ok) errors.dosis_kg_ha = dose.issue;
  if (!/^\d{6,10}$/.test(v.nationalId.trim())) errors.cedula_capataz = { code: "id_format" };
  return errors;
}

export const PLOT_PATTERN = /^S-\d{3}$/;

/** Shows only the last 4 digits (Ley 1581 de 2012), with a fixed-length mask. */
export const maskNationalId = (id: string): string => "xxxxxx" + id.trim().slice(-4);
