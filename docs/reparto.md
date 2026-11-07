# Reparto de la deuda técnica (rama `final`)

Feedback de la profesora (Partes 1 y 2). Orden acordado: 2 → 1 → 3 → 4 y 5.

## Hecho

- Punto 2, paso 1: job `contrato` primero y una sola ejecución de Schemathesis.
- Punto 2, paso 2: dashboard de ejecuciones y duplicados (44 → 12 escenarios que solo repiten el contrato).

## Maykol (pipeline, reportes, gestión de casos)

| # | Tarea | Entregable |
|---|---|---|
| 2.3 | Quality gates con umbrales: `--cov-fail-under`, 0 fallos de contrato, web 3/3, toda HU con un caso ejecutado, tope de duración; publicar siempre con el estado real | `pruebas.yml`, `reportes.py` |
| 2.5 | Reporte con o sin evidencia: input `evidencia` en `workflow_dispatch` y variable `EVIDENCIA` en local (adjuntos HTTP en pytest) | `pruebas.yml`, `tests/api/conftest.py` |
| 3 | Trazabilidad para varias ejecuciones + herramienta de gestión de casos (Qase o Kiwi TCMS): investigar, elegir y justificar | `docs/informe.md`, `reportes.py` |

## Sebastián (E2E y fundamentación)

| # | Tarea | Entregable |
|---|---|---|
| 2.4 | Arreglar el login inestable del E2E (`toHaveUrl` en el job web) y que la matriz de 3 corridas no se corte en la primera falla | `tests/e2e/`, `pruebas.yml` (job `web`) |
| 1 | Más escenarios E2E: los que valga la pena automatizar + módulo común (Núcleo: registro, sesión, cuenta, transferencias) | `tests/e2e/features/`, `steps/`, `pages/` |
| 4 | Fundamentar por qué Page Object (mantenibilidad, reutilización; ejemplos del repo) | `docs/informe.md` §3 |
| 5 | Mostrar que las herramientas se complementan (BDD, contrato, E2E, Allure) y sustentar su elección | `docs/informe.md`, `docs/comparativa-ia.md` |

## Dependencias

- 2.5 (evidencia en E2E: capturas) toca el mismo job `web` que 2.4: Sebastián lo termina primero y Maykol agrega el input después.
- 3 usa los escenarios nuevos de la tarea 1 para la matriz; conviene que Sebastián los suba antes de cerrar la trazabilidad.
- Ambos tocan `pruebas.yml`: hacer `git pull --rebase` antes de cada push.
