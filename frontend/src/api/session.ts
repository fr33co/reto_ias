/** Operator data shown in the header (taken from the token's claims, for display only). */
export interface SessionInfo {
  id: string;
  warehouse: string;
  counter: string;
}

/** Reads the token claims ONLY to show them on screen. The server re-validates every request. */
export function readSession(token: string): SessionInfo | null {
  try {
    const payload = token.split(".")[1];
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    if (typeof json.sub !== "string" || typeof json.bodega !== "string" || typeof json.ventanilla !== "string") return null;
    return { id: json.sub, warehouse: json.bodega, counter: json.ventanilla };
  } catch {
    return null;
  }
}
