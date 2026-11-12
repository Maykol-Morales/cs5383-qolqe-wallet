# Comparativa de herramientas de rendimiento (Parte 3)

Cómo expresa cada herramienta lo que pide **este** requerimiento ("Quincena Qolqe", `pdfs/P2_Parte3_Enunciado.pdf`), no una comparación genérica. Candidatas: las que nombra el enunciado (k6, JMeter, Gatling, Locust, Artillery, Taurus). Elegida: **k6**. Fecha: 2026-11-11.

## 1. Por necesidad del requerimiento

| Necesidad (de dónde sale) | k6 | JMeter | Gatling | Locust | Artillery |
|---|---|---|---|---|---|
| **p95 por tipo de operación** como criterio de paso ("95 % < 800 ms" consultas, "< 1.5 s" dinero) | `thresholds` sobre una etiqueta: `http_req_duration{tipo:dinero}` p(95) < 1500; sale ≠ 0 | Sin criterio de paso por percentil nativo: el dashboard HTML informa, no falla. Hace falta Taurus (`passfail`) o un plugin | `assertions`: `responseTime().percentile(95).lt(1500)` global o por grupo de peticiones | Sin umbrales: se programan en el evento `quitting` leyendo `stats` | `ensure` con p95 global; por endpoint hace falta un plugin |
| **Modelo abierto** ("3 000 sesiones por hora … sin acumular retrasos") | `ramping-arrival-rate`; los retrasos salen en `dropped_iterations` | Open Model Thread Group (5.5, marcado experimental) | Nativo: `injectOpen` | Cerrado por defecto; `constant_pacing` lo aproxima con pausas adaptativas | Nativo: `arrivalRate` por fase |
| **Usuarios simultáneos** (pico de 300, estrés hasta 1 000) | `ramping-vus` | Thread Group | `injectClosed` | Nativo (`-u`, `LoadTestShape`) | Indirecto: se deriva de la tasa de llegada |
| **Pesos 30/15/15/…, pausa 10–25 s (media 18 s), id único por operación de dinero** | Código JS | JSR223/Groovy o varios controladores anidados | Código JS/TS, Java, Scala o Kotlin | Código Python (`@task(peso)`) | YAML + funciones JS para lo que no es `think` fijo |
| **4xx de negocio aparte de las fallas** (enunciado §5) | `responseCallback` + `Counter` por `codigo` | Response Assertion + listener propio | `check(status.in(…))` + grupos | `catch_response` | Se cuentan por código; no se separan de los errores sin código propio |
| **Generador liviano** (si pasa de ~80 % de CPU la corrida no vale) | Go; con 100 VUs usó **2,6 % de CPU** (medido) | Un hilo de JVM por usuario: con 1 000 VUs, ~1 000 hilos | Muy eficiente (Netty, JVM) | Gevent: un núcleo por proceso, varios workers para mucha carga | Node, un hilo: satura antes |
| **Reporte con gráficos** (rúbrica: resultados con gráficos) | Dashboard web en vivo + HTML exportado | `-e -o` genera dashboard HTML | Reporte HTML muy completo | `--html` | JSON; el reporte visual bueno está en su nube |
| **Lenguaje del equipo** | JS (el E2E de la §3 también es JS) | GUI + XML (`.jmx`) | JS/TS desde 2024 (corre en la JVM) | Python (como Qolqe y `datos.py`) | YAML + JS |
| Licencia | AGPL-3.0 | Apache 2.0 | Apache 2.0 (Community) | MIT | MPL-2.0 |

**Taurus** no es un generador: es una capa YAML que corre JMeter, Gatling, Locust o k6 por debajo y les agrega `passfail` (por ejemplo `p95>800ms for 30s, stop as failed`). Sirve para ponerle umbrales a JMeter. Con k6 no hace falta, porque k6 ya los trae.

## 2. Decisión

Dos herramientas cubren bien el requerimiento: **k6** y **Gatling**. Las dos tienen modelo abierto nativo y umbrales por percentil. Elegimos k6 por tres razones:

