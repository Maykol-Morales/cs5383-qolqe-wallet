# Comparativa: `browser.act`, Page Objects y un agente Claude para la misma tarea de UI

Medición del 2026-10-30, en una sola máquina Linux (Chromium 155 headless, Qolqe en `:8002` con BD propia). Datos crudos en `tests/e2e/benchmark/resultados.json`; scripts en `tests/e2e/benchmark/`.

**Tarea (la misma en los cuatro enfoques):** iniciar sesión como Ana (987654321 / PIN 4826), ir a Movimientos, crear la categoría "Viajes" en azul #1E88E5, clasificar el movimiento más reciente en "Viajes" con la nota "Pasaje a Cusco" y verificar que la fila lo muestre. Antes de cada corrida se reinician los datos (`DELETE /api/pruebas/reloj` y `POST /api/pruebas/reiniciar`).

| Enfoque | Qué se ejecutó |
|---|---|
| **A** `browser.act` en frío | `features/clasificar-ia.feature` con `benchmark/wdio.bench.conf.js`: caché vacía en `benchmark/__act__/` y modo `write`, así que el modelo graba los 4 `act`. Modelo `claude-sonnet-5`, temperature 1, igual que `wdio.conf.js`. |
| **B** `browser.act` desde la caché | El mismo escenario en modo `locked` (si falta la caché, falla y nunca llama al modelo), con la caché que grabó A. |
| **C** Page Objects clásicos | `features/clasificar.feature` (CP-W01), con el mismo navegador y la misma configuración. |
| **D** agente Claude ad hoc | `claude -p "<tarea>" --bare --output-format stream-json --allowedTools "Bash,Read,Write,Edit" --permission-mode acceptEdits`, desde un directorio vacío (`benchmark/correr-agente.sh`). El agente decide cómo hacerlo. Después de cada corrida se verifica por la API, con el token de Ana. |

## 1. Resultados

Para cada enfoque se muestra la mediana y, entre corchetes, el rango mín.–máx. El tiempo es de reloj y cubre toda la corrida: arranque de `wdio`, Chromium y el escenario. En D es el `duration_ms` del agente.

| Enfoque | n | Éxito | Tiempo (s) | Tokens de entrada | Tokens de salida | Llamadas al modelo | USD por corrida |
|---|---|---|---|---|---|---|---|
| A · act en frío (Sonnet 5) | 3 | 3/3 | **34,3** [32,0–39,3] | 137 397 [137 332–144 645] | 1 539 [1 496–1 640] | 16 [16–17] | **0,290** [0,290–0,306] |
| B · act desde caché | 3 | 3/3 | **6,8** [6,7–6,8] | 0 | 0 | 0 | **0** |
| C · Page Objects | 3 | 3/3 | **3,6** [3,56–3,59] | 0 | 0 | 0 | **0** |
| D · agente Claude, Sonnet 5 (comparable con A) | 3 | 3/3 | **98,1** [49,8–164,8] | 241 k en total [229–284 k]: 209 k leídos de caché y 31 k escritos en caché | 5 759 [4 149–8 195] | 17 turnos [15–18] | **0,359** [0,164–0,496] |
| D′ · agente sin la ruta del repo (Sonnet 5) | 3 | 3/3 | 166,5 [104,1–174,0] | 251 k [170–274 k] (225 k leídos de caché) | 6 851 [6 312–12 921] | 15 [13–21] | 0,354 [0,269–0,570] |
| D″ · agente, alias `sonnet` (resolvió a **Sonnet 5.5**) | 4 | 4/4 | 19,1 [16,9–30,0] | 24 k [20–53 k] | 1 473 [1 326–2 165] | 4,5 [4–7] | 0,037 [0,031–0,060] |

Detalle por `act` en A, en segundos (mediana de 3): login 10,1 · ir a Movimientos 4,6 · crear categoría 7,2 · clasificar 9,3. Cada `act` hizo entre 3 y 5 llamadas al modelo, de ~6–14 k tokens de entrada cada una. En B los mismos 4 pasos tardan 1,45 · 0,63 · 0,95 · 1,19 s. Tiempo del escenario sin el arranque, según Cucumber: A 32 s, B 4,5 s, C 1,4 s.

**Costos.** A usa los precios de lista de Claude Sonnet 5: US$ 2 por MTok de entrada y US$ 10 por MTok de salida (escritura de caché 1,25×, lectura 0,1×). Las tres corridas de A tuvieron 0 tokens de caché de prompt: `@wdio/ai-service` no marca `cache_control`. En D se usa el `total_cost_usd` que informa Claude Code, que en su mayor parte son lecturas de caché.

