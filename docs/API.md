# Referencia del API

Contrato base: sección 4.2 del enunciado. Aquí se documentan las respuestas **reales** (capturadas del sistema en ejecución; el historial se recorta a una fila) y las extensiones agregadas. Los nombres de campo están en español porque son el contrato; el código interno está en inglés (ver `GLOSARIO.md`).

- Base: `http://localhost:8088/api/v1` (nginx → API; la API no se publica directamente).
- Autenticación: `Authorization: Bearer <token>` (JWT HS256, 12 h). Emisión de demostración: `make tokens`.
- Idioma de mensajes: cabecera `Accept-Language: es|en` (por defecto `es`). El cliente web envía el idioma activo.
- Todas las respuestas llevan `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`. Cuerpo máximo: 4 KB.
- Los campos de dominio **no** se traducen; solo los textos `mensaje`.

## Resumen
| Método y ruta | Éxito | Errores |
|---|---|---|
| `POST /suertes/{codigo}/despachos` | 201 `Despacho` | 400, 401, 403, 404, 409 (`LIMITE_NITROGENO` / `ORDEN_DUPLICADA`), 413 |
| `GET /suertes/{codigo}/balance-nitrogeno?pagina=N` | 200 `Balance` | 400, 401, 403, 404 |

Extensiones sobre el enunciado (ver `DECISIONES.md`, S7–S8): `401`, `409 ORDEN_DUPLICADA`, `413`, `405`, campo opcional `bultos_confirmados`.

## POST /suertes/{codigo}/despachos
Solo suertes de la bodega de la sesión. Todos los errores de validación se devuelven **juntos**.

| Campo | Regla |
|---|---|
| `orden` | `OF-AAAA-NNNN` |
| `producto` | `URE`, `SAM`, `DAP` o `KCL` |
| `dosis_kg_ha` | número (no texto ni booleano), `0 < d ≤ 200`, un decimal; kg del **nutriente principal** por ha neta |
| `cedula_capataz` | **texto** de 6 a 10 dígitos |
| `bultos_confirmados` | *(opcional)* entero ≥ 1. Si se envía y no coincide con los bultos que calcula el servidor → 400 y **no se registra** |

Los bultos son el entero **más cercano** (mitad hacia arriba) de `dosis · área_neta / (ley_principal · kg_bulto)`.

### 201 Despacho
```json
{
 "id": "aff3c4a4-3005-4f94-945e-13a6f98232b4",
 "orden": "OF-2026-1187", "suerte": "S-104", "producto": "URE",
 "dosis_kg_ha": 80.0, "bultos": 148, "kg_entregados": 7400,
 "n_despacho_kg_ha": 80.09,
 "capataz": "xxxxxx4321", "ventanilla": "NORTE-1", "registrado_por": "B-NORTE-01",
 "registrado_en": "2026-11-23T14:23:06.199121-05:00"
}
```
`capataz` siempre es `xxxxxx` + 4 últimos dígitos (largo fijo). La cédula completa no se devuelve jamás.

### 409 `LIMITE_NITROGENO`
```json
{
 "motivo": "LIMITE_NITROGENO",
 "mensaje": "El despacho supera el límite de nitrógeno del ciclo. Disponible: 34,43 kg N/ha.",
 "n_despacho_kg_ha": 39.86,
 "bultos_maximos": 52,
 "balance": { "suerte": "S-117", "n_ciclo_kg_ha": 125.57, "n_disponible_kg_ha": 34.43, "...": "Balance completo" }
}
```
`bultos_maximos`: bultos de ese producto que aún caben (0 si ninguno; `null` si el producto no aporta N).

### 409 `ORDEN_DUPLICADA`
```json
{ "mensaje": "Esa orden de fertilización ya fue despachada.", "motivo": "ORDEN_DUPLICADA" }
```

### 400
```json
{ "errores": [
  { "campo": "orden", "mensaje": "Use el formato OF-AAAA-NNNN, por ejemplo OF-2026-1187." },
  { "campo": "dosis_kg_ha", "mensaje": "La dosis debe ser mayor que 0 y hasta 200 kg/ha." },
  { "campo": "cedula_capataz", "mensaje": "La cédula debe tener de 6 a 10 dígitos." } ] }
```
Con `Accept-Language: en` y `bultos_confirmados` distinto:
```json
{ "errores": [ { "campo": "bultos_confirmados",
  "mensaje": "Confirmed bags (147) do not match the computed bags (148). Review again." } ] }
```
Otros `campo`: `producto`, `bultos_confirmados`, `pagina`, `_general` (JSON inválido, tipo de contenido, cuerpo no objeto) y el nombre de cualquier campo no permitido. **El mensaje nunca repite el valor enviado** (privacidad de la cédula).

## GET /suertes/{codigo}/balance-nitrogeno?pagina=N
`pagina` entero 1–100000 (por defecto 1); fuera de rango de contenido devuelve `despachos: []`.

```json
{
 "suerte": "S-104", "area_neta_ha": 42.5, "inicio_ciclo": "2026-08-21",
 "limite_n_kg_ha": 160, "n_ciclo_kg_ha": 65.48, "n_disponible_kg_ha": 94.51,
 "productos": [ { "codigo": "URE", "nutriente_principal": "N", "ley_principal": 46, "ley_n": 46, "kg_bulto": 50 }, "... SAM, DAP, KCL" ],
 "historial": { "pagina": 1, "paginas": 1, "despachos": [ { "...": "Despacho, más reciente primero, 50 por página" } ] }
}
```
- `n_ciclo_kg_ha` se redondea al más cercano; `n_disponible_kg_ha` **hacia abajo** (nunca promete de más) y nunca es negativo. Por eso `n_ciclo + n_disponible` puede diferir en 0,01 de 160 (65,48 + 94,51 = 159,99).
- `n_ciclo_kg_ha` se calcula con una agregación sobre **todo** el ciclo, independiente de la página pedida.
- `productos` trae las leyes para que el cliente muestre los bultos antes de confirmar.

## Errores comunes
| Código | Cuándo | Cuerpo |
|---|---|---|
| 401 | Sin token, token vencido, firma inválida o `alg=none` (con `WWW-Authenticate: Bearer`) | `{"mensaje": "Sesión inválida o vencida."}` |
| 403 | Suerte de otra bodega | `{"mensaje": "La suerte no pertenece a la bodega de su sesión."}` |
| 404 | Suerte inexistente o código con formato inválido, o ruta desconocida | `{"mensaje": "La suerte no existe."}` |
| 405 | `PUT/PATCH/DELETE` sobre despachos (la trazabilidad no permite modificarlos) | `{"mensaje": "Método no permitido."}` |
| 413 | Cuerpo > 4 KB | `{"mensaje": "Solicitud demasiado grande."}` |
| 500 | Error inesperado (sin detalles internos) | `{"mensaje": "Error interno."}` |

## Ejemplo completo con curl
```bash
T=$(docker compose run --rm --no-deps -T init flask --app wsgi issue-token B-NORTE-01 | tail -1)
curl -s -XPOST localhost:8088/api/v1/suertes/S-104/despachos \
  -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
  -d '{"orden":"OF-2026-1187","producto":"URE","dosis_kg_ha":80.0,"cedula_capataz":"1113654321","bultos_confirmados":148}'
```
