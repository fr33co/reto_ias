/** Integer arithmetic identical to backend/app/domain/nitrogen.py (the server stays authoritative). */
export interface ProductRule {
  ley_principal: number;
  ley_n: number;
  kg_bulto: number;
}

/** Convert a number with one decimal (e.g. 42.5) to integer tenths (425). */
export const toTenths = (x: number): number => Math.round(x * 10);

/** Nearest CLOSED bag count, half rounds up. */
export function bagsForDose(doseTenths: number, areaTenths: number, p: ProductRule): number {
  const num = doseTenths * areaTenths;
  const den = p.ley_principal * p.kg_bulto;
  return Math.floor((2 * num + den) / (2 * den));
}

/** Nitrogen in grams contained in `bags` bags of the product (exact integer). */
export const nitrogenGrams = (bags: number, p: ProductRule): number => bags * p.kg_bulto * p.ley_n * 10;

/** Convert grams of nitrogen to kg per net hectare (for display). */
export const gramsToKgHa = (grams: number, areaTenths: number): number => grams / (areaTenths * 100);

/** Dose (tenths) that yields exactly `bags` bags, or null if none exists (used after a 409). */
export function doseForBags(bags: number, areaTenths: number, p: ProductRule): number | null {
  if (bags < 1) return null;
  const guess = Math.round((bags * p.ley_principal * p.kg_bulto) / areaTenths);
  for (const d of [guess, guess - 1, guess + 1, guess - 2, guess + 2]) {
    if (d >= 1 && d <= 2000 && bagsForDose(d, areaTenths, p) === bags) return d;
  }
  return null;
}
