# Registro de decisiones — DS-FS-20261120-ykgp
Inicio: 23/11/2026 13:40 · Fin de la Parte 1: 23/11/2026 14:41 · Fin: 15:20


## Supuestos
| # | Supuesto | Por qué lo asumí | Qué cambiaría si es falso |
|---|---|---|---|
| S1 | Los bultos se calculan al **entero más cercano** (mitad hacia arriba) a partir de la dosis | "Solo bultos cerrados"; minimiza el error agronómico en ambos sentidos | Con "hacia arriba", OF-1195 (43,7 → 53 bultos) pasaría a 409; se cambia una función (`bags_for_dose`) y sus pruebas |
| S2 | El límite es inclusivo: N total **≤ 160** se acepta (OF-1198 queda en 160,00 exacto) | "Un despacho que haría **superar** el límite no se entrega" | Cambiar `<=` por `<` en `fits_limit` |
| S3 | Un despacho sin nitrógeno (KCL) se entrega aunque la suerte ya esté en el límite | No puede "hacer superar" nada; OF-1196 lo requiere para S-208 | Quitar la excepción `dispatch_n_g == 0` |
| S4 | Una orden se despacha una sola vez (`orden` única, 409 `ORDEN_DUPLICADA`) | Evita doble despacho por reintento/doble clic | Modelar líneas/saldo de orden para entregas parciales |
| S5 | El ciclo es el actual de la suerte (`cycle_start`); cuenta `local_date >= cycle_start` (día en America/Bogota) | Glosario: "fecha de ese día o posterior" | Tabla `cycles` si hay que auditar ciclos pasados |
| S6 | "Elige una suerte" se resuelve **digitando el código** | El contrato no tiene endpoint de listado y no se esperan más endpoints | Añadir `GET /suertes` y cambiar a lista/combobox |
| S7 | Los 401 (sesión inválida) y 413/405 son respuestas adicionales válidas | Un contrato con Bearer implica 401 | — |
| S8 | `bultos_confirmados` es un campo **opcional** adicional en el cuerpo | Garantiza "lo que se registra es lo que se carga" sin romper el contrato | Si se prohíben campos extra, se valida en el cliente solamente (más débil) |
| S9 | `n_disponible_kg_ha` nunca es negativo y se redondea hacia abajo | No prometer más de lo real | Mostrar negativo si el agrónomo quiere ver el exceso |
| S10 | Las 62 suertes no se cargan: solo las 6 de ejemplo | "Estos son los únicos insumos" | Seed adicional |

## Decisiones

### D-01 Stack: Flask + SQLAlchemy 2 + PostgreSQL / React + TypeScript + Vite
- **Tema:** stack
- **Contexto:** Se pide Flask y React, desplegable con Docker Compose, concurrencia estricta entre ventanillas y p95 bajos.
- **Alternativas:** (a) SQLite: trivial, pero sin `SELECT … FOR UPDATE` por fila y con escritura serializada global. (b) PostgreSQL: bloqueo por fila, índices cubrientes, restricciones `CHECK`, triggers. (c) FastAPI: no pedido.
- **Decisión:** PostgreSQL 16 + SQLAlchemy 2 (ORM declarativo) + psycopg 3; React 18 + TS estricto + Vite.
- **Por qué:** La concurrencia entre SUR-1 y SUR-2 es un requisito duro; solo un motor con bloqueo de fila lo resuelve bien.
- **Consecuencias:** Las pruebas necesitan PostgreSQL (se levanta en compose). Más pesado que SQLite, pero igual a producción.
- **Dónde se ve:** `docker-compose.yml`, `backend/requirements.txt`, `frontend/package.json`.

