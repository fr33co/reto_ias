# Historias de usuario

Actores: **Bodeguero** (ventanilla), **Capataz** (retira bultos), **Agrónomo**, **Auditor/Jefe de campo**, **Desarrollador**.
Estado: ✅ implementada · 📘 documentada en `GUIA-EXTENSION.md` (no implementada).

## Épica 1 — Registrar despachos respetando el límite
**HU-01 ✅ Registrar un despacho.** Como bodeguero quiero registrar el despacho de una orden (suerte, producto, dosis, cédula del capataz) para entregar los bultos y dejar trazabilidad.
- Dado una orden válida y N que cabe, cuando registro, entonces recibo 201 con bultos, kg, N aportado, capataz enmascarado, ventanilla y bodeguero.
- La dosis (kg del nutriente principal/ha neta) se convierte en bultos cerrados al más cercano.
- *Pruebas:* `test_example_orders.py`.

**HU-02 ✅ Rechazar lo que superaría el límite.** Como jefe de campo quiero que ningún despacho haga superar 160 kg N/ha por ciclo para cumplir el plan ambiental.
- El N de **todo** producto cuenta (DAP aporta N); un despacho sin N (KCL) no se bloquea.
- El límite es inclusivo (160,00 exacto se acepta).
- 409 con `n_despacho_kg_ha`, `bultos_maximos` y el balance.
- *Pruebas:* OF-1190/1191/1198, `test_full_cycle_rejects…`.

**HU-03 ✅ Dos ventanillas sin pisarse.** Como jefe de bodega Sur quiero que SUR-1 y SUR-2 nunca superen juntas el límite.
- Con peticiones simultáneas a la misma suerte, solo caben las que quepan en total. *Prueba:* `test_concurrency.py`.

**HU-04 ✅ Una orden se despacha una vez.** Como bodeguero quiero que reintentos o doble clic no dupliquen un despacho. → 409 `ORDEN_DUPLICADA`.

## Épica 2 — Consultar el balance
**HU-05 ✅ Ver balance e historial.** Como bodeguero quiero ver el N del ciclo, el disponible y el historial (50 por página, más reciente primero) de una suerte de mi bodega.
- El N sale de **todo** el ciclo, no de la página (regresión del incidente: S-208, 104 despachos, 3 páginas).
- Solo se cuentan despachos desde la fecha del corte/siembra (inclusive).

**HU-06 ✅ Solo mi bodega.** Como administrador quiero que cada bodeguero opere solo suertes de su bodega → 403 / 404 / 401.

## Épica 3 — Pantalla de ventanilla
**HU-07 ✅ Elegir suerte y ver balance** (por código, formato `S-NNN`).
**HU-08 ✅ Confirmar en ventanilla.** Como bodeguero quiero ver, antes de registrar, suerte, producto y **número de bultos** en grande para leerlos al capataz; el registro solo ocurre al confirmar.
**HU-09 ✅ Ajustar tras un rechazo.** Como bodeguero quiero ver el N disponible y los bultos máximos y corregir la dosis **sin volver a digitar** orden, producto ni cédula. (Botón "Usar N bultos".)
**HU-10 ✅ Errores claros.** Como bodeguero quiero que cada error indique qué campo corregir (resumen con enlaces + mensaje junto al campo; mismas reglas en cliente y servidor).
**HU-11 ✅ Lector de código de barras.** El lector escribe la cédula y termina con Enter: abre la confirmación, no registra.
**HU-12 ✅ Accesible (WCAG 2.2 AA)** y legible a 1366×768; teclado completo; español e inglés.

## Épica 4 — Privacidad y seguridad
**HU-13 ✅ Proteger la cédula (Ley 1581).** Como capataz quiero que mi cédula se guarde pero nunca se muestre completa (solo 4 dígitos), ni en pantalla al digitarla, ni en logs, ni quede en el computador compartido.
**HU-14 ✅ Trazabilidad.** Como auditor quiero que los despachos no se modifiquen ni eliminen (API sin PUT/PATCH/DELETE y trigger en BD).
**HU-15 ✅ Sesión simulada.** Como equipo de TI quiero simular sesiones por bodega/ventanilla y poder sustituirlas por la identidad corporativa.
**HU-16 ✅ Cierre por inactividad** (10 min) para el equipo compartido por tres turnos.

## Épica 5 — Operación y calidad
**HU-17 ✅ Rendimiento:** POST p95 ≤ 300 ms y GET p95 ≤ 200 ms con 60.000 despachos y 400 en el ciclo (medido ≈ 16–18 ms).
**HU-18 ✅ Un solo comando de pruebas** (`make test`) y despliegue con Docker Compose (`make up`).
**HU-19 ✅ Entender el incidente.** Como jefe de campo quiero saber qué pasó en S-305 (`INCIDENTE.md`) y cómo se evita (`RIESGOS.md`).

## Épica 6 — Futuro
**HU-20 📘 Anular (total o parcial) un despacho devuelto sin abrir.** Como agrónomo quiero anular bultos con un motivo, sin borrar el despacho, para liberar N del ciclo. Criterios: registro solo-inserción, no se anula más de lo despachado, reduce el N del ciclo, solo rol agrónomo. Ver `GUIA-EXTENSION.md`.
**HU-21 📘 Listar suertes de la bodega** (endpoint nuevo) y **OIDC real**.
