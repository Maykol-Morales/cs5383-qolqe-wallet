# Declaración de uso de IA

| Fecha | Herramienta | Tarea | Qué aceptamos | Qué corregimos o descartamos y por qué |
|---|---|---|---|---|
| 2026-10-12 | Claude Code (Claude Sonnet 5.5) | Lectura del enunciado y de `docs/requisitos.md`; redacción de los `.feature` del núcleo y de G3 | Estructura de los escenarios, uso de `Scenario Outline` con valores límite, etiquetas `@HU-…` | El asistente asumió "hasta ayer" como rango de 90 días y mezclaba la recarga de hoy en los conteos: se cambió a "últimos 90 días hasta hoy" para no mezclar con el defecto DEF-07. Se quitó el escenario "solo veo mis propios movimientos" porque no se podía verificar con los datos semilla |
| 2026-10-12 | Claude Code | Pasos de pytest-bdd (`tests/api/`), fixtures y prueba de contrato con Schemathesis | Fixtures `ctx`/`http`, reinicio de datos por escenario, marcado de defectos como `xfail(strict)` | Se partieron pasos ambiguos (`parse` coincidía con dos frases) y se desactivaron los checks `positive/negative_data_acceptance` de Schemathesis porque generaban falsos positivos |
| 2026-10-12 | Claude Code | Búsqueda y reporte de defectos (`docs/defectos.md`) | Los 10 defectos: cada uno se reprodujo ejecutando la API antes de documentarlo | Revisar y confirmar a mano los pasos de reproducción y la severidad antes de entregar *(pendiente del equipo)* |