### D-02 Arquitectura por capas con inversión de dependencias (SOLID)
- **Tema:** arquitectura
- **Contexto:** El incidente nació de mezclar la consulta de presentación con la regla de negocio.
- **Alternativas:** (a) Lógica en las rutas Flask (rápido, intestable sin HTTP+BD). (b) Capas dominio/aplicación/infraestructura/API con puertos `Protocol`.
- **Decisión:** (b). `domain` puro; `application` (casos de uso) depende de `ports.py`; `infrastructure` implementa; `__init__.create_app` es la única raíz de composición.
- **Por qué:** S (cada módulo una razón de cambio), O (nuevo caso de uso sin tocar los existentes), L/I (puertos pequeños), D (el caso de uso no conoce SQLAlchemy, Fernet ni JWT).
- **Consecuencias:** Más archivos que un script único; a cambio, la regla de límite se prueba sin red y la anulación se añade sin tocar el registro.
- **Dónde se ve:** `backend/app/{domain,application,infrastructure,api}`.

### D-03 Aritmética entera para el límite
- **Tema:** datos
- **Contexto:** Desarrollo propuso "decimales exactos". OF-1198 cae exactamente en 160,00.
- **Alternativas:** (a) `float`: error binario en el borde. (b) `Decimal` en todo. (c) Enteros: área y dosis en décimas, nitrógeno en gramos.
- **Decisión:** (c); `Decimal` solo para presentar kg/ha.
- **Por qué:** Es exacto, rápido y la comparación `≤` es entre enteros; el borde de 160,00 no depende del redondeo.
- **Consecuencias:** Hay que recordar las unidades (documentadas en `nitrogen.py`); el JSON de salida convierte a número con 2 decimales.
- **Dónde se ve:** `domain/nitrogen.py`, `test_cycle_and_arithmetic.py`.

### D-04 El N del ciclo se calcula con una agregación SQL, nunca desde el historial
- **Tema:** arquitectura / datos
- **Contexto:** Causa raíz del incidente (ver `INCIDENTE.md`).
- **Alternativas:** (a) Sumar filas paginadas (v1). (b) Sumar todas las filas en Python (traer 400+ filas por POST). (c) `SUM(n_grams)` en la BD con índice cubriente. (d) Columna acumulada materializada.
- **Decisión:** (c).
- **Por qué:** Correcto por construcción y barato: p95 ≈ 16 ms con 60.000 filas. (d) añade un segundo dato que puede desincronizarse.
- **Consecuencias:** Una lectura por POST; si el volumen creciera mucho se evalúa (d) con trigger.
- **Dónde se ve:** `SqlDispatchRepository.cycle_nitrogen_g`, índice `dispatches_plot_date`.

### D-05 Concurrencia: `SELECT … FOR UPDATE` sobre la suerte
- **Tema:** arquitectura
- **Contexto:** Las dos ventanillas de SUR nunca deben superar el límite juntas.
- **Alternativas:** (a) Aislamiento SERIALIZABLE con reintentos (complejo y propenso a fallos visibles). (b) Restricción en BD (no expresable como CHECK de agregado). (c) Bloqueo pesimista de la fila de la suerte. (d) Lock en memoria (no sirve con 3 workers).
- **Decisión:** (c).
- **Por qué:** Serializa solo los despachos de la **misma suerte**; el resto sigue en paralelo.
- **Consecuencias:** Una espera corta bajo contención; impacto despreciable con ~140 despachos/semana en SUR.
- **Dónde se ve:** `SqlPlotRepository.get(lock=True)`, `tests/test_concurrency.py` (6 hilos → exactamente un 201).

### D-06 Lecturas con instantánea REPEATABLE READ de solo lectura
- **Tema:** datos
- **Contexto:** El balance hace SUM + COUNT + página; no deben mezclar estados.
- **Alternativas:** READ COMMITTED (puede mezclar si entra un despacho en medio) vs REPEATABLE READ read-only.
- **Decisión:** REPEATABLE READ en `GET`.
- **Por qué:** Total, número de páginas y filas coherentes entre sí sin bloquear a nadie.
- **Dónde se ve:** `uow_factory`.