**Gasto total de la medición: US$ 3,26** (A 0,89 · D Sonnet 5 1,02 · D′ 1,19 · D″ 0,17).

## 2. Costo acumulado a N ejecuciones

A paga una sola vez, al grabar. Después, B repite gratis hasta que un cambio de la UI obliga a regrabar. La curación de nivel 1 (selectores alternativos o rol y nombre) no llama al modelo. La de nivel 2 sí, y cuesta como mucho lo que un `act` en frío. D paga en cada ejecución. C no consume tokens, pero los Page Objects los escribe una persona.

| Ejecuciones del pipeline | A + B (sin cambios de UI) | A + B, regrabando 1 de cada 10 | D Sonnet 5 (US$ 0,359 c/u) | D″ Sonnet 5.5 (US$ 0,037 c/u) | C |
|---|---|---|---|---|---|
| 1 | 0,29 | 0,29 | 0,36 | 0,04 | 0 |
| 10 | 0,29 | 0,58 | 3,59 | 0,37 | 0 |
| 100 | 0,29 | 3,19 | 35,90 | 3,69 | 0 |
| 1 000 | 0,29 | 29,30 | 359,04 | 36,93 | 0 |

**Punto de equilibrio.** Contra D en Sonnet 5, el mismo modelo que A, `act` sale más barato desde la **primera** ejecución (0,29 < 0,36). Contra D″ en Sonnet 5.5 se equilibra en 0,290 / 0,037 ≈ **8 ejecuciones**. En general, con k regrabaciones completas, A + B cuesta 0,29·(1 + k) y D″ cuesta 0,037·N. `act` gana mientras se regrabe menos de una vez cada ~8 corridas.

**Caso realista de CI**, con unos 20 push por semana (≈ 1 040 corridas al año) y una regrabación completa al mes por cambios de UI:

| | Costo al año | Minutos de CI al año para este escenario |
|---|---|---|
| A + B | ≈ US$ 3,8 (13 grabaciones) | ≈ 2 h (6,8 s por corrida) |
| D″ (Sonnet 5.5) | ≈ US$ 38 | ≈ 5,5 h |
| D (Sonnet 5) | ≈ US$ 373 | ≈ 28 h |
| C | US$ 0 | ≈ 1 h |

Esto es **un** escenario. Una suite de 50 escenarios multiplica la columna D por 50, mientras que A + B solo paga los escenarios que cambian.

## 3. Determinismo, fiabilidad y riesgos

**Resultado.** Los 10 agentes D quedaron bien según la verificación por la API: una categoría "Viajes" #1E88E5 con 1 movimiento y la nota correcta. Todos clasificaron la primera fila de la lista, que es lo mismo que hacen A, B y C. Sin embargo, el camino que siguieron no se repite de una corrida a otra:

- **Tiempo y costo muy variables.** Con Sonnet 5, D va de 50 a 165 s y de US$ 0,16 a 0,50, con 13 a 21 turnos. A varía menos del 6 % en tokens y B varía menos de 0,1 s.
- **Ningún D fue scraping a ciegas.** Las 7 corridas con traza leyeron los Page Objects del repo (`pages/*.js`) y usaron sus `data-testid`. D-1 lo dice en su propia respuesta; D-2 y D-3 se corrieron sin traza. En D′ no se le dio la ruta del repo, pero la encontró siguiendo el enlace `node_modules`. Por eso el costo de D es una **cota inferior**: sin una suite existente de la cual copiar, saldría más caro.
- **Atajos que no son automatizar la UI.** D-5, D-6 y D′-1 corrieron la suite que ya existe (`wdio run … features/clasificar.feature`) para resolver o verificar la tarea. D′-1 mezcló el script WebdriverIO con llamadas directas a la API. Las demás corridas usaron un script propio con `webdriverio.remote()` sobre la UI.
- **Efectos secundarios.** D-5, D-6, D′-2 y D′-3 llamaron por su cuenta a `POST /api/pruebas/reiniciar` y borraron datos. D′-3 lo admitió en su respuesta ("pensando que era un simple chequeo de salud"). D-5 y D′-1 dejaron scripts temporales dentro de `tests/e2e/` y luego los borraron. Ningún agente apuntó a los puertos de otros servidores.
- **Datos sensibles.** En D-5, D-6 y D′-3 el agente ejecutó `cat .env` y **vio la `ANTHROPIC_API_KEY`**, que así llegó al contexto del modelo. En las trazas guardadas la clave quedó redactada y `benchmark/crudo/` está en `.gitignore`. Además, D siempre ve el PIN en claro porque va en el prompt. `browser.act` usa placeholders (`{{celular}}`, `{{pin}}`) que no se envían al modelo ni se guardan en la caché.
- **Hallazgo funcional.** D′-1 notó por su cuenta que la lista no muestra el movimiento de hoy. Es DEF-07: el historial excluye el día `hasta`. Por eso el "más reciente" de la UI es el pago de ayer y no la recarga de hoy, en los cuatro enfoques.

