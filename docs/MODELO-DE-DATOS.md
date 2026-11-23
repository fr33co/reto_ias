# Modelo de datos

Dos entidades, como pide el enunciado. Esquema verificado con `\d` sobre la base en ejecución.

```
┌───────────────────────────┐ 1        N ┌────────────────────────────────────────┐
│ plots  (suerte)           │────────────│ dispatches  (despacho)  ← solo inserción│
├───────────────────────────┤            ├────────────────────────────────────────┤
│ code            PK  S-NNN │◀───────────│ plot            FK → plots.code        │
│ warehouse       NORTE|SUR │            │ id              PK uuid                │
│ gross_area_ha   numeric(6,1)│          │ order_no        UNIQUE  OF-AAAA-NNNN   │
│ net_area_ha     numeric(6,1)│          │ product         URE|SAM|DAP|KCL        │
│ cycle_start     date      │            │ dose_kg_ha      numeric(4,1) (0,200]   │
│ cycle_origin    CORTE|SIEMBRA│         │ bags            int > 0                │
│ irrigation      SURCOS|FERTIRRIEGO│    │ delivered_kg    int > 0                │
└───────────────────────────┘            │ n_grams         bigint ≥ 0             │
                                         │ foreman_encrypted_id  text (Fernet)    │
                                         │ foreman_last4   varchar(4)             │
                                         │ counter         varchar(10)            │
                                         │ registered_by   varchar(20)            │
                                         │ registered_at   timestamptz            │
                                         │ local_date      date (America/Bogota)  │
                                         └────────────────────────────────────────┘
```

## Restricciones (la BD es la última defensa)
| Tabla | Restricción | Razón |
|---|---|---|
| `plots` | `CHECK code ~ '^S-[0-9]{3}$'`, bodega/origen/riego en listas, `0 < net ≤ gross` | Datos coherentes aunque se escriba por fuera de la app |
| `dispatches` | `UNIQUE(order_no)` | Una orden se despacha una vez (supuesto S4); también cubre la carrera entre ventanillas |
| `dispatches` | `CHECK` formato de orden, producto, `0 < dosis ≤ 200`, cantidades positivas | Espejo de la validación de la API |
| `dispatches` | FK `plot → plots.code` | No hay despachos huérfanos |
| `dispatches` | **Trigger** `BEFORE UPDATE OR DELETE` → excepción | Trazabilidad: no se modifica ni elimina (el `TRUNCATE` de las pruebas no lo dispara) |

## Decisiones de modelado
- **Unidades enteras.** `n_grams` guarda el nitrógeno en gramos (entero exacto = `bags · kg_bulto · n% · 10`). La suma y la comparación con el límite (`160 · área_décimas · 100`) son exactas. Los kg/ha se calculan solo al presentar.
- **`n_grams` y `bags` se guardan, no se recalculan.** Si el catálogo de leyes cambiara, el histórico seguiría reflejando lo que realmente se entregó.
- **`local_date`.** El ciclo se define por **día calendario en Bogotá** ("un despacho de esa fecha o posterior pertenece al ciclo"). Guardar solo `timestamptz` obligaría a convertir zona en cada consulta y a un despacho a las 19:30 de Bogotá (00:30 UTC) lo cambiaría de día. Se calcula una vez al insertar.
- **Un ciclo por suerte (`cycle_start`).** Cuenta `local_date >= cycle_start`. Los despachos de ciclos anteriores no se borran; simplemente quedan antes de la fecha. Si se necesitara auditar ciclos pasados: tabla `cycles` (riesgo R11).
- **Cédula:** `foreman_encrypted_id` (Fernet; recuperable con la llave) + `foreman_last4` (para mostrar sin descifrar).
- **Trazabilidad de quién y dónde:** `registered_by` (id del bodeguero) y `counter` (ventanilla) vienen de la **sesión firmada**, no del cuerpo de la petición.
- **Productos en configuración** (`domain/catalog.py`) y `CHECK` de producto en la BD (el enunciado lo permite). Añadir un producto exige tocar ambos (ver sustentación §3.5).
- **`order_no`** y no `order`: `ORDER` es palabra reservada de SQL.

## Índice y consultas
```sql
CREATE INDEX dispatches_plot_date
  ON dispatches (plot, local_date DESC, registered_at DESC, id) INCLUDE (n_grams);
```
| Consulta | Cómo la sirve el índice |
|---|---|
| `SUM(n_grams) WHERE plot=:p AND local_date >= :d` | Index-only scan (`n_grams` va en `INCLUDE`): sin leer la tabla |
| `COUNT(*)` del ciclo | Mismo recorrido |
| Historial `ORDER BY local_date DESC, registered_at DESC, id LIMIT 50 OFFSET n` | El orden del índice coincide con el `ORDER BY`; `id` desempata para que la paginación sea determinista |
Medido: GET p95 ≈ 18 ms y POST p95 ≈ 16 ms con 60.000 despachos y 400 en el ciclo (ver `EVIDENCIAS.md`).

## Concurrencia y aislamiento
| Operación | Aislamiento | Mecanismo |
|---|---|---|
| Registrar | READ COMMITTED | `SELECT … FOR UPDATE` sobre la fila de la suerte: serializa las ventanillas de la **misma** suerte |
| Consultar balance | REPEATABLE READ, solo lectura | Una instantánea: suma, total de páginas y filas coherentes entre sí |

## Seed de ejemplo (`app/seed.py`)
6 suertes del enunciado + 9 despachos previos + 104 de S-208 (`06:30` y `14:30`, del 2026-10-02 al 2026-11-22). Cédula sintética cifrada. Es idempotente (no duplica suertes ni órdenes).

## Migraciones
Hoy `create_all` + trigger vía `init-db` (idempotente). Para producción: Alembic (riesgo R13).
