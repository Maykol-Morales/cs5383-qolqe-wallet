# Conector MCP de WebdriverIO frente a un agente de código: tokens, precio y si vale la pena

Pedido de la entrega final: comparar la capacidad de IA del **conector MCP de WebdriverIO** con usar **agentes de código directamente** (Claude Code) y ver, con tokens y precio, si su uso vale la pena. Medición del 2026-11-21; datos crudos en `tests/e2e/benchmark/mcp/` (`crudo/`, `resultados.json`).

Es una comparación distinta de `docs/comparativa-ia.md`, que mide `browser.act()` (`@wdio/ai-service`, un servicio de IA *dentro* de WebdriverIO). Aquí el modelo es un agente externo que maneja el navegador.

## 1. Qué es cada enfoque

WebdriverIO documenta dos formas de que un agente de código maneje un navegador ([IA para agentes de código](https://webdriver.io/docs/ai-agents)): la CLI `wdio session` ("la forma por defecto") y el servidor MCP como alternativa "cuando el agente debe llamar herramientas en vez de la terminal". Se midieron además una tercera, la más libre, y una cuarta, la integración **Claude in Chrome** (la extensión de Chrome que usa el propio Claude Code).

| Enfoque | Qué recibe el agente |
|---|---|
| **E · MCP** (`@wdio/mcp` 4.1.0, MIT, 1,2 MB sin comprimir) | Solo las herramientas del servidor: 17 visibles al arrancar (la documentación habla de 42 en total; el resto se activa con `enable_tools`). Sin terminal. Lee la página como árbol de accesibilidad con referencias (`snapshot`) y actúa con `click_element`, `set_value`, `perform_actions`… |
| **F · `wdio session`** (CLI de `@wdio/cli` 10.1.0) | Solo Bash limitado a `wdio session …` y Read, más la skill que instala `wdio session skill --install`. Una acción por comando, encadenables con `&&`. |
| **D · scripts propios** | Bash, Read, Write y Edit, y WebdriverIO en `node_modules`. El agente escribe y corre su propio script. |
| **G · Claude in Chrome** (`--chrome`) | Solo las 20 herramientas de la extensión: pestañas, `navigate`, `computer` (capturas de pantalla y clics por coordenadas), `find`, `form_input`, `get_page_text`, `javascript_tool`… Maneja el **Chrome real del usuario**, no uno headless. No necesita código ni descargar nada. |

**Tarea** (la misma de `comparativa-ia.md`): iniciar sesión como Ana, ir a Movimientos, crear "Viajes" en azul #1E88E5, clasificar el movimiento más reciente con la nota "Pasaje a Cusco" y verificar la fila. Qolqe se reinicia antes de cada corrida y el resultado se verifica por la API, no por lo que dice el agente.

## 2. Método

`claude -p` con salida `stream-json` (tokens y `total_cost_usd` salen del último evento), el mismo modelo en todas (`claude-sonnet-5-5`), 3 corridas por enfoque, directorio de trabajo vacío fuera del repo, sin ajustes de usuario ni otros servidores MCP, sin skills y con un tope de US$ 1,50 por corrida (`benchmark/mcp/correr.sh`). Además, una corrida **base** por configuración con un prompt trivial ("responde listo") que mide el costo fijo. G se corrió con `--chrome` en el Chrome real (abre una pestaña nueva y la cierra al terminar; la extensión sí tenía permiso para `localhost`). El costo en dólares es el que informa Claude Code a **precio de lista**; en esta medición se facturó contra una sesión iniciada, no contra una clave de API.

## 3. Resultados

Mediana y, entre corchetes, el rango mín.–máx. de 3 corridas. "Contexto total" suma los tokens de entrada de todos los turnos (en su mayoría lecturas de caché).

| Enfoque | Éxito | Tiempo (s) | Turnos | Llamadas a herramientas | Contexto total (tokens) | Salida (tokens) | USD por corrida |
|---|---|---|---|---|---|---|---|
| **E · MCP** | 3/3 | **24** [14–24] | **17** [9–18] | 16 [8–17] | **177 604** [86 388–192 683] | 1 496 [896–1 640] | **0,078** [0,056–0,079] |
| **F · `wdio session`** | 3/3 | **45** [44–46] | **10** [9–11] | 9 [8–10] | **96 161** [96 109–111 483] | **853** [795–861] | **0,067** [0,065–0,069] |
| **D · scripts propios** | 3/3 | **42** [42–46] | **9** [8–11] | 8 [7–10] | **99 159** [84 315–110 377] | 3 351 [3 059–3 471] | **0,103** [0,099–0,104] |
| **G · Claude in Chrome** | 3/3 | **87** [66–99] | **30** [29–34] | 29 [28–33] | **296 784** [262 830–394 150] | 3 718 [3 653–4 135] | **0,140** [0,133–0,170] |

**Costo fijo** (corrida base): G 15 002 tokens, E 9 503 (US$ 0,038), D 6 478 (US$ 0,011), F 5 894 (US$ 0,011). Declarar el MCP de WebdriverIO suma **unos 3 000 a 3 600 tokens fijos** por turno (los esquemas de las 17 herramientas); la extensión de Chrome suma **unos 8 500 a 9 000** (20 herramientas con descripciones largas y sus instrucciones de uso). La diferencia en dólares de la base es mayor que la de tokens porque la primera llamada escribe la caché a 2× el precio de entrada.

**Qué dicen los datos**
- **Dólares.** D es claramente el más caro (0,103, sin solaparse con los otros dos): escribe el script, y por eso 3,4 mil tokens de salida a US$ 10 por MTok. E y F se solapan (0,056–0,079 frente a 0,065–0,069), así que **entre el MCP y la CLI no hay diferencia de precio demostrable** con 3 corridas.
- **Tokens.** E consume casi el doble de contexto (177 k frente a ~96–99 k). No es porque sus respuestas sean grandes: un `snapshot` promedia ~1 200 caracteres y el de mayor tamaño 4 000, frente a ~1 900 en F y ~2 500 en D. Es porque hace **más llamadas y más chicas**: cada acción es una llamada (16 llamadas en 17 turnos, casi una por turno), y cada turno vuelve a leer todo el contexto anterior. F encadena varias acciones con `&&` en un solo comando (9 llamadas) y D hace todo en un script (8 llamadas), así que necesitan la mitad de turnos.
- **Tiempo.** E es el más rápido (24 s frente a 42–45): cada acción es una llamada a una sesión ya abierta, sin arrancar un proceso por comando.
- **Variabilidad.** E es la más irregular (9 a 18 turnos, US$ 0,056 a 0,079); F y D son muy estables.
- **Cómo lo hace.** E casi siempre repite *snapshot → click*: 14 `snapshot` y 11 `click_element` en 3 corridas. Nunca pidió una captura de pantalla.
- **Claude in Chrome (G) cuesta más y es más lento que todos:** US$ 0,140 por corrida, es decir **+79 % frente al MCP de WebdriverIO, +109 % frente a la CLI y +36 % frente a los scripts**, sin solaparse con ninguno (0,133–0,170), y 87 s (3,6 veces lo que tarda E). Usa además el mayor contexto (297 k tokens) y el mayor costo fijo (15 k).
  - **No son las capturas lo que más pesa.** El modelo recibió solo 5 a 7 imágenes por corrida (siempre `computer: screenshot`, salvo un `zoom`). Lo que pesa es el número de pasos: 29 llamadas y 30 turnos, de las cuales **19 a 21 son acciones de `computer`** (clic, escribir o desplazarse, una por una y por coordenadas, con una captura entre medias), y esos pasos se suman al costo fijo más grande.
  - **Lo que da a cambio:** es el único enfoque que ve la pantalla como un usuario, no necesita escribir ni instalar nada y trabaja con el navegador y la sesión reales. Por eso mismo es el más intrusivo: abre pestañas en tu Chrome y depende del permiso de la extensión para cada sitio.

**Costo acumulado** (mediana × N; el Page Object clásico y `browser.act` desde la caché cuestan 0 tokens por ejecución, ver `comparativa-ia.md`):

| Ejecuciones | E · MCP | F · `wdio session` | D · scripts | G · Claude in Chrome |
|---|---|---|---|---|
| 1 | US$ 0,08 | US$ 0,07 | US$ 0,10 | US$ 0,14 |
| 10 | US$ 0,78 | US$ 0,67 | US$ 1,03 | US$ 1,40 |
| 100 | US$ 7,80 | US$ 6,70 | US$ 10,30 | US$ 14 |
| 1 000 | US$ 78 | US$ 67 | US$ 103 | US$ 140 |

## 4. ¿Vale la pena?

- **Como regresión en cada push: no.** Cualquiera de los tres paga tokens en cada ejecución y no es determinista; el Page Object clásico (3,6 s, 0 tokens) y `browser.act` desde la caché (6,8 s, 0 tokens) siguen siendo la opción.
- **Para explorar la interfaz, encontrar selectores y escribir pruebas: sí.** Una tarea cuesta de 7 a 10 centavos de dólar a precio de lista, mucho menos que el tiempo de una persona. WebdriverIO recomienda justamente ese uso: explorar con el agente, proponer selectores y luego escribir la especificación.
- **Cuál elegir.**
  - **MCP** si importa la interactividad y la velocidad (24 s). Cuesta lo mismo que la CLI, pero es más irregular y carga unos 3 mil tokens fijos por turno. Necesita un cliente MCP y descargar el paquete con `npx`.
  - **`wdio session`** si se quiere lo más barato y lo más predecible (0,067, 10 turnos, 853 tokens de salida). Es la opción que la propia documentación llama "por defecto", no requiere servidor y puede exportar los pasos a una especificación (`wdio session export`; no se probó aquí).
  - **Scripts propios** si se quiere el máximo control o un script reutilizable: es el más caro por corrida entre los tres enfoques de WebdriverIO (0,103) y tuvo fricción de permisos, pero deja un archivo que se puede repetir gratis.
  - **Claude in Chrome** para una revisión visual puntual o para probar algo sin escribir código ni montar nada. Es el más caro (0,140) y el más lento (87 s), y toca tu navegador real; no conviene para repetirlo ni para automatizar.
- **Un matiz de precio.** El servidor MCP es gratuito (MIT); lo que se paga son los tokens del modelo. Con un plan de Claude Code no hay cargo por token, pero el costo equivalente a lista es el de las tablas.

## 5. Limitaciones y problemas de la medición

- **Pocos datos.** n = 3, una sola tarea, un solo modelo (Sonnet 5.5), Windows y WebdriverIO 10.1. Las diferencias de unos centavos entre E y F están dentro del ruido.
- **Contaminación en F (tanda 1).** `wdio session` mantiene el Chrome vivo entre corridas: F-2 reutilizó la sesión de F-1 y dijo "yo no hice los pasos" (no verificó). Se repitió F con `wdio session close` antes y después de cada corrida; la primera tanda se conserva como `F0-*` en `crudo/`. Con la tanda 1, F habría salido 2/3 y más barata (US$ 0,065).
- **Permisos en D.** En cada corrida de D se denegó un comando de Bash (un redireccionamiento y un `cd`), lo que costó un turno extra. D tiene, por eso, algo de sobrecosto.
- **No se usó `--bare`**, que exige una clave de API; el costo fijo que queda (memoria de usuario) lo mide la corrida base y es parecido en los tres. No se probaron las otras herramientas del MCP (capturas, exportar pasos, móvil) ni el servidor de documentación.
- **Distinto de `comparativa-ia.md`.** Allí un agente con el repo a la vista costó US$ 0,037 con Sonnet 5.5 porque leyó los Page Objects y reutilizó sus `data-testid`; aquí ningún agente tiene el repo, por eso D cuesta más. No son cifras comparables entre documentos.
- **G no es comparable en el entorno.** Corre en tu Chrome real, con ventana y con la extensión, mientras que E, F y D usan Chrome headless con Qolqe local; parte de sus 87 s es la propia ventana. Tampoco se probó pedirle que prefiera texto a capturas, que podría abaratarlo.
- **Gasto de la medición:** US$ 1,91 a precio de lista: 12 corridas de la tarea, 3 de la tanda contaminada de F, 4 bases (US$ 1,42, 19 corridas) y la sesión exploratoria de la sección 6 (US$ 0,49).

## 6. Uso real: una sesión exploratoria con el MCP

Para que el análisis no quede solo en una tarea de laboratorio, se usó el MCP de WebdriverIO en el trabajo propio de pruebas: una **sesión exploratoria** (`benchmark/mcp/explorar.sh`, con el prompt versionado en `explorar-prompt.md`). El agente (Claude Code, Sonnet 5.5, solo con las herramientas del MCP, Chrome headless y un tope de US$ 1,50) explora la interfaz de Qolqe buscando comportamientos que contradigan las reglas de negocio. Recibe un resumen de esas reglas y los usuarios semilla, pero **no se le dice cuáles son los defectos conocidos**.

**Costo de la sesión:** 153 s, 79 turnos, 78 llamadas (28 `click_element`, 27 `perform_actions`, 9 `set_value`, 7 `navigate`, 5 `snapshot`, 1 `get_screenshot`), 1,9 millones de tokens de contexto (casi todo lecturas de caché) y 10,5 mil de salida: **US$ 0,49**. Sin permisos denegados.

**Qué encontró.** Cuatro hallazgos; cada uno se reprodujo después a mano contra la API de un servidor limpio:

| # | Hallazgo del agente, en la interfaz | Defecto conocido | Reproducido |
|---|---|---|---|
| 1 | Transferir a Fabián (cuenta cerrada) se acepta y descuenta S/ 10.00 | **DEF-06** (Crítica) | Sí: `201` |
| 2 | Con dos PIN malos, un ingreso exitoso y un PIN malo más, la cuenta se bloquea (el conteo no se reinició) | **DEF-03** (Alta) | Sí: `401`, `401`, ingreso, `423` |
| 3 | El registro acepta el PIN 4321 (secuencia descendente) | **DEF-02** (Media) | Sí: `201` |
| 4 | La tabla de Movimientos no muestra los movimientos de hoy, pero el inicio sí | **DEF-07** (Alta) | Sí: 0 de hoy en la lista |

**Cómo leerlo**
- **Precisión:** 4 de 4 hallazgos son correctos (ningún falso positivo), pero **los 4 ya estaban en nuestra lista**: no encontró ningún defecto nuevo.
- **Cobertura de lo conocido:** de los 8 defectos que considero alcanzables desde la interfaz en una sola sesión (DEF-01, 02, 03, 04, 06, 07, 10 y 13) halló 4 (02, 03, 06 y 07). Se le pasaron DEF-01 (comisión que no redondea 0.005), DEF-04 (saldo negativo con comisión), DEF-10 (nombre repetido al editar una categoría) y DEF-13 (límite diario con transferencias interbancarias): justo los que piden hacer cuentas o repetir operaciones. Los demás (05, 08, 09, 12, 14, 15, 16) no se alcanzan con una sesión de interfaz. «Alcanzable» es juicio propio.
- **Qué aporta:** una validación independiente. Un agente al que no se le dijo qué buscar redescubrió 4 defectos en 2,5 minutos, a unos US$ 0,12 por defecto. Es **complementario, no un reemplazo**: la suite automática detecta los 16 de forma determinista y gratis en cada run.
- **Dónde encaja:** antes de escribir pruebas (para decidir qué automatizar) y para revisar pantallas nuevas, no como regresión. Esta sesión cuesta unas 6 veces la tarea de la sección 3 porque explora más.
- **Límites:** n = 1 (otra sesión puede encontrar otras cosas), el resumen de reglas condiciona lo que busca, y al no haber hallazgos nuevos no se pudo medir su capacidad de descubrir.

## Fuentes

- WebdriverIO, *MCP*: https://webdriver.io/docs/mcp · *FAQ*: https://webdriver.io/docs/mcp/faq · *WebdriverIO para agentes de código*: https://webdriver.io/docs/ai-agents
- Presentación del MCP: https://webdriver.io/blog/2026/02/04/introducing-webdriverio-mcp · repositorio: https://github.com/webdriverio/mcp · paquete: `@wdio/mcp` en npm
- La documentación oficial no publica cifras de tokens ni de costo, ni compara el MCP con `wdio session` o con scripts; las cifras de arriba son propias.
- Claude Code, modo headless: https://code.claude.com/docs/en/headless

## Cómo reproducir

```bash
cd tests/e2e   # Qolqe en :8002 con QOLQE_MODO_PRUEBA=1 y una BD temporal; sesión de Claude Code iniciada
export QOLQE_URL=http://localhost:8002
benchmark/mcp/correr.sh base-E 1 && benchmark/mcp/correr.sh base-D 1 && benchmark/mcp/correr.sh base-F 1 && benchmark/mcp/correr.sh base-G 1
benchmark/mcp/correr.sh E 3 && benchmark/mcp/correr.sh F 3 && benchmark/mcp/correr.sh D 3
benchmark/mcp/correr.sh G 3   # con la extensión Claude in Chrome conectada; abre pestañas en tu Chrome (INICIO=2 continúa desde la corrida 2)
python benchmark/mcp/resumir.py   # → benchmark/mcp/resultados.json y la tabla
```