**Fiabilidad de la caché de `act`.**

- La caché commiteada se identifica por el **título del escenario**. Cuando el otro agente renombró el escenario a `CP-W90 · …`, la repetición en modo `locked` falló con *"no cached steps for CP-W90 · …"*.
- En modo `auto` con clave, ese renombre provoca una regrabación silenciosa que gasta tokens. En la CI (`heal`) graba en `outputDir` en cada corrida.
- El contenido de la caché sigue siendo válido: con las claves renombradas repitió 4/4 desde caché en 7,0 s.
- El otro agente ya regrabó `features/__act__/clasificar-ia.feature.json` con las claves nuevas. Este benchmark no tocó ese archivo: usó `benchmark/__act__/`.

**Mantenibilidad y uso en CI.**

- **B y C** son deterministas, no necesitan secretos y ocupan unos 4–7 s.
- **B** necesita la clave solo para regrabar. Cuando la UI cambia, la curación de nivel 1 es gratis, y la verificación de efectos (`effects: strict`) impide que un paso curado "haga otra cosa" sin avisar.
- **C** exige mantener los Page Objects a mano, pero es lo más rápido (3,6 s) y lo más fácil de depurar.
- **D** en la CI necesita la clave como secreto en cada corrida, y su duración y su costo son impredecibles. Además puede tocar datos, archivos y secretos fuera de la tarea.

## 4. Conclusión

- **Page Objects (C)**: la regresión que corre en cada push. Es el más rápido (3,6 s), cuesta 0 tokens, es determinista y no usa secretos.
- **`browser.act` (A → B)**: conviene cuando escribir el flujo cuesta más que US$ 0,29. Graba una vez en ~34 s y luego repite en 6,8 s gratis. Hay que versionar la caché y no renombrar los escenarios sin regrabar. Mientras se regrabe menos de una vez cada ~8 corridas, es más barato que cualquier agente.
- **Agente Claude (D)**: sirve para explorar, para generar o depurar pasos y para encontrar defectos (D′-1 encontró DEF-07), no como suite de regresión. Con Sonnet 5 cuesta US$ 0,36 y ~98 s por corrida. Con Sonnet 5.5 cuesta US$ 0,04 y ~19 s, pero sigue sin ser determinista. En esta medición leyó el `.env` y reinició datos por su cuenta.

## Fuentes

- WebdriverIO, *AI Service* (`browser.act`, modos de caché, curación, `ai:act`): https://webdriver.io/docs/ai-service y `tests/e2e/node_modules/@wdio/ai-service/README.md` (v10.1.0).
- WebdriverIO, *AI Steps in Tests*: https://webdriver.io/docs/ai-steps
- Anthropic, *Pricing*: https://platform.claude.com/docs/en/about-claude/pricing. Precios de Sonnet 5 y 5.5 tomados de la tabla de modelos del skill `claude-api` (caché del 2026-09-25): US$ 2 / 10 por MTok, lectura de caché 0,1×, escritura de 5 min 1,25×.
- Anthropic, *Prompt caching*: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- Claude Code, modo headless (`claude -p`, `--output-format`, `--bare`): https://code.claude.com/docs/en/headless

## Cómo reproducir

```bash
cd tests/e2e   # Qolqe en :8002 con QOLQE_MODO_PRUEBA=1; ANTHROPIC_API_KEY en .env
export QOLQE_URL=http://localhost:8002 CHROME_BIN=/usr/bin/chromium
benchmark/correr.sh A 3 && benchmark/correr.sh B 3 && benchmark/correr.sh C 3
MODELO=claude-sonnet-5 benchmark/correr-agente.sh 3 /tmp/agente   # CIEGO=1 para D′
python3 benchmark/resumir.py   # → benchmark/resultados.json
```
