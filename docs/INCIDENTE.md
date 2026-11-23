# INCIDENTE — S-305 con 198,81 kg N/ha sin que la v1 rechazara un solo despacho

## Resumen
La v1 calculaba el nitrógeno del ciclo **sumando las filas que devolvía la consulta paginada del historial** (50 filas por página). Con fertirriego (2 despachos/día) la suerte S-305 superó las 50 filas, la suma dejó de crecer y la v1 creyó que había ~61 kg N/ha usados cuando el kárdex marcaba 198,81.

**Capa:** servidor (lógica de aplicación / acceso a datos). La pantalla solo mostró fielmente el valor equivocado que le dio la API.

## Línea de tiempo con evidencia
| Fecha | Registro | Lectura |
|---|---|---|
| 08-03 | despliegue 1.4.0 `pruebas=datos_bodega_NORTE` | Se habilitó fertirriego en SUR probando solo con datos de NORTE (3 a 6 despachos por ciclo, nunca >50 filas). |
| 09-16/17 | `n_ciclo_leido=0 → 48.49 → 67.67`, `filas_leidas=0,1,2` | Mientras hay pocas filas la suma es correcta. |
| 09-22 | S-109: 409 `LIMITE_N` con `filas_leidas=4` | La regla **sí funcionaba** con pocas filas: por eso nadie sospechó. |
| 09-30 → 10-11 | `filas_leidas=29, 44, 50`; `n_ciclo_leido=100.76, 119.15, 126.50` | La suma crece hasta que las filas llegan a **50 = tamaño de página**. |
| 10-11 06:30 → 14:30 | `filas_leidas=50`, `n_ciclo_leido=126.50 → 79.24 → 61.28` | El valor **baja** aunque se despacha más: la v1 solo ve una ventana de las 50 filas más recientes. |
| 10-12 → 11-09 | `filas_leidas=50`, `n_ciclo_leido=61.28` constante | 50 × 1,2256 = 61,28: la suma de 50 despachos de 3 bultos. Ya no cambia nunca. |
| 10-14, 11-06, 11-09 | pantalla `n_ciclo=61.28 disponible=98.72`, `historial_pagina=1/2 → 1/3` | El historial crece a 3 páginas (>100 filas) y el N sigue en 61,28. |
| 11-09 | auditoría `n_ciclo_kardex=198.81 EXCEDE` | Realidad según kárdex. |

El N real que se perdió de vista: 198,81 − 61,28 ≈ **137,5 kg N/ha** (≈ 107 despachos de urea invisibles). El límite de 160 se cruzó hacia el 25 de octubre (67,67 + 1,2256·n = 160 → n ≈ 75 despachos desde el 17-09).

## Hipótesis y por qué se descartan
| Hipótesis | Quién | Veredicto | Evidencia |
|---|---|---|---|
| La Bodega Sur entregó bultos sin registrarlos | Jefe de campo | **Descartada (evidencia parcial)** | `CONCILIACION kardex bodega=SUR 2026-10 salidas=3184 registrados=3184 diferencia=0` (y NORTE =0). La conciliación solo cubre **octubre**; no hay registros para septiembre ni para noviembre, así que la evidencia directa es parcial. Lo que refuerza el descarte: el patrón de `filas_leidas=50` con `n_ciclo_leido=61.28` constante se explica por completo por la paginación (50 × 1,2256 = 61,28) sin necesitar bultos sin registrar. Para cerrarla del todo habría que conciliar septiembre y noviembre contra el kárdex. |
| La pantalla siempre mostró disponible | Bodeguero SUR-1 | **Parcial: síntoma, no causa** | Sí mostró disponible (98,72) pero no "siempre": ese valor es exactamente 160 − 61,28, es decir, lo que calculó la API. La pantalla reflejó bien un dato mal calculado (y el bodeguero no podía saberlo). |
| No hubo errores | Infraestructura | **Cierta pero irrelevante** | `errores_5xx=0`, p95_post 44 ms. Es un error lógico silencioso: el sistema respondía 201 correctamente… a la pregunta equivocada. Ninguna alarma de disponibilidad lo detecta. |
| Usar decimales exactos | Desarrollo | **Descartada como causa** | El redondeo por despacho (1,23 vs 1,2256) suma ≈ 0,5 kg N/ha en 107 despachos; no explica 137 kg. (Igual se adoptó aritmética entera por buena práctica.) |

## Causa raíz
Se **reutilizó la consulta de presentación (paginada a 50) como fuente de verdad de una regla de negocio**. La regla "N del ciclo + N del despacho ≤ límite" debía calcularse con una agregación sobre *todo* el ciclo, no con las filas de una página.

Factores que lo dejaron pasar: (1) no había prueba con más de 50 filas en un ciclo; (2) las pruebas del cambio de fertirriego usaron datos de NORTE; (3) la v1 registraba `filas_leidas` pero nadie lo vigilaba (50 constante = alarma); (4) no existía una conciliación automática N-registrado vs kárdex.

## Cómo lo evita este corte
| Medida | Dónde |
|---|---|
| El N del ciclo sale de `SELECT SUM(n_grams) … WHERE plot = :p AND local_date >= :cycle_start`, independiente de cualquier paginación; el historial es solo presentación | `SqlDispatchRepository.cycle_nitrogen_g`, `use_cases._build_balance` |
| Un índice con `INCLUDE (n_grams)` hace la suma barata (p95 ≈ 16 ms con 60.000 despachos y 400 por ciclo), así que no hay incentivo a "ahorrar" la consulta | `orm.py` índice `dispatches_plot_date`, `tests/test_performance.py` |
| Aritmética entera (gramos y décimas): el límite se decide sin redondeo | `domain/nitrogen.py` |
| Bloqueo `SELECT … FOR UPDATE` de la suerte: dos ventanillas no se pisan | `SqlPlotRepository.get(lock=True)` |
| Pruebas de regresión: S-208 con 104 filas (3 páginas) suma todo; el límite se aplica con >50 filas; el historial pagina de 50 en 50 | `tests/test_incident_regression.py` |
| Las 6 órdenes de ejemplo, incluido el borde exacto de 160,00 | `tests/test_example_orders.py` |

## Acciones recomendadas (fuera del corte)
Alarma si `filas_leidas == tamaño de página` en cualquier regla; conciliación nocturna N-registrado vs kárdex por suerte; incluir al menos un caso de fertirriego (>50 filas) en toda prueba de regresión de despliegue; regularizar S-305 y las demás suertes de fertirriego de SUR con el agrónomo (hoy están por encima del límite y deberán anularse bultos o autorizar excepción).
