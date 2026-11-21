# Guía para la exposición y la demo

Para que ambos integrantes dominen todo el trabajo. Cada pregunta tiene su respuesta corta y dónde verificarla. Arquitectura: `docs/arquitectura.md`.

## Demo (unos 4 minutos)

1. `python demo.py final` (se ensayó en 3 min 36 s): contrato, API, web y reporte.
2. Abrir el sitio de Pages: portada con el quality gate (6 de 6), matriz HU → caso, dashboard y «IA en el ciclo».
3. Abrir el dashboard de contrato (Schemathesis frente a nuestros `.feature`) y la pestaña Hallazgos.
4. Mostrar el run con evidencia (`fallos`) frente a uno sin ella (`no`).

## Preguntas probables

| Tema | Respuesta corta | Dónde verificar |
|---|---|---|
| ¿Por qué el contrato va primero? | Es la verificación más amplia y barata; si la API no cumple su OpenAPI, lo demás no tiene sentido | `arquitectura.md` §4 |
| ¿Qué halla Schemathesis que los `.feature` no? | Entradas inesperadas y carreras: DEF-15 (la API responde antes de confirmar en BD) y DEF-17 (`cci` ignorado) | `comparativa-schemathesis.md` |
| ¿Por qué Page Object y no Screenplay? | 6 clases pequeñas, un rol casi siempre; un selector se corrige en un solo lugar. Screenplay se evaluaría con muchos actores | `informe.md` §3.1 (escalabilidad) |
| ¿Por qué `recargarHasta`? | DEF-15: la API responde antes de guardar, así que la UI puede leer datos viejos; se recarga y reintenta | `tests/e2e/pages/espera.js` |
| ¿Cómo se usa el reporte sin evidencia? | Input `evidencia` (`fallos`, `todo`, `no`); con `no` salen 0 adjuntos | `README.md`, `informe.md` |
| ¿Qué son los quality gates? | G1 a G6: cobertura, contrato sin fallos, web 3/3, toda HU con caso, duración, estado real publicado | `reportes.py` |
| ¿Por qué rendimiento no está en el CI? | Dura de 17 a 32 min y exige CPU fija; un runner compartido no da resultados comparables | `arquitectura.md` §4 |
| ¿Qué aporta la IA y cómo la validaron? | Un agente explora la web con el MCP. En el CI (US$ 0,41) dio 5 entradas: 3 conocidos bien marcados, DEF-14 mal marcado y 1 que no era hallazgo; verificamos a mano: 0 nuevos. Propone, no decide | `ia-en-el-ciclo.md` §4 |
| ¿MCP o agente de código directo? | Se midieron tokens y costo de ambos | `comparativa-mcp-agentes.md` |
| ¿Por qué Qase? | Plan gratuito con API; comparado con Kiwi TCMS (autoalojado) | `gestion-casos.md` |
| ¿Qué defectos hay? | 16 abiertos (DEF-01 a DEF-17, DEF-11 descartado) | `defectos.md` |
| ¿Qué límite tiene el sistema? | Capacidad medida en EC2 de 1 000 usuarios o más; DEF-16 (`database is locked`) bajo carga | `comparativa-rendimiento.md` |

## Reparto sugerido al exponer

Cada uno presenta un bloque y responde en el del otro: **Sebastián** web, patrón, IA y MCP; **Maykol** pipeline, reportes, trazabilidad y rendimiento. Ambos deben poder ejecutar `demo.py` y explicar el gate.