### D-07 Redondeo de bultos al más cercano y confirmación `bultos_confirmados`
- **Tema:** diseño
- **Contexto:** La dosis se da en kg de nutriente/ha; la bodega entrega bultos cerrados; "lo que se registra es lo que se carga".
- **Alternativas:** hacia arriba (garantiza dosis mínima, pero sobre-aplica hasta un bulto); hacia abajo (nunca excede la orden, puede quedar corto); más cercano.
- **Decisión:** más cercano; el cliente calcula y muestra los bultos, y el POST incluye `bultos_confirmados`; si el servidor calcula otro número, 400 y no registra.
- **Por qué:** Minimiza el error agronómico y evita que las dos capas diverjan sin que nadie lo note.
- **Consecuencias:** Duplicación deliberada de una función de 3 líneas, protegida con los mismos vectores de prueba (`bags_for_dose` / `bagsForDose`).
- **Dónde se ve:** `domain/nitrogen.py`, `frontend/src/domain/bags.ts`, tests de ambos lados.

### D-08 Cédula: cifrada en reposo + 4 últimos dígitos
- **Tema:** seguridad (Ley 1581)
- **Alternativas:** (a) texto plano; (b) hash (no recuperable: no sirve si hay que identificar al capataz ante una auditoría); (c) cifrado simétrico con llave fuera de la BD; (d) solo los 4 últimos (no cumple "se guarda").
- **Decisión:** (c) Fernet (MultiFernet para rotar) en `foreman_encrypted_id` + `foreman_last4` para mostrar.
- **Por qué:** Cumple "se guarda" y limita el daño de un volcado de BD. Máscara de largo fijo `xxxxxx1234` para no revelar la longitud.
- **Consecuencias:** La llave vive en variable de entorno (demo); en producción, KMS.
- **Dónde se ve:** `NationalIdEncryptor`, `serializers.masked_foreman`, `test_security_and_traceability.py`.

### D-09 Cédula fuera de logs y de errores
- **Tema:** seguridad
- **Decisión:** el log de acceso solo registra método, ruta, estado, duración y sesión (nunca cuerpo); además un `logging.Filter` enmascara cualquier secuencia de 6–10 dígitos; los mensajes de error 400 no repiten el valor.
- **Por qué:** Defensa en profundidad: si alguien añade un `log.info(request.json)`, el filtro lo atrapa.
- **Dónde se ve:** `PersonalDataFilter`, tests de logs.

### D-10 Cliente: nada sensible en el navegador
- **Tema:** seguridad
- **Contexto:** Computador compartido por tres turnos con la pantalla hacia la fila.
- **Decisión:** token y cédula solo en estado/memoria de React (sin `localStorage`, cookies ni URL); campo cédula `type=password` + `autocomplete=off`; borrado al registrar, al cerrar sesión y tras 10 min sin actividad; `Cache-Control: no-store`; CSP estricta en nginx.
- **Alternativas:** `localStorage` para comodidad (descartado: persiste entre turnos); campo de texto con CSS que oculta (no funciona igual en Firefox).
- **Dónde se ve:** `App.tsx`, `useIdleTimeout.ts`, `nginx.conf`, pruebas de almacenamiento.

### D-11 Lector de código de barras: Enter abre la revisión
- **Tema:** diseño
- **Decisión:** el Enter del lector envía el formulario, que solo **abre la confirmación**; registrar exige el botón "Confirmar y registrar". Evita despachos por un Enter accidental.
- **Dónde se ve:** `DispatchForm.review`, prueba "scanner's Enter".

