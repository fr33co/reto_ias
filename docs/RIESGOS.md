# RIESGOS TÉCNICOS

Escala: Probabilidad (P) y Impacto (I) = Baja / Media / Alta.

| # | Riesgo | P | I | Mitigación (hecha / pendiente) |
|---|---|---|---|---|
| R1 | Un cálculo de N basado en datos de presentación vuelve a distorsionar el límite (causa del incidente) | M | Alta | **Hecha:** suma por agregación, pruebas con >50 filas. **Pendiente:** alarma si una lectura iguala el tamaño de página; conciliación nocturna contra kárdex. |
| R2 | Carrera entre ventanillas SUR supera el límite | M | Alta | **Hecha:** `FOR UPDATE` por suerte + prueba con 6 hilos. **Pendiente:** si se escala a varias réplicas con BD distribuida, el bloqueo debe seguir en la BD (no en memoria). |
| R3 | Diferencia entre bultos que el cliente muestra y los que el servidor registra ("lo que se registra es lo que se carga") | M | Alta | **Hecha:** el cliente envía `bultos_confirmados`; si difiere, 400 y no se registra. Mismos vectores de prueba en ambas capas. |
| R4 | Fuga de la cédula (Ley 1581 de 2012): BD, copias de seguridad, logs, pantalla | M | Alta | **Hecha:** cifrado Fernet en reposo, solo 4 dígitos en respuestas, filtro de logs, campo `password`, sin almacenamiento en el navegador, borrado tras registrar. **Pendiente:** KMS/rotación programada de llaves, política de retención y supresión, cifrado de respaldos. |
| R5 | Residuos en el computador compartido de 3 turnos (token en pantalla, caché, historial) | M | Media | **Hecha:** token solo en memoria, cierre por inactividad (10 min), `Cache-Control: no-store`, CSP. **Pendiente:** modo quiosco del navegador, bloqueo de sesión del SO por turno. |
| R6 | La pantalla queda de frente a la fila: se ve el balance y los capataces (enmascarados) | M | Baja | Cédula siempre enmascarada y campo oculto al digitar. Pendiente: opción de ocultar el historial por defecto. |
| R7 | Sesión simulada sin revocación; si se filtra el secreto JWT cualquiera emite tokens | B (demo) / M (prod) | Alta | Secreto aleatorio por instalación, expiración 12 h, verificación estricta (HS256, `iss`, `exp`). **Producción:** OIDC corporativo con claims de bodega, clave pública (RS256), revocación y rol. |
| R8 | Fuerza bruta / abuso de la API sin límite de tasa | B | Media | Cuerpo máx. 4 KB, validación estricta. Pendiente: limitador en nginx o gateway. |
| R9 | Política de redondeo de bultos distinta a la del negocio (se asumió el entero más cercano) | M | Media | Función única `bags_for_dose` y su espejo `bagsForDose`; cambiar a "hacia arriba/abajo" es una línea + pruebas. Validar con el agrónomo. |
| R10 | Fronteras de ciclo/zona horaria (día del corte, medianoche) | M | Media | `local_date` en `America/Bogota`; el día del corte cuenta; pruebas de borde. Pendiente: pruebas cerca de medianoche y reloj del servidor sincronizado (NTP). |
| R11 | Solo se guarda el ciclo actual (`plots.cycle_start`); al registrar un corte se pierde el rango del ciclo anterior | M | Media | Hoy los despachos antiguos se excluyen por fecha, no se pierden. Pendiente: tabla `cycles` si hace falta auditar ciclos pasados. |
| R12 | Crecimiento de datos (60.000 hoy; ~140/semana en SUR) | B | Media | Índice cubriente; p95 medido 16–18 ms con 60.000. Pendiente: particionar por año si supera ~10 M. |
| R13 | Esquema con `create_all` sin migraciones versionadas | M | Media | Aceptado para el corte. Pendiente: Alembic antes de producción. |
| R14 | Anular implementado con `UPDATE` rompería la trazabilidad | M | Alta | Trigger que bloquea `UPDATE/DELETE` en `dispatches`; la guía exige tabla de anulaciones solo-inserción. |
| R15 | Supuesto "una orden = un despacho" (índice único en `order_no`) bloquea entregas parciales legítimas | M | Media | 409 `ORDEN_DUPLICADA` explícito; si el negocio requiere parciales, añadir `order_lines`/saldo de orden. |
| R16 | Accesibilidad: axe en jsdom no mide contraste ni lector de pantalla real | M | Media | Reglas axe WCAG 2.2 AA pasan; contrastes elegidos a mano (≥ 7:1). Pendiente: prueba manual con NVDA y Edge/Chrome/Firefox, y axe en navegador real. |
| R17 | Punto único de falla de la BD y sin respaldos | M | Alta | Volumen persistente en compose. Pendiente: backups con PITR, réplica, plan de restauración probado. |
| R18 | Cadena de suministro (dependencias, imágenes) | B | Media | Versiones fijadas, usuario no root, `read_only`, `cap_drop ALL`. Pendiente: escaneo (Trivy/pip-audit/npm audit) en CI. |
| R19 | Lector de código de barras: el "teclado" puede escribir en otro campo si se pierde el foco | M | Media | Enter en la cédula abre la revisión, nunca registra directamente; confirmación obligatoria y legible. |
| R20 | Clientes antiguos en Firefox (oficina) | B | Baja | Sin APIs específicas de Chromium; solo CSS/JS estándar. Pendiente: matriz de pruebas de navegador. |
