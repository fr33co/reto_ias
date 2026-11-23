import { render } from "@testing-library/react";
import { App } from "../App";
import type { BalanceDto, DispatchDto } from "../api/types";
import { I18nProvider, type Language } from "../i18n";

const b64 = (o: object) => btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
/** Fake session token (unsigned) whose payload carries NORTE / NORTE-1, enough for the client to display it. */
export const TOKEN = `${b64({ alg: "HS256" })}.${b64({ sub: "B-NORTE-01", bodega: "NORTE", ventanilla: "NORTE-1" })}.sig`;

/** Product rules as the API returns them in the balance. */
export const PRODUCTS = [
  { codigo: "URE", nutriente_principal: "N", ley_principal: 46, ley_n: 46, kg_bulto: 50 },
  { codigo: "SAM", nutriente_principal: "N", ley_principal: 21, ley_n: 21, kg_bulto: 50 },
  { codigo: "DAP", nutriente_principal: "P2O5", ley_principal: 46, ley_n: 18, kg_bulto: 50 },
  { codigo: "KCL", nutriente_principal: "K2O", ley_principal: 60, ley_n: 0, kg_bulto: 50 },
] as const;

/** Build a dispatch fixture; pass overrides for the fields a test cares about. */
export const dispatch = (over: Partial<DispatchDto> = {}): DispatchDto => ({
  id: "1", orden: "OF-2026-0002", suerte: "S-117", producto: "URE", dosis_kg_ha: 71.9, bultos: 110, kg_entregados: 5500,
  n_despacho_kg_ha: 71.88, capataz: "xxxxxx0001", ventanilla: "NORTE-1", registrado_por: "B-NORTE-01",
  registrado_en: "2026-09-15T08:00:00-05:00", ...over,
});

/** Build a balance fixture (S-117, 107.68 of 160 used); pass overrides as needed. */
export const balance = (over: Partial<BalanceDto> = {}): BalanceDto => ({
  suerte: "S-117", area_neta_ha: 35.2, inicio_ciclo: "2026-06-30", limite_n_kg_ha: 160, n_ciclo_kg_ha: 107.68, n_disponible_kg_ha: 52.32,
  productos: [...PRODUCTS] as BalanceDto["productos"],
  historial: { pagina: 1, paginas: 1, despachos: [dispatch(), dispatch({ id: "2", orden: "OF-2026-0001", producto: "SAM", capataz: "xxxxxx4321" })] },
  ...over,
});

/** Decides the mocked HTTP response (status and JSON body) for a request. */
export type Handler = (url: string, init?: RequestInit) => { status: number; body: unknown };

/** Replaces fetch; returns the recorded calls so tests can assert what was sent. */
export function mockFetch(handler: Handler) {
  const calls: { url: string; init?: RequestInit }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    const { status, body } = handler(url, init);
    return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
  }));
  return calls;
}

/**
 * Render the app inside the i18n provider.
 *
 * @param lang - Initial UI language.
 * @param idleMs - Inactivity limit; tests pass a small value to exercise the auto sign-out.
 */
export function renderApp(lang: Language = "es", idleMs?: number) {
  return render(<I18nProvider initial={lang}><App idleMs={idleMs} /></I18nProvider>);
}