### D-12 Sesión simulada con JWT HS256 y emisión por CLI
- **Tema:** seguridad
- **Contexto:** El contrato no tiene login; hay que simular sesión y explicar la integración corporativa.
- **Alternativas:** tabla de sesiones; tokens estáticos; JWT firmado.
- **Decisión:** JWT firmado (`sub`, `bodega`, `ventanilla`, `iss`, `exp`) emitido con `flask issue-token`; la API valida firma, emisor y expiración.
- **Integración real:** un IdP corporativo (OIDC/Azure AD/Keycloak) emite el token; la API valida con JWKS (RS256) y toma `bodega`/`ventanilla` de claims o grupos; mismo decorador `requires_session`, solo cambia `SessionTokens.verify`. La pantalla de ingreso se reemplaza por el redireccionamiento OIDC.
- **Consecuencias:** sin revocación (aceptable en demo); expira a las 12 h.
- **Dónde se ve:** `infrastructure/services.py`, `api/routes.py`.

### D-13 Control de acceso por bodega en el caso de uso
- **Tema:** seguridad
- **Decisión:** `_authorize` compara la bodega de la suerte con la de la sesión **en el caso de uso** (404 si no existe, 403 si es de otra bodega), para que ninguna ruta futura se olvide de comprobarlo.
- **Dónde se ve:** `use_cases._authorize`, prueba 403/404/401.

### D-14 Integridad en la BD: restricciones y trigger de inmutabilidad
- **Tema:** datos
- **Decisión:** `CHECK` (formato de orden, rangos de dosis, producto), `UNIQUE(order_no)` y trigger que rechaza `UPDATE`/`DELETE` en `dispatches`; la API ni siquiera expone `PUT/PATCH/DELETE` (405).
- **Por qué:** "Los despachos no se modifican ni se eliminan": se garantiza aunque alguien con acceso a la BD o un futuro bug lo intente.
- **Dónde se ve:** `orm.py`, `db.py`, prueba de inmutabilidad.

### D-15 Validación coherente cliente/servidor
- **Tema:** diseño
- **Decisión:** mismas reglas y mismos nombres de campo (`orden`, `producto`, `dosis_kg_ha`, `cedula_capataz`) en `api/schemas.py` y `domain/validation.ts`; el servidor acumula todos los errores en un solo 400 `{errores:[{campo,mensaje}]}`; el cliente mapea cada uno a su campo. JSON parseado con `parse_float=Decimal` para que 43,7 llegue exacto.
- **Alternativas:** una librería de esquemas compartida (más acoplamiento y dependencias para 4 campos).
- **Dónde se ve:** `schemas.py`, `validation.ts`, pruebas parametrizadas.

### D-16 Internacionalización es/en
- **Tema:** diseño
- **Decisión:** código, identificadores, docstrings y pruebas en inglés; textos al usuario en diccionarios es/en (cliente: `i18n/`, servidor: `api/i18n.py` según `Accept-Language`, por defecto es). Los nombres del contrato (`orden`, `LIMITE_NITROGENO`…) no se traducen.
- **Alternativas:** i18next/Flask-Babel (más peso para ~60 cadenas).
- **Dónde se ve:** `frontend/src/i18n`, `backend/app/api/i18n.py`, pruebas de idioma.

### D-17 Accesibilidad WCAG 2.2 AA
- **Tema:** diseño
- **Decisión:** etiquetas visibles, ayudas y errores enlazados con `aria-describedby`/`aria-invalid`; resumen de errores con foco; foco gestionado en revisión/límite/éxito; objetivos ≥ 44 px; foco visible de alto contraste; sin reintroducir datos tras un 409 (3.3.7); `lang`, "saltar al contenido", tabla con `caption`/`scope`; diseño usable a 1366×768 y sin scroll horizontal en estrecho.
- **Verificación:** `jest-axe` con etiquetas wcag2a/2aa/21aa/22aa en 5 estados de pantalla.
- **Limitación:** axe en jsdom no mide contraste real ni lector de pantalla.

