import type { BalanceDto, DispatchBody, DispatchDto, FieldErrorDto } from "./types";

/** Outcome of a balance request (discriminated by `kind`). */
export type BalanceResult =
  | { kind: "ok"; balance: BalanceDto }
  | { kind: "unauthorized" | "forbidden" | "not_found" | "network" | "error"; message?: string };

/**
 * Outcome of registering a dispatch. `limit` is the 409 for the nitrogen limit and carries
 * the maximum bags that fit plus the refreshed balance; `invalid` carries per-field errors.
 */
export type DispatchResult =
  | { kind: "created"; dispatch: DispatchDto }
  | { kind: "limit"; message: string; maxBags: number | null; nDispatch: number; balance: BalanceDto }
  | { kind: "duplicate_order"; message: string }
  | { kind: "invalid"; errors: FieldErrorDto[] }
  | { kind: "unauthorized" | "forbidden" | "not_found" | "network" | "error"; message?: string };

/** Typed access to the two API endpoints. Network failures never throw: they return `kind: "network"`. */
export interface ApiClient {
  getBalance(plot: string, page?: number): Promise<BalanceResult>;
  registerDispatch(plot: string, body: DispatchBody): Promise<DispatchResult>;
}

/**
 * The token lives only in memory (closure): never localStorage/sessionStorage/cookies,
 * because the workstation is shared by three shifts.
 */
export function createApiClient(getToken: () => string | null, getLanguage: () => string, baseUrl = ""): ApiClient {
  /**
   * Perform an authenticated request: no cache, no cookies, no referrer, with the token and UI language.
   *
   * @param path - Path under the API base URL.
   * @param init - Extra `fetch` options (method, body).
   */
  async function call(path: string, init: RequestInit = {}) {
    return fetch(baseUrl + path, {
      ...init,
      cache: "no-store",
      credentials: "omit",
      referrerPolicy: "no-referrer",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": getLanguage(),
        Authorization: `Bearer ${getToken() ?? ""}`,
      },
    });
  }
  /** Map the status codes shared by every endpoint (401, 403, 404) to a result kind; anything else is `error`. */
  const common = (status: number) =>
    status === 401 ? "unauthorized" : status === 403 ? "forbidden" : status === 404 ? "not_found" : "error";

  return {
    /**
     * `GET /suertes/{plot}/balance-nitrogeno`.
     *
     * @param plot - Plot code.
     * @param page - 1-based history page.
     */
    async getBalance(plot, page = 1) {
      try {
        const r = await call(`/api/v1/suertes/${encodeURIComponent(plot)}/balance-nitrogeno?pagina=${page}`);
        if (r.ok) return { kind: "ok", balance: (await r.json()) as BalanceDto };
        return { kind: common(r.status) } as BalanceResult;
      } catch {
        return { kind: "network" };
      }
    },
    /**
     * `POST /suertes/{plot}/despachos`.
     *
     * @param plot - Plot code.
     * @param body - The dispatch, including `bultos_confirmados` (the bags shown on the confirmation screen).
     */
    async registerDispatch(plot, body) {
      try {
        const r = await call(`/api/v1/suertes/${encodeURIComponent(plot)}/despachos`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        if (r.status === 201) return { kind: "created", dispatch: (await r.json()) as DispatchDto };
        const data = await r.json().catch(() => ({}));
        if (r.status === 400) return { kind: "invalid", errors: data.errores ?? [] };
        if (r.status === 409 && data.motivo === "LIMITE_NITROGENO")
          return { kind: "limit", message: data.mensaje, maxBags: data.bultos_maximos, nDispatch: data.n_despacho_kg_ha, balance: data.balance };
        if (r.status === 409) return { kind: "duplicate_order", message: data.mensaje };
        return { kind: common(r.status), message: data.mensaje } as DispatchResult;
      } catch {
        return { kind: "network" };
      }
    },
  };
}
