/** Wire types: the property names are the API contract (Spanish, fixed by the brief). */
export interface ProductDto {
  codigo: string;
  nutriente_principal: "N" | "P2O5" | "K2O";
  ley_principal: number;
  ley_n: number;
  kg_bulto: number;
}

/** A dispatch as returned by the API. The foreman's id arrives already masked (`xxxxxx4321`). */
export interface DispatchDto {
  id: string;
  orden: string;
  suerte: string;
  producto: string;
  dosis_kg_ha: number;
  bultos: number;
  kg_entregados: number;
  n_despacho_kg_ha: number;
  capataz: string;
  ventanilla: string;
  registrado_por: string;
  registrado_en: string;
}

/** Nitrogen balance of a plot with the product rules (needed to compute bags) and one history page. */
export interface BalanceDto {
  suerte: string;
  area_neta_ha: number;
  inicio_ciclo: string;
  limite_n_kg_ha: number;
  n_ciclo_kg_ha: number;
  n_disponible_kg_ha: number;
  productos: ProductDto[];
  historial: { pagina: number; paginas: number; despachos: DispatchDto[] };
}

/** Body of `POST /suertes/{plot}/despachos`. `bultos_confirmados` makes the server reject the request if its bag count differs from the one shown on screen. */
export interface DispatchBody {
  orden: string;
  producto: string;
  dosis_kg_ha: number;
  cedula_capataz: string;
  bultos_confirmados: number;
}

/** One validation error returned by the API: the field name and a message already in the UI language. */
export interface FieldErrorDto {
  campo: string;
  mensaje: string;
}