### D-18 Rendimiento: índice cubriente y medición
- **Tema:** rendimiento
- **Decisión:** índice `(plot, local_date DESC, registered_at DESC, id) INCLUDE (n_grams)`; pool de 5+5 conexiones; 3 workers de gunicorn. Medido con 60.000 despachos y 400 por ciclo: **GET p95 ≈ 17,8 ms, POST p95 ≈ 16,2 ms** (objetivos 200/300 ms).
- **Limitación:** medido en proceso (cliente de pruebas de Flask) sin latencia de red ni nginx.
- **Dónde se ve:** `tests/test_performance.py` (`make perf`).

### D-19 Docker Compose endurecido
- **Tema:** operación
- **Decisión:** BD sin puerto publicado; API solo alcanzable vía nginx; contenedores no root, `read_only`, `cap_drop: ALL`, `no-new-privileges`; secretos generados por `scripts/setup.sh` (`.env` fuera de git); `init` aplica esquema y datos de ejemplo una sola vez.
- **Alternativas:** publicar la API directamente (expone superficie; obliga a CORS).

### D-20 Pruebas con PostgreSQL real, no con mocks
- **Tema:** pruebas
- **Decisión:** pytest contra una BD `reto_test` en el mismo Postgres de compose; reinicia al estado del enunciado antes de cada prueba. Cubre las 6 órdenes en orden, bordes, regresión del incidente, concurrencia, seguridad, i18n. Cliente: vitest + Testing Library + axe.
- **Por qué:** la concurrencia y el trigger no se pueden probar con SQLite ni con mocks.

### D-21 Lo que decidí no hacer
Login real, endpoint de listado de suertes, anulaciones (solo guía), migraciones Alembic, tabla de ciclos, limitador de tasa, CI, pruebas E2E en navegador real, métricas/alarmas. Razón: "no se espera más de un corte vertical ni más endpoints"; cada ítem está en `RIESGOS.md` o `GUIA-EXTENSION.md`.

## Qué probé y qué no
| Probado | Cómo |
|---|---|
| 6 órdenes en orden + bordes (160,00 exacto, KCL sin N, 52 bultos máx., borde de ciclo) | `test_example_orders.py`, `test_cycle_and_arithmetic.py` |
| Regresión del incidente (>50 filas, 3 páginas) | `test_incident_regression.py` |
| Concurrencia | `test_concurrency.py` |
| Seguridad (cifrado, logs, inmutabilidad, tokens, 401/403/404) | `test_security_and_traceability.py`, `test_validation_and_access.py` |
| Rendimiento p95 con 60.000 | `make perf` |
| UI: flujo completo, 409, errores, inactividad, idioma, almacenamiento | `App.test.tsx` |
| Accesibilidad automática | axe en 5 estados |
| **No probado:** lector de código de barras físico, Edge/Chrome/Firefox reales, lector de pantalla, contraste medido en navegador, carga concurrente por HTTP/nginx, restauración de respaldos | Requieren hardware/navegadores/infra que no hay en el entorno de la prueba |

## Lo que dejé fuera y por qué
Ver D-21: el enunciado limita el alcance a un corte vertical.

## Si tuviera más tiempo
1. Anulaciones (según `GUIA-EXTENSION.md`) con rol de agrónomo. 2. OIDC real. 3. Alembic. 4. E2E con Playwright + `@axe-core/playwright` en Chrome, Edge y Firefox. 5. Alarma "filas leídas = página" y conciliación nocturna contra kárdex. 6. KMS para las llaves de la cédula. 7. Limitador de tasa. 8. Tabla de ciclos.

## Decisiones adicionales (complemento)

### D-22 Día de calendario local (`local_date`) para definir el ciclo
- **Tema:** datos
- **Contexto:** "Un despacho de esa fecha o posterior pertenece al ciclo" y todas las horas son de America/Bogota. Un despacho a las 19:30 de Bogotá es del día siguiente en UTC.
- **Alternativas:** (a) comparar solo `timestamptz` (obliga a convertir zona en cada consulta y es fácil equivocarse en el borde); (b) guardar fecha UTC (cambia de ciclo a quien despacha de noche); (c) guardar `local_date` calculada una vez al insertar.
- **Decisión:** (c), además de `registered_at timestamptz`.
- **Por qué:** El borde del ciclo queda explícito, indexable y probado (el día del corte cuenta, el anterior no).
- **Consecuencias:** Un dato derivado más; se calcula en un solo lugar (`SqlDispatchRepository.add`). Depende de que la hora del servidor esté sincronizada.
- **Dónde se ve:** `orm.py`, `repositories.py`, `test_cycle_and_arithmetic.py`.