1. **Un umbral por etiqueta.** El requerimiento separa consultas y dinero. En k6 es una etiqueta (`tipo`) y dos líneas de `thresholds`. En Gatling hay que agrupar las peticiones y aserciones por grupo.
2. **Montaje mínimo.** k6 es un binario (`~/.local/bin/k6`). Gatling JS necesita Node más una JVM que baja su CLI.
3. **Dashboard en vivo.** Sirve para la demo de la exposición sin herramientas extra.

Las otras quedan descartadas por un hueco concreto frente al requerimiento:
- **JMeter**: no tiene criterio de paso por percentil sin Taurus. El modelo abierto es experimental. La lógica de sesión (pesos, pausa triangular, ids) va en Groovy dentro de un XML difícil de revisar.
- **Locust**: su modelo es cerrado ("sin acumular retrasos" no se observa directamente). Tampoco trae umbrales. A favor tiene que usa Python, el lenguaje del SUT.
- **Artillery**: su modelo es abierto, pero los umbrales por endpoint necesitan plugin y el generador es de un solo hilo.

## 3. Limitaciones de k6 que encontramos

- No mide el servidor. CPU y memoria se miden con `monitor.py` (psutil) y el cuello de botella con py-spy.
- El runtime no es Node: no hay paquetes npm. La pausa triangular, los pesos y los ids se escribieron a mano, unas 20 líneas.
- Los 4xx cuentan como falla por defecto. Hubo que declarar `http.setResponseCallback(expectedStatuses({min: 200, max: 499}))` y contarlos aparte.
- La integridad del dinero no se puede ver desde k6. Se verifica después contra la BD (`datos.py verificar`), cruzando los ids que k6 registró.

## 4. Medición propia: CPU del generador, k6 frente a Locust

Mismo escenario en las dos herramientas (`tests/performance/comparativa/`: `saldo.js` y `locustfile.py`):
- 100 usuarios que entran en 50 s y hacen login una vez.
- Después, `GET /api/cuentas/me/saldo` cada 1 s durante 2 min.
- Mismo Qolqe (Docker, 1 núcleo) y BD preparada antes de cada corrida.
- CPU medido con `monitor.py` sobre el proceso del generador, en la meseta (los 100 usuarios ya dentro).

Se corre con `tests/performance/comparativa/correr.sh`. Resultados en `tests/performance/resultados/comparativa-20261111-2236/`:

| Generador | Peticiones | p95 medido | CPU del generador |
|---|---|---|---|
| k6 1.3.0 | 14 561 | 11 ms | **5,2 %** |
| Locust 2.47.0 (1 proceso) | 14 471 | 17 ms | **14,0 %** |

**Lectura:**
- Para la misma carga (~85 req/s), **Locust gasta unas 2,7 veces más CPU que k6**.
- Un proceso de Locust usa un solo núcleo. A este ritmo, se saturaría cerca de 600 req/s (extrapolación lineal), y por encima habría que repartir la carga entre varios workers.
- Para nuestro estrés (~27 req/s) cualquiera de los dos alcanza. La diferencia importa porque el generador corre en la misma laptop que Qolqe: cada punto de CPU del generador se le quita al sistema que se mide.
- El p95 que informa Locust es 6 ms mayor para las mismas respuestas: mide también el tiempo del cliente Python (`requests` + gevent).

## Fuentes

- k6, executors y thresholds: https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/ · https://grafana.com/docs/k6/latest/using-k6/thresholds/
- Gatling, SDK de JavaScript y modelos de carga: https://docs.gatling.io/tutorials/test-as-code/javascript/installation-guide/ · https://docs.gatling.io/reference/script/core/injection
- JMeter, Open Model Thread Group (5.5, experimental): https://www.blazemeter.com/blog/open-model-thread-group
- Locust, modelo cerrado y `constant_pacing`: https://medium.com/locust-cloud/locusts-and-honey-badgers-closed-vs-open-workload-models-in-load-testing-9f59abfc6d9f
- Medición propia: `tests/performance/resultados/carga-20261111-0422-docker/recursos-k6.csv` y `tests/performance/resultados/comparativa-20261111-2236/`
