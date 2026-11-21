# Reparto de la deuda técnica (rama `final`)

Feedback de la profesora (Partes 1 y 2) y de la Parte 3. **Todo quedó hecho en la rama `final`.**

| Punto | Estado | Dónde |
|---|---|---|
| Contrato primero y una sola ejecución de Schemathesis | Hecho | job `contrato` |
| Duplicados entre contrato y `.feature`, y comparación | Hecho | `comparativa-schemathesis.md`, dashboard de contrato |
| Quality gates con umbrales (G1 a G6), publicar siempre | Hecho | `pruebas.yml`, `reportes.py` |
| Reporte con o sin evidencia | Hecho | input `evidencia`, variable `EVIDENCIA` |
| Trazabilidad entre ejecuciones y herramienta de gestión | Hecho (Qase investigado frente a Kiwi) | `gestion-casos.md`, `qase.py` |
| Login web inestable y matriz de 3 corridas | Hecho | `recargarHasta`, job `web` |
| Más escenarios web y módulo común (Núcleo) | Hecho: 50 escenarios | `tests/e2e/features/` |
| Justificar Page Object y su escalabilidad | Hecho | `informe.md` §3.1 |
| Complementariedad de herramientas | Hecho | `informe.md` §3.2, `arquitectura.md` |
| Parte 3: limpiar resultados y mostrar mejor los datos | Hecho | `tests/performance/resumen.py`, `resultados/index.html` |
| IA en el ciclo y comparación MCP frente a agentes | Hecho | `ia-en-el-ciclo.md`, `comparativa-mcp-agentes.md` |

## Pendiente fuera del repositorio

- Actualizar los decks (16 defectos, 50 escenarios web, capacidad en EC2, IA y MCP, DEF-17).
- Rotar el token de Qase y la clave de Anthropic que se compartió en un chat.
- Revisar en Qase que aparezcan los runs del proyecto.