### D-23 Formato de errores y mensajes traducidos
- **Tema:** diseño
- **Contexto:** El contrato fija `{ "errores": [ { "campo", "mensaje" } ] }` para 400 y `{ "motivo", "mensaje", ... }` para 409.
- **Alternativas:** devolver códigos y traducir solo en el cliente (cliente y servidor desincronizados; clientes que no son la SPA verían códigos); devolver texto traducido según `Accept-Language`.
- **Decisión:** el dominio emite `FieldError(campo, código, parámetros)`; la capa API traduce con `Accept-Language` (es por defecto) y el cliente envía su idioma. El separador decimal sigue al idioma (`34,43` / `34.43`).
- **Por qué:** El texto siempre coincide con el idioma de la pantalla y el dominio no conoce idiomas.
- **Dónde se ve:** `domain/errors.py`, `api/i18n.py`, prueba de separador decimal.

### D-24 Orden determinista del historial
- **Tema:** datos
- **Decisión:** `ORDER BY local_date DESC, registered_at DESC, id` (el `id` desempata). Sin desempate, dos despachos en el mismo instante podrían repetirse o perderse entre páginas.
- **Dónde se ve:** `SqlDispatchRepository.cycle_page`, índice `dispatches_plot_date`.

### D-25 Redondeo asimétrico en las cifras mostradas
- **Tema:** diseño
- **Decisión:** `n_ciclo_kg_ha` se redondea al más cercano y `n_disponible_kg_ha` hacia abajo. Consecuencia visible: pueden sumar 159,99 (ej. 65,48 + 94,51 en S-104). Es deliberado: nunca se promete más disponible del real. La decisión de aceptar/rechazar usa gramos enteros, no estas cifras.
- **Dónde se ve:** `nitrogen.available_kg_ha`, `docs/API.md`.

### D-26 Documentación como parte de la entrega verificable
- **Tema:** proceso
- **Decisión:** `API.md` se escribió con respuestas capturadas del sistema real (no inventadas) y `GUIA-EXTENSION.md` se ejecutó en una copia del proyecto; los errores que salieron (6) se corrigieron en la guía. Las salidas de `make test`/`make perf` están en `EVIDENCIAS.md`.
- **Por qué:** una guía sin ejecutar suele fallar justo en el primer paso del lector.

### D-27 Documentación de código obligatoria y verificada
- **Tema:** proceso
- **Contexto:** El código lo leerán evaluadores y el desarrollador junior de la guía; debe poder entenderse sin preguntar.
- **Alternativas:** (a) comentarios sueltos (se desactualizan, no se verifican); (b) docstrings Google-style en Python y TSDoc en TypeScript, más una prueba que falla si falta alguna.
- **Decisión:** (b). Todo módulo, clase, función y método del servidor lleva docstring (propósito, `Args`, `Returns`, `Raises` cuando aplica); todo componente, hook y función del cliente lleva TSDoc con `@param`/`@returns`. `tests/test_documentation.py` recorre el árbol sintáctico y falla listando lo que falte.
- **Por qué:** Lo que se verifica automáticamente no se degrada. Los comentarios explican el *por qué* (reglas de negocio, privacidad, decisiones del incidente), no repiten el código.
- **Consecuencias:** Una prueba más; cada función nueva exige su docstring.
- **Dónde se ve:** `backend/tests/test_documentation.py`, `backend/app/**`, `frontend/src/**`.
