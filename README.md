# Ventanilla de despachos — Agrícola La Guabina (DS-FS-20261120-ykgp)

**ES** — Corte vertical para registrar despachos de fertilizante respetando el límite de 160 kg N/ha por ciclo.
**EN** — Vertical slice to register fertilizer dispatches while enforcing the 160 kg N/ha-per-cycle limit.

Flask 3 + SQLAlchemy 2 + PostgreSQL 16 · React 18 + TypeScript + Vite · todo con Docker Compose / everything with Docker Compose.

## Requisitos / Requirements
Docker + Docker Compose v2. Opcional / optional: `make` y `python3` (el script que genera los secretos usa `python3`; sin él cree `.env` a mano a partir de `.env.example`).

## 1. Iniciar / Start
```bash
make up                    # genera .env con secretos aleatorios, construye y levanta todo
# sin make:  ./scripts/setup.sh && docker compose up --build -d
docker compose ps          # listo cuando db y web están "running/healthy" y init terminó ("exited (0)")
```
La primera vez construye las imágenes (unos minutos). / The first run builds the images (a few minutes).
Aplicación / App: <http://localhost:8088> (cambie el puerto con `WEB_PORT` en `.env`).

## 2. Obtener el token de sesión / Get a session token
No hay endpoint de login (el contrato solo tiene 2): un token firmado simula la identidad corporativa y lleva la bodega y la ventanilla del bodeguero. / There is no login endpoint (the contract has only 2): a signed token stands in for the corporate identity and carries the operator's warehouse and counter.
```bash
make tokens
# sin make (uno solo): docker compose run --rm --no-deps -T init flask --app wsgi issue-token B-SUR-01
```
El token es **la última línea** que imprime cada operador: una sola línea larga con tres partes separadas por puntos (`xxxx.yyyy.zzzz`). Docker puede imprimir líneas de contenedor antes; ignórelas. / The token is the **last line** printed per operator: one long line with three dot-separated parts.

| Operador / Operator | Bodega / Warehouse | Ventanilla / Counter | Suertes que puede ver / Plots it can open |
|---|---|---|---|
| `B-NORTE-01` | NORTE | NORTE-1 | `S-104`, `S-117` |
| `B-SUR-01` | SUR | SUR-1 | `S-208`, `S-212`, `S-221`, `S-305` |
| `B-SUR-02` | SUR | SUR-2 | `S-208`, `S-212`, `S-221`, `S-305` |

Una suerte de otra bodega responde 403; una inexistente, 404. / A plot of another warehouse returns 403; an unknown one, 404.

## 3. Entrar y probar / Sign in and try it
1. Abra <http://localhost:8088>, pegue el token completo de `B-NORTE-01` en **Token de sesión** y pulse **Entrar** (o Enter). Arriba aparece "Bodega NORTE · Ventanilla NORTE-1".
2. Busque la suerte `S-117`: muestra 107,67 de 160 kg N/ha usados.
3. Registre primero `OF-2026-1190`: producto `DAP`, dosis `46`, cédula de 6 a 10 dígitos. Revise, confirme: son **70 bultos** y aportan 17,90 kg N/ha (el DAP también lleva nitrógeno), quedando en 125,57.
4. Registre ahora `OF-2026-1191`: producto `URE`, dosis `40`. La pantalla de revisión muestra **61 bultos**; al confirmar, el servidor responde **409**: solo caben **52 bultos** (quedan 34,43 kg N/ha). Pulse "Usar 52 bultos": ajusta la dosis y conserva los demás campos.
5. Para la API directa: `Authorization: Bearer <token>` (ver [docs/API.md](docs/API.md)).

> El token vive solo en memoria: dura **12 h**, y la sesión se cierra tras **10 min sin actividad** o al recargar la página; vuelva a pegarlo. / The token lives only in memory: valid **12 h**; the session closes after **10 min idle** or on page reload; paste it again.

### Problemas frecuentes / Troubleshooting
| Síntoma / Symptom | Causa y solución / Cause and fix |
|---|---|
| "El token no es válido" | Copió solo una parte o con saltos de línea; pegue la línea completa. |
| 403 al buscar una suerte | El operador es de otra bodega: use la tabla de arriba. |
| `make tokens` falla con "env file not found" | Falta `.env`: ejecute `make setup` (o `./scripts/setup.sh`). |
| Puerto 8088 ocupado | Cambie `WEB_PORT` en `.env` y ejecute `make up` de nuevo. |
| La app no responde justo después de `make up` | `init` aún crea el esquema: espere y revise `docker compose ps` / `docker compose logs init`. |
| Quiere empezar de cero | `docker compose down -v` borra también la base de datos. |

## Pruebas / Tests (un solo comando / one command)
```bash
make test                  # servidor (pytest + PostgreSQL real) + cliente (vitest + axe)
make perf                  # medición p95 con 60.000 despachos (GET ≤ 200 ms, POST ≤ 300 ms)
```
Sin make: `docker compose --profile test run --rm --build api-tests` y `docker compose --profile test run --rm --build web-tests`.

## Estructura / Layout
```
backend/app/domain          reglas puras (aritmética entera de N, catálogo)       pure rules
backend/app/application     casos de uso + puertos (Protocol)                      use cases + ports
backend/app/infrastructure  SQLAlchemy ORM, Fernet, JWT, logs                      adapters
backend/app/api             Flask: rutas, esquemas, i18n es/en                      HTTP layer
frontend/src                domain/ api/ components/ i18n/ (es, en)
```
Código, docstrings y pruebas están en inglés; los textos al usuario se traducen (es/en). Los nombres de campos del API (`orden`, `balance-nitrogeno`…) son el contrato del enunciado y no se tradujeron.

## Documentos / Documents
En `docs/`: [API](docs/API.md) · [GLOSARIO](docs/GLOSARIO.md) · [MODELO-DE-DATOS](docs/MODELO-DE-DATOS.md) · [EVIDENCIAS](docs/EVIDENCIAS.md) · [DECISIONES](docs/DECISIONES.md) · [INCIDENTE](docs/INCIDENTE.md) · [RIESGOS](docs/RIESGOS.md) · [GUIA-EXTENSION](docs/GUIA-EXTENSION.md) · [HISTORIAS-DE-USUARIO](docs/HISTORIAS-DE-USUARIO.md) · [FASES-DE-EJECUCION](docs/FASES-DE-EJECUCION.md)

## Detener / Stop
`make down` (los datos persisten en el volumen `pgdata`; `docker compose down -v` los borra).
