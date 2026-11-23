# Fases de ejecución del proyecto

Orden recomendado (el enunciado exige priorizar Parte 1 → 2 → 3). Cada fase termina con un **criterio de salida** verificable y un commit pequeño sugerido. Estado: ✅ completada.

| # | Fase | Entregables | Criterio de salida | Estado |
|---|---|---|---|---|
| 0 | **Análisis del enunciado y del incidente** | Lectura de datos y registros de la v1; cálculo manual de las 6 órdenes (bultos, N, disponible) | Cada orden tiene resultado esperado (201/409) y se detectó la causa raíz (50 filas = tamaño de página) | ✅ |
| 1 | **Esqueleto y Docker** | `docker-compose.yml`, Dockerfiles, `.env` por script, Makefile | `docker compose up` levanta db + api + web | ✅ |
| 2 | **Dominio puro** | `catalog.py`, `nitrogen.py` (aritmética entera) | Pruebas unitarias de bultos, N, bordes | ✅ |
| 3 | **Persistencia** | Modelos SQLAlchemy, restricciones, índice cubriente, trigger de inmutabilidad, seed del enunciado | Esquema idempotente; balance de S-104 = 65,48 | ✅ |
| 4 | **Casos de uso y API** (Parte 1) | `RegisterDispatch`, `GetBalance`, rutas, validación, errores, i18n, JWT, cifrado de cédula | Las 6 órdenes en orden pasan; 400/401/403/404/409 | ✅ |
| 5 | **Concurrencia y regresión del incidente** | `FOR UPDATE`, `REPEATABLE READ` en lecturas, pruebas de 6 hilos y 104 filas | Exactamente un 201 en carrera; balance suma todo el ciclo | ✅ |
| 6 | **Medición de rendimiento** | `make perf` con 60.000 despachos | GET p95 ≤ 200 ms, POST p95 ≤ 300 ms (medido ≈ 18 / 16 ms) | ✅ |
| 7 | **Cliente** (Parte 2) | Dominio (bultos, validación), API client, i18n es/en, componentes, estilos | Flujo completo contra la API real vía nginx | ✅ |
| 8 | **Calidad del cliente** | Pruebas de flujo, privacidad (sin storage), inactividad, idioma; axe WCAG 2.2 AA | 42 pruebas verdes | ✅ |
| 9 | **Endurecimiento** | CSP, `no-store`, contenedores no root/solo lectura, secretos, filtro de logs | Cabeceras presentes; cédula ausente de logs | ✅ |
| 10 | **Documentación** (Parte 3) | `INCIDENTE.md`, `RIESGOS.md`, `GUIA-EXTENSION.md`, `DECISIONES.md`, `README.md`, este archivo, historias, cómo probar/justificar | Todos los archivos obligatorios presentes | ✅ |
| 11 | **Verificación final y entrega** | `make test` y `make perf` desde cero; completar horas en `DECISIONES.md`; historial Git | Comandos del README funcionan en un clon limpio | ⏳ (horas y commits: a cargo del autor) |
| 12 | **Preparación de la sustentación** | Ensayar la demo y las respuestas; practicar un cambio en vivo | Explicar cada decisión de memoria, sin IA | ⏳ |

## Plan de commits sugerido (historia revisable)
1. `chore: docker compose, Makefile y secretos por script`
2. `feat(domain): catálogo y aritmética entera del balance de nitrógeno`
3. `feat(db): modelos SQLAlchemy, índice cubriente y trigger de inmutabilidad`
4. `feat(api): registrar despacho y consultar balance con validación y errores`
5. `feat(security): JWT de sesión, autorización por bodega, cifrado y filtro de cédula`
6. `fix(concurrency): bloqueo por suerte y lecturas con instantánea` + prueba de 6 hilos
7. `test: regresión del incidente S-305 (más de 50 filas) y las 6 órdenes`
8. `test(perf): medición p95 con 60.000 despachos`
9. `feat(web): dominio del cliente, API client e i18n es/en`
10. `feat(web): formulario con confirmación, límite y accesibilidad`
11. `test(web): flujo, privacidad, inactividad y axe`
12. `chore(web): nginx con CSP y contenedor sin privilegios`
13. `docs: incidente, riesgos, guía de extensión y decisiones`
14. `docs: historias de usuario, fases y guía de prueba/justificación`

## Dependencias entre fases
0 → 2 → 3 → 4 → 5 → 6 ; 4 → 7 → 8 ; 1 transversal ; 9 después de 4 y 7 ; 10 puede avanzar en paralelo desde la fase 0.
