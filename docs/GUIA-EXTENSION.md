# Guía de extensión — Anular (total o parcialmente) un despacho devuelto sin abrir

Para un desarrollador recién llegado. Sigue los pasos en orden; cada uno dice **qué archivo** tocar y **cómo probarlo**.

> **Esta guía fue ejecutada.** Se implementó la anulación completa en una copia del proyecto siguiendo estos pasos: servidor 55 pruebas verdes, cliente 47 verdes, y la medición de rendimiento no cambió (GET p95 ≈ 17,8 ms, POST ≈ 14,3 ms). Los avisos marcados con ⚠ son errores reales que aparecieron al ejecutarla; evítalos.

Los nombres de código están en inglés; si dudas de un término, mira `GLOSARIO.md`.

## 0. Antes de empezar
```bash
make up && make test          # todo debe estar en verde
```
Reglas del sistema que **no puedes romper**:
1. Los despachos **no se modifican ni se eliminan** (trigger en BD). Una anulación es un **registro nuevo**.
2. El N del ciclo siempre sale de una **agregación SQL**, jamás del historial paginado (ver `INCIDENTE.md`).
3. Toda escritura sobre una suerte toma el bloqueo `FOR UPDATE` de esa suerte.
4. Ninguna respuesta ni log lleva la cédula completa.

## 1. Diseño (lo que vas a construir)
- Tabla nueva `voidings` (solo inserción): `id`, `dispatch_id` (FK), `bags_voided` (>0), `n_grams_voided`, `reason` (no vacío), `voided_by`, `voided_at`.
- Regla: `SUM(bags_voided)` de un despacho **≤ su `bags`**. Anular reduce el N del ciclo: `N_ciclo = SUM(dispatches.n_grams) − SUM(voidings.n_grams_voided)` (solo despachos del ciclo).
- Endpoint: `POST /api/v1/despachos/{id}/anulaciones` con `{"bultos": 3, "motivo": "Devuelto sin abrir"}` → 201 con el despacho (incluye `bultos_anulados`). 400 validación · 403 sin rol · 404 despacho inexistente · 409 `ANULACION_EXCEDE_DESPACHO`.
- **Rol:** solo el **agrónomo** (`role == "AGRONOMIST"`). ⚠ El agrónomo **no pertenece a una bodega**: la anulación comprueba el rol, **no** compara bodegas (a diferencia de registrar). El token seguirá llevando un `bodega` válido (la oficina), pero no se usa para autorizar la anulación.

## 2. Backend — paso a paso
1. **Dominio** (`app/domain/`)
   - `models.py`: añade `bags_voided: int = 0` a `Dispatch`; `role: str = "OPERATOR"` a `OperatorSession`; y dos dataclasses: `Voiding(id, dispatch_id, bags_voided, n_grams_voided, reason, voided_by, voided_at)` y `VoidRequest(bags, reason)`.
   - `errors.py`: `VoidExceedsDispatch(DomainError)` y `DispatchNotFound(DomainError)`.
   - `nitrogen.py`: nada nuevo; reutiliza `n_grams(bags, product)`.
2. **Sesión y roles** (`infrastructure/services.py`): `SessionTokens.issue` añade el claim `"rol": s.role`; `verify` lee `c.get("rol", "OPERATOR")`; en `OPERATORS` agrega `"A-AGRO-01": OperatorSession("A-AGRO-01", "SUR", "OFICINA", "AGRONOMIST")` (sin esto `flask issue-token` no lo ofrece).
3. **Puertos** (`application/ports.py`): en `DispatchRepository` añade `get(dispatch_id, lock=False) -> Dispatch | None` y `add_voiding(v) -> None`.
4. **Caso de uso** (`application/use_cases.py`): `VoidDispatch` (mismo patrón que `RegisterDispatch`):
   ```python
   class VoidDispatch:
       def __init__(self, uow, clock): self._uow, self._clock = uow, clock

       def execute(self, session, dispatch_id, req):
           if session.role != "AGRONOMIST":
               raise AccessDenied()                       # 403
           with self._uow() as uow:
               d = uow.dispatches.get(dispatch_id)
               if d is None:
                   raise DispatchNotFound()               # 404
               uow.plots.get(d.plot, lock=True)           # mismo bloqueo que registrar
               if d.bags_voided + req.bags > d.bags:
                   raise VoidExceedsDispatch()            # 409
               uow.dispatches.add_voiding(Voiding(
                   str(uuid.uuid4()), d.id, req.bags, nit.n_grams(req.bags, PRODUCTS[d.product]),
                   req.reason, session.id, self._clock.now()))
               return uow.dispatches.get(dispatch_id)
   ```
5. **Persistencia**
   - `infrastructure/orm.py`: modelo `VoidingORM` (`voidings`) con `CheckConstraint("bags_voided > 0")`, `CheckConstraint("length(trim(reason)) > 0")`, FK a `dispatches.id` con índice.
   - `infrastructure/db.py`: añade al `_TRIGGER` el mismo trigger de inmutabilidad para `voidings` (reutiliza la función `dispatches_immutable`).
