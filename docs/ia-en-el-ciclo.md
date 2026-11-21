# IA en el ciclo automático de pruebas

Pedido de la entrega final: agregar al ciclo automático alguna herramienta de IA que facilite el flujo o haga algo interesante. La indicación fue aprovechar la IA de **las herramientas que ya manejamos**. Investigación y pruebas del 2026-11-21.

## 1. Qué IA trae cada herramienta

| Herramienta | IA que incluye | Decisión |
|---|---|---|
| **WebdriverIO** (`@wdio/ai-service` 10.1.0) | `browser.act()` con caché; curación de pasos en 2 niveles (selector alternativo sin modelo, luego con modelo) con evidencia; verificación de efectos; `extract`; `wdio-ai eject` | **Se usa** (escenario `@ia`, CP-W90) y ahora se **muestra** en el dashboard (sección 2.1) |
| **WebdriverIO** (MCP `@wdio/mcp`, `wdio session`) | Servidor MCP con 42 herramientas y CLI para que un agente maneje el navegador | Medido en `comparativa-mcp-agentes.md`; se usa para explorar, no en el CI |
| **Allure 3** | *Agent Mode*: ordena un run (Markdown y JSON) para que un agente externo lo lea; no trae modelo | **Probado y descartado** (sección 3) |
| **Qase** | IA para generar casos; según su [página de precios](https://qase.io/pricing) no está en el plan gratuito | No se puede usar |
| **k6**, **Schemathesis** | No investigados | — |

Además se agregó una pieza propia que usa un modelo de Anthropic: el **triage de fallas** (sección 2.2). No se sumó otra herramienta de terceros.

## 2. Lo que quedó en el pipeline

### 2.1 La IA de WebdriverIO, visible en el dashboard del run

El escenario `@ia` pide los pasos al modelo una sola vez y los repite desde la caché versionada. Al terminar, `@wdio/ai-service` imprime un resumen (`4 act calls · 4 from cache · 0 healed … · 0 tokens`) que antes se perdía en el log. Ahora el job `web` guarda esa consola (`tee` → `reportes/ia-consola.txt`) y `reportes.py` publica en `dashboard.html` la sección **«IA en el ciclo: WebdriverIO (browser.act)»**: llamadas de IA, cuántas salen de la caché, pasos curados sin modelo y por el modelo, grabados por el modelo, tokens y la lista de pasos curados.

- **Qué significa:** en el CI no hay clave de API, así que solo puede curar sin modelo (probar otros selectores del mismo elemento). «0 tokens» quiere decir que nadie gastó. Si la interfaz cambiara, ahí se vería cuántos pasos se curaron antes de que la prueba falle.
- **Probado:** el lector se verificó con la salida real del escenario (4 llamadas, 4 desde la caché, 0 tokens) y con un ejemplo sintético con curaciones y «3.1k tokens». Si el archivo no existe la sección simplemente no aparece.

### 2.2 Triage de fallas con IA (`.github/scripts/triage.py`)

Un asesor, **nunca parte del quality gate**. Se ejecuta en el job `reportes`, antes de armar el sitio:

1. Si el run **no tiene fallas inesperadas**, no hace nada y no llama al modelo (un run verde cuesta 0).
2. Si las hay, arma un contexto de unos 700 tokens: la tabla del gate, cada falla con su mensaje y **lo que pasó con la misma prueba en las otras corridas del run**, la lista de defectos conocidos de `docs/defectos.md` y la nota de que DEF-15 causa la mayoría de las fallas intermitentes. La falla esperada de DEF-14 se excluye porque el pipeline la invierte a propósito.
3. Le pide a Claude (Sonnet 5.5, por la API de Anthropic) que clasifique cada falla como **defecto conocido** (citando el DEF-nn solo si lo respalda), **intermitente** o **nueva**, con evidencia y siguiente paso, y un veredicto de dos líneas.
4. Escribe `triage.md` y `triage.html` (enlazado desde la portada de Pages) y lo imprime en el resumen del run.

**Seguridad.** Sin el secreto `ANTHROPIC_API_KEY` (forks, PR, un repositorio sin configurar), sin fallas, o si la API falla, el paso se omite y avisa, y el run sigue igual (`continue-on-error` más salida con código 0). Solo usa la biblioteca estándar. La clave nunca se imprime.

**Para activarlo.** Maykol debe cargar `ANTHROPIC_API_KEY` en *Settings → Secrets and variables → Actions* del repositorio. Sin eso, el paso dice «Omitido».

**Costo medido:** un triage de una falla usó 2 273 tokens de entrada y 728 de salida: **≈ US$ 0,012** a precio de lista. Con unos 31 runs al mes, aun si todos fallaran, serían centavos.

**Resultado de la prueba.** Con los datos reales del run que falló (CP-W35 en 1 de 3 corridas) el modelo respondió:
- Clasificó la falla como **intermitente**, con la evidencia correcta: falló en la corrida 1 y pasó en la 2 y la 3 del mismo run.
- Señaló que el error era una lectura de `lista-categorias` que pudo ver el estado anterior, es decir, la huella de DEF-15, **pero no lo afirmó**: dijo que el mensaje no lo confirma.
- Reconoció lo que no podía concluir (el mensaje venía truncado y no tenía trazas).
- Explicó por qué el gate G4 quedó en rojo (49 de 50 casos estables) y dio un veredicto razonable: el run no se puede dar por bueno hasta tener 3 de 3.

Esa respuesta confirma lo que ya habíamos diagnosticado a mano.

## 3. Evaluado y descartado: Allure Agent Mode

Se probó `allure agent inspect` sobre los 394 casos de la API: en 2 s genera un `index.md`, una guía para agentes y un archivo por prueba. Se descartó: solo reordena datos que ya tenemos (el JUnit y la matriz), no trae modelo, y el único hallazgo propio fue informativo («el run no incluye logs globales»). Sus expectativas de evidencia (`--expect-steps`, `--expect-attachments`) no se activaron con nuestros datos. No agrega valor frente a la tabla del gate y la matriz de trazabilidad, así que no se dejó en el pipeline.

## 4. Límites

- **El triage no se probó contra la API real de Anthropic**, porque en la máquina de desarrollo no hay clave. Se probó de dos maneras: (a) con la CLI de Claude Code (`TRIAGE_BACKEND=cli`) sobre los datos reales de un run fallido, que valida el contexto y la respuesta; (b) contra un servidor que simula la API, que valida la ruta `/v1/messages`, las cabeceras (`x-api-key`, `anthropic-version`), el cuerpo y la lectura de la respuesta. La primera llamada real ocurrirá en el CI cuando exista el secreto.
- Solo se probó con **un** run fallido real. Los nombres de las pruebas web llegan sin tildes ni signos (el reporte JUnit los quita), y el mensaje de falla viene truncado.
- Es un asesor: puede equivocarse. Los criterios del gate siguen siendo deterministas.

## Fuentes

- WebdriverIO, *AI Service*: https://webdriver.io/docs/ai-service y `tests/e2e/node_modules/@wdio/ai-service/README.md`
- Anthropic, *Messages API*: https://docs.anthropic.com/en/api/messages
- Allure, *Agent Mode*: https://allurereport.org/docs/agent-mode/
- Qase, *IA en Qase*: https://docs.qase.io/en/articles/14442830-ai-in-qase · precios: https://qase.io/pricing
