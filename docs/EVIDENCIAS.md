# Evidencias de verificación

Salidas reales de la ejecución desde cero (`docker compose down -v` + `make test` + `make perf`) el **2026-11-23**. Se pueden reproducir con los mismos comandos.

## Entorno de medición
| Elemento | Valor |
|---|---|
| Equipo | Intel Core i7-3537U @ 2,00 GHz (2 núcleos/4 hilos), 11 GiB RAM |
| SO / Docker | Linux 6.8, Docker 29.10, Compose v5.8 |
| Motor | PostgreSQL 16 (contenedor), Python 3.12, Node 20 |
| Tiempo total de `make test` | ≈ 34 s (incluye construir imágenes en caché) |

## 1. `make test`
```
$ make test
49 passed, 1 deselected in 5.84s            ← servidor (pytest, PostgreSQL real)
 Test Files  2 passed (2)
      Tests  42 passed (42)                  ← cliente (vitest + axe)
```
(La prueba "deselected" es la de rendimiento, que se ejecuta aparte con `make perf`.)

### Servidor: 49 pruebas por archivo
| Archivo | Pruebas | Demuestra |
|---|---:|---|
| `test_example_orders.py` | 3 | Las 6 órdenes en su orden; ciclo lleno; balance S-104 = auditoría |
| `test_incident_regression.py` | 3 | Suma de todo el ciclo (104 filas); páginas de 50; límite con >50 filas |
| `test_validation_and_access.py` | 33 | 400 por campo, bordes, 401/403/404/413, tokens, duplicados, idioma, separador decimal |
| `test_cycle_and_arithmetic.py` | 2 | Aritmética entera; borde del día del corte |
| `test_security_and_traceability.py` | 6 | Cédula cifrada/ausente de respuestas y logs; inmutabilidad; 405 |
| `test_concurrency.py` | 1 | 6 hilos SUR-1/SUR-2: exactamente un 201 |
| `test_documentation.py` | 1 | Todo módulo, clase, función y método del servidor tiene docstring |
| `test_performance.py` | 1 | (aparte) p95 con 60.000 despachos |

### Cliente: 42 pruebas
- `domain.test.ts` (24): mismos vectores de bultos que el servidor (148, 70, 61, 52, 194, 21), `doseForBags`, `parseDose`, `validateForm`, máscara.
- `App.test.tsx` (18): flujo completo, 409 con ajuste de dosis, resumen de errores, Enter del lector, sin almacenamiento, 401/403/404, inactividad, idiomas, y **5 verificaciones axe** (WCAG 2.2 A/AA).

## 2. `make perf`
```
$ make perf
GET  p95=15.2 ms (target 200)   POST p95=13.4 ms (target 300)
1 passed, 48 deselected in 11.61s
```
Datos: 60.000 despachos (150 suertes × 400, todos dentro del ciclo), 300 GET (8 páginas de historial cada uno) y 300 POST (201, cada uno suma 400 filas). Mediciones previas en la misma máquina: 17,8 / 16,2 ms y 15,2 / 13,4 ms (variación normal).

**Margen:** 13× en GET y 22× en POST. **Límite:** medido en proceso (cliente de pruebas de Flask), un solo hilo, sin red ni nginx.

## 3. Prueba de humo del despliegue (Compose)
Con `docker compose up`: `db` healthy → `init` termina con código 0 → `api` y `web` arriba. Comprobado vía nginx (<http://localhost:8088>):
| Comprobación | Resultado |
|---|---|
| `GET /api/v1/suertes/S-208/balance-nitrogeno` (SUR) | `n_ciclo_kg_ha 98.44`, `n_disponible 61.56`, 3 páginas |
| `POST OF-2026-1196` (KCL 120) | 201, 194 bultos, `capataz: xxxxxx3845` |
| `GET S-104` con token de SUR | 403 |
| Cabeceras de `/` | CSP, `X-Content-Type-Options`, sin versión de nginx |
| Cédula en `docker compose logs api` | 0 apariciones |
| Respuesta de `GET /api/v1/...` sin token | 401 |

## 4. Verificación de la guía de extensión
La guía (`GUIA-EXTENSION.md`) se ejecutó en una copia del proyecto: anulación completa en servidor y cliente.
| Resultado | Valor |
|---|---|
| Servidor | 55 pruebas verdes (49 + 6 nuevas de anulación) |
| Cliente | 47 verdes (42 + 5 nuevas del diálogo, incluida axe) |
| Rendimiento con la agregación ampliada (JOIN) | GET 17,8 ms · POST 14,3 ms |
| Errores que aparecieron y ya están corregidos en la guía | 6 (área neta en `get`, bultos anulados en el historial, rol sin bodega, JSON roto, fixture del cliente, `role="group"` en `<form>`) |

## 5. Cómo reproducir
```bash
docker compose down -v && make up   # estado limpio
make test                            # 49 + 42 pruebas
make perf                            # p95
```

## 6. Lo que estas evidencias NO cubren
Lector de código de barras físico, Edge/Chrome/Firefox reales, lector de pantalla, contraste medido en navegador, carga concurrente por HTTP, y restauración de respaldos (ver `DECISIONES.md` y `RIESGOS.md`).
