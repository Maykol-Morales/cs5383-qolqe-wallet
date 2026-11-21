# IA en el ciclo automático de pruebas

Pedido de la entrega final: agregar al ciclo automático alguna herramienta de IA que facilite el flujo o haga algo interesante, aprovechando **las herramientas que ya manejamos**. Lo que se eligió es usar el **MCP de WebdriverIO** dentro del ciclo, con un agente de Claude que explora la interfaz buscando defectos nuevos. Investigación y pruebas del 2026-11-21.

## 1. Qué IA trae cada herramienta

| Herramienta | IA que incluye | Decisión |
|---|---|---|
| **WebdriverIO** (MCP `@wdio/mcp`) | Servidor MCP con 42 herramientas para que un agente maneje el navegador | **Se usa en el ciclo** (sección 2.1) |
| **WebdriverIO** (`@wdio/ai-service` 10.1.0) | `browser.act()` con caché; curación de pasos en 2 niveles con evidencia; verificación de efectos; `extract`; `wdio-ai eject` | **Se usa** (escenario `@ia`, CP-W90) y se **muestra** en el dashboard (sección 2.2) |
| **Allure 3** | *Agent Mode*: ordena un run (Markdown y JSON) para que un agente externo lo lea; no trae modelo | Probado y descartado (sección 3) |
| **Qase** | IA para generar casos; según su [página de precios](https://qase.io/pricing) no está en el plan gratuito | No se puede usar |
| **k6**, **Schemathesis** | No investigados | — |

## 2. Lo que quedó en el pipeline

### 2.1 Exploración con IA: el MCP de WebdriverIO dentro del ciclo

Un job aparte del workflow (`exploracion` en `.github/workflows/pruebas.yml`) lanza un agente de Claude Code que **solo** tiene las herramientas del MCP de WebdriverIO y explora la interfaz de Qolqe buscando comportamientos que contradigan las reglas de negocio. Es la sesión exploratoria de `comparativa-mcp-agentes.md` §6, ahora automatizada.

- **Qué hace:** levanta Qolqe en el runner, arranca el agente (Chrome headless, tope de US$ 1,50 por sesión) y le pasa un resumen de las reglas y la **lista de defectos ya conocidos** de `docs/defectos.md`, para que busque cosas distintas. Devuelve un arreglo JSON de hallazgos. `.github/scripts/exploracion.py` lo convierte en un resumen del run (tabla de hallazgos y el costo de la sesión) y el crudo se sube como artefacto `exploracion`.
- **Cuándo corre:** solo a pedido. *Actions → Pruebas → Run workflow* con la casilla `exploracion` marcada. Cuesta unos US$ 0,5 por sesión, así que no corre en cada push, y no forma parte del quality gate ni del job `reportes` (si falla o se omite no afecta nada).
- **Qué necesita:** el secreto `ANTHROPIC_API_KEY` en el repositorio (*Settings → Secrets and variables → Actions*). Sin él, el job termina bien y deja en el resumen «Omitida: falta el secreto».
- **Qué entrega (diseño final):** el agente reporta todo lo que encuentra y marca en cada hallazgo el DEF-nn que reconoce (o `null` si es distinto). El resumen del run separa los **posiblemente nuevos** de los **ya conocidos que reconfirmó**.
- **Probado en local** (el mismo flujo que correrá el CI, con la CLI de Claude y la sesión iniciada, 2026-11-21):
  - *Primer diseño* (se le pide buscar **solo cosas nuevas**): 4 minutos, 124 turnos, US$ 0,85, devolvió `[]`. Es un resultado honesto, pero un resumen que siempre diga «nada» no demuestra que el agente funciona, así que se cambió.
  - *Diseño final* (reporta todo y marca los conocidos): 2,5 minutos, 82 turnos, **US$ 0,49**, 4 hallazgos marcados como DEF-01, DEF-02, DEF-03 y DEF-06 y **0 posiblemente nuevos**. Se verificó cada marca: DEF-01 es la comisión de S/ 71.00 (`1.06` en vez de `1.07`), el mismo ejemplo de `docs/defectos.md`; DEF-06, DEF-02 y DEF-03 se reprodujeron por API.
  - La sesión de `comparativa-mcp-agentes.md` §6 (sin lista) halló DEF-02, 03, 06 y 07. Entre las dos sesiones se cubren 5 de los 8 defectos alcanzables por interfaz (01, 02, 03, 06 y 07): **una sola sesión no es exhaustiva y cada una encuentra algo distinto**, así que conviene repetirla.
- **Cómo leer lo que entrega:** los hallazgos son **candidatos**. Un agente puede equivocarse; hay que reproducirlos a mano contra la API antes de registrar un defecto, como se hizo con los cuatro de la sesión de `comparativa-mcp-agentes.md`.

### 2.2 La IA de WebdriverIO, visible en el dashboard del run

El escenario `@ia` pide los pasos al modelo una sola vez y los repite desde la caché versionada. Al terminar, `@wdio/ai-service` imprime un resumen (`4 act calls · 4 from cache · 0 healed … · 0 tokens`) que antes se perdía en el log. El job `web` guarda esa consola (`tee` → `reportes/ia-consola.txt`) y `reportes.py` publica en `dashboard.html` la sección **«IA en el ciclo: WebdriverIO (browser.act)»**: llamadas de IA, cuántas salen de la caché, pasos curados sin modelo y por el modelo, grabados por el modelo, tokens y la lista de pasos curados.

- **Qué significa:** en el CI no hay clave de API, así que solo puede curar sin modelo. «0 tokens» quiere decir que nadie gastó. Si la interfaz cambiara, ahí se vería cuántos pasos se curaron antes de que la prueba falle.
- **Comprobado en el sitio publicado:** muestra 4 llamadas, 4 desde la caché y 0 tokens.

## 3. Evaluado y descartado

- **Allure Agent Mode.** Se probó `allure agent inspect` sobre los 394 casos de la API: en 2 s genera un `index.md`, una guía para agentes y un archivo por prueba. Solo reordena datos que ya tenemos (el JUnit y la matriz), no trae modelo y su único hallazgo fue informativo. Sus expectativas de evidencia no se activaron con nuestros datos. No se dejó en el pipeline.
- **Triage de fallas con Claude.** Se construyó y se subió un paso que clasificaba las fallas de un run (defecto conocido, intermitente o nueva). Con los datos reales de un run que falló clasificó bien CP-W35 como intermitente (≈ US$ 0,012 por triage), pero no era lo que se quería para el ciclo, que era usar el MCP, y se **retiró**.

## 4. Límites

- **Primera ejecución en el CI** (run 44864757692, lanzado a mano el 2026-11-21): Chrome headless del MCP y la instalación de Claude Code funcionaron en el runner de Linux (184 s, 70 turnos, ≈ US$ 0,41) y el resumen quedó en el run. El primer intento había fallado con código 126 porque `explorar.sh` no tenía permiso de ejecución en git (se corrigió; no llegó a llamar al modelo). **La marca del agente no es del todo fiable.** De sus 5 entradas, 3 eran reconfirmaciones correctas (DEF-01, DEF-06 y DEF-07), una era **DEF-14 marcado como «nuevo»** (a las 23:10 de Lima el runner, en UTC, ya está en el día siguiente y el historial pide un `hasta` futuro: es exactamente DEF-14, aunque el agente escribió que «no coincide») y otra **no era un hallazgo** (un resumen de las reglas que sí se cumplen). Verificado a mano: **0 defectos nuevos**. Por eso el resumen advierte que hay que reproducir cada hallazgo antes de registrarlo.
- Una sola sesión por ejecución y un solo modelo: otra sesión puede encontrar otras cosas, y el agente puede reportar falsos positivos.
- Es una exploración: no sustituye a la suite automática, que detecta los defectos conocidos de forma determinista y gratis.

## Fuentes

- WebdriverIO, *MCP*: https://webdriver.io/docs/mcp · *AI Service*: https://webdriver.io/docs/ai-service
- Allure, *Agent Mode*: https://allurereport.org/docs/agent-mode/
- Qase, *IA en Qase*: https://docs.qase.io/en/articles/14442830-ai-in-qase · precios: https://qase.io/pricing