6. **Repositorio** (`infrastructure/repositories.py`) — tres cambios:
   - `cycle_nitrogen_g` resta lo anulado:
     ```python
     gross = select(func.coalesce(func.sum(DispatchORM.n_grams), 0)).where(*self._in_cycle(plot, since))
     voided = (select(func.coalesce(func.sum(VoidingORM.n_grams_voided), 0))
               .join(DispatchORM, DispatchORM.id == VoidingORM.dispatch_id).where(*self._in_cycle(plot, since)))
     return int(self._s.execute(gross).scalar_one()) - int(self._s.execute(voided).scalar_one())
     ```
   - ⚠ `get(dispatch_id)` **debe unir con `plots` para traer `net_area_ha`** (`select(DispatchORM, PlotORM.net_area_ha).join(...)`) y pasarlo como `net_area_dha`; si lo dejas en 0 el serializador divide por cero (500). Además `UUID(dispatch_id)` puede fallar: captura `ValueError` y devuelve `None` (→ 404).
   - ⚠ `cycle_page` **debe traer los bultos anulados por despacho**, o el historial mostrará 0 aunque haya anulaciones:
     ```python
     voided = (select(func.coalesce(func.sum(VoidingORM.bags_voided), 0))
               .where(VoidingORM.dispatch_id == DispatchORM.id).correlate(DispatchORM).scalar_subquery())
     q = select(DispatchORM, voided).where(*self._in_cycle(plot, since)).order_by(...).limit(limit).offset(offset)
     # for r, v in self._s.execute(q).all():  Dispatch(..., net_area_dha, int(v))
     ```
   - `add_voiding(v)`: `self._s.add(VoidingORM(...)); self._s.flush()`.
7. **API** (`app/api/`)
   - `schemas.py`: `parse_void_request(data)` → `VoidRequest`; `bultos` entero ≥ 1 (no booleano), `motivo` de 1 a 200 caracteres tras `strip()`; errores como `FieldError("bultos", "void_bags")` y `FieldError("motivo", "void_reason")`.
   - `routes.py`: ruta `POST /despachos/<dispatch_id>/anulaciones` con `@requires_session`; handlers `VoidExceedsDispatch → 409 {"motivo": "ANULACION_EXCEDE_DESPACHO"}` y `DispatchNotFound → 404`. ⚠ Parsea el JSON dentro de `try/except ValueError` (→ `InvalidData` `invalid_json`); si no, un cuerpo roto da 500.
   - `serializers.py`: `dispatch_json` añade `"bultos_anulados": d.bags_voided`.
   - `i18n.py`: claves nuevas **en es y en** (`void_reason`, `void_bags`, `void_exceeds`, `dispatch_not_found`).
   - `app/__init__.py`: registra `void=VoidDispatch(uow, clock or SystemClock())` en `app.extensions`.
8. **Pruebas** (`backend/tests/test_voiding.py`, en inglés) — estas pasaron al ejecutar la guía:
   - anulación parcial baja `n_ciclo_kg_ha`; la respuesta trae `bultos_anulados`;
   - más bultos de los despachados → 409; usuario sin rol → 403; motivo en blanco → 400;
   - id inexistente o mal formado → 404;
   - tras anular 70 de 70, el despacho antes rechazado (409) ahora se acepta (201);
   - `DELETE FROM voidings` falla por el trigger; el historial muestra `bultos_anulados`.
   Ejecuta: `make test-api` y luego `make perf` (la agregación ahora tiene un JOIN: el p95 no debe acercarse a 200/300 ms).

## 3. Frontend — paso a paso
1. **Tipos y cliente** (`src/api/`): `types.ts` añade `bultos_anulados: number` a `DispatchDto`; `client.ts` añade `voidDispatch(id, {bultos, motivo})` con resultado discriminado (`voided | invalid | exceeds | unauthorized | forbidden | not_found | network | error`), igual que `registerDispatch`.
2. **Sesión** (`src/api/session.ts`): `SessionInfo` añade `role` leído del claim `rol` (por defecto `"OPERATOR"`). Mostrar el botón solo si `role === "AGRONOMIST"`; el servidor es quien manda, ocultar es cortesía.
3. **Textos** (`src/i18n/es.ts` y `en.ts`): claves `void.*` y `history.col.voided`. TypeScript falla si falta alguna en `en.ts`.
4. **Componente** `src/components/VoidDialog.tsx`: formulario con `bultos` (1 … bultos − anulados) y `motivo` (≤ 200). Mismas reglas de accesibilidad que `DispatchForm`: `label` por campo, `aria-invalid`, `aria-describedby` al error. ⚠ **No pongas `role="group"` en un `<form>`**: axe lo rechaza (`aria-allowed-role`); `aria-labelledby` basta.
5. **Integración** (`HistoryTable.tsx`): prop opcional `onVoid`; añade la columna "Anulados" y, si `onVoid` existe, un botón "Anular" por fila (con el número de orden en texto solo para lector de pantalla). Al terminar, recarga el balance con `load(plot, 1)`.
6. **Pruebas** (`src/VoidDialog.test.tsx`): valida antes de llamar; rechaza más bultos de los despachados; envía `{bultos, motivo}` y avisa éxito; muestra el mensaje de un 409; **axe sin violaciones**. ⚠ Los datos de prueba (`src/test/helpers.tsx`, función `dispatch()`) deben incluir `bultos_anulados: 0` o TypeScript falla en todas las pruebas existentes.
   Ejecuta: `make test-web`.

## 4. Lista de verificación antes de abrir el PR
- [ ] `make test` verde y `make perf` dentro de objetivos.
- [ ] Ningún `UPDATE`/`DELETE` sobre `dispatches` ni `voidings`.
- [ ] Mensajes nuevos en es y en; sin la cédula en logs ni respuestas.
- [ ] `GET balance` tras anular: `n_ciclo_kg_ha` baja y `n_disponible_kg_ha` sube.
- [ ] Actualizaste `RIESGOS.md` (nuevo rol) y `DECISIONES.md` (nueva entrada: por qué tabla de anulaciones y no `UPDATE`; por qué el agrónomo no se limita por bodega).
- [ ] Actualizaste `API.md` con el nuevo endpoint.
