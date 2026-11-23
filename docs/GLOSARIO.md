# Glosario español ↔ inglés

El **contrato del API** y los textos de negocio están en español (los fija el enunciado). El **código, los identificadores, docstrings y pruebas** están en inglés. Esta tabla permite pasar de uno al otro.

| Español (contrato / negocio) | Inglés (código) | Dónde aparece |
|---|---|---|
| suerte | plot | `Plot`, tabla `plots`, `PlotORM`, `PlotNotFound` |
| código de suerte (`S-104`) | `plot.code`, `plot_code` | URL `/suertes/{codigo}` |
| bodega (NORTE, SUR) | warehouse | `OperatorSession.warehouse`, `plots.warehouse` |
| ventanilla (NORTE-1, SUR-2) | counter (service window) | `Dispatch.counter`, `OperatorSession.counter` |
| bodeguero | operator / warehouse clerk | `OperatorSession`, `OPERATORS` |
| capataz | foreman | `foreman_last4`, `foreman_encrypted_id` |
| cédula | national id | `national_id`, `NationalIdEncryptor` |
| despacho | dispatch | `Dispatch`, `DispatchORM`, `RegisterDispatch` |
| orden de fertilización (`orden`) | order (`order`, `order_no`) | `DispatchRequest.order`, columna `order_no` (`ORDER` es reservada en SQL) |
| producto | product | `Product`, `PRODUCTS` |
| bulto | bag | `bags`, `bags_for_dose`, `max_bags` |
| bultos máximos | max bags | `NitrogenLimitExceeded.max_bags` |
| dosis (kg/ha) | dose | `dose_kg_ha`; `dose_dkg_ha` = **décimas** de kg/ha |
| área neta / bruta | net / gross area | `net_area_ha`; `net_area_dha` = décimas de ha |
| nitrógeno (N) | nitrogen | `nitrogen.py`; `n_grams` = gramos de N |
| ley del producto | main/N percentage | `main_pct`, `n_pct` |
| nutriente principal | main nutrient | `Product.main_nutrient` |
| ciclo de cultivo | crop cycle | `cycle_start`, `cycle_nitrogen_g` |
| corte / siembra | cut (harvest) / planting | `cycle_origin` (`CORTE`/`SIEMBRA`) |
| límite de nitrógeno | nitrogen limit | `LIMIT_N_KG_HA`, `NitrogenLimitExceeded` |
| balance | balance | `Balance`, `GetBalance`, `balance_json` |
| historial | history | `cycle_page`, `HistoryTable` |
| fertirriego / surcos | fertigation / furrow irrigation | `irrigation` (`FERTIRRIEGO`/`SURCOS`) |
| kárdex | stock ledger (kardex) | solo en documentos |
| anulación | voiding | `GUIA-EXTENSION.md` (`voidings`, `VoidDispatch`) |
| agrónomo | agronomist | rol futuro `AGRONOMIST` |
| sesión | session | `OperatorSession`, `SessionTokens` |

## Unidades internas (importante para leer el código)
| Magnitud | Unidad interna | Ejemplo |
|---|---|---|
| Área neta | décimas de hectárea (`*_dha`) | 42,5 ha → `425` |
| Dosis | décimas de kg/ha (`*_dkg_ha`) | 80,0 kg/ha → `800` |
| Nitrógeno | gramos (`*_g`, `n_grams`) | 3404 kg → `3_404_000` |
| Límite | gramos | 160 kg/ha × 42,5 ha → `6_800_000` |

Los kg/ha de las respuestas se obtienen al final con `Decimal` (`to_kg_ha`). Ver `MODELO-DE-DATOS.md`.

## Nombres del contrato que no se traducen
`orden`, `producto`, `dosis_kg_ha`, `cedula_capataz`, `bultos_confirmados`, `bultos`, `kg_entregados`, `n_despacho_kg_ha`, `capataz`, `ventanilla`, `registrado_por`, `registrado_en`, `area_neta_ha`, `inicio_ciclo`, `limite_n_kg_ha`, `n_ciclo_kg_ha`, `n_disponible_kg_ha`, `productos`, `historial`, `pagina(s)`, `despachos`, `errores`, `campo`, `mensaje`, `motivo` (`LIMITE_NITROGENO`, `ORDEN_DUPLICADA`), `bultos_maximos`, `balance`. Se convierten en el borde (`api/schemas.py` y `api/serializers.py`).
