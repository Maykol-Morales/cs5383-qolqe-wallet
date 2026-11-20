# Informe del proyecto – Grupo 3 (G3 · Historial y categorías)

## 1. Datos generales y alcance
*(Parte 1; se actualiza en cada parte)*

| Campo | Valor |
|---|---|
| Integrantes | Sebastian, Maykol |
| Módulo | G3 · Historial (filtros, paginación, exportación CSV) y categorías, más el núcleo común |
| Herramienta de API | pytest + httpx + pytest-bdd (**provisional**: la celda de la herramienta asignada está vacía en el sorteo; si cambia, los `.feature` se reutilizan tal cual) + Schemathesis para contrato |
| Herramienta web | WebdriverIO 10 + Cucumber + Page Objects + Allure; CI/CD con GitHub Actions y GitHub Pages |
| Herramienta de rendimiento | k6 (§4.2) |

**Alcance y nivel de prueba.** Se cubren **todas** las HU del núcleo (HU-N-01 a N-09) y de G3 (HU-G3-01 a G3-08), con 141 escenarios Gherkin (ver trazabilidad). Criterios para elegir el nivel:

- **API** cuando el criterio es una regla de negocio, un valor límite o un código de error: es rápido, determinista y se repite con datos independientes (`/api/pruebas/reiniciar` antes de cada escenario). Aquí se ejecutan el 100 % de los escenarios escritos, salvo uno.
- **E2E web (Parte 2)** para lo que solo existe en la interfaz: formularios, mensajes, navegación de la paginación, descarga del CSV desde el botón y el comprobante en pantalla.
- **Rendimiento (Parte 3)** para el historial con ~1,000 movimientos por usuario y la concurrencia de HU-N-07 CA5 (`@concurrencia`, omitido aquí a propósito: con un cliente en el mismo proceso no es una prueba de concurrencia real).

| HU | Prioridad | Nivel elegido | Justificación |
|---|---|---|---|
| HU-N-01 Registro | Alta | API (+ E2E el flujo del formulario) | Reglas RN-01 a RN-03 con valores límite; el SMS de bienvenida se consulta en `/api/pruebas/notificaciones` |
| HU-N-02 Login · HU-N-03 Logout | Alta | API | Bloqueo a los 3 intentos y a los 15 min (14/15 min), token 30 min, dispositivo nuevo. Seguridad: máximo riesgo |
| HU-N-04/05/06 Saldo, perfil, cierre | Alta/Media | API | Orden de validaciones del cierre (PIN → saldo → solicitudes) y efectos sobre sesiones y transferencias |
| HU-N-07/08/09 Transferencias y comisión | Alta | API | Dinero: S/ 500.00 por operación, límite diario, saldo, comisión 1.5 % con mínimo y máximo, simulador sin efectos |
| HU-G3-01 Consultar movimientos | Alta | API (+ E2E filtros y paginación en pantalla) | Rango de 90 días, tipo, categoría, páginas de 10 (9/10/11/20/21), orden y saldo posterior |
| HU-G3-02 Detalle | Alta | API | Propiedad de los datos (404 si es ajeno) |
| HU-G3-03 a 06 Categorías | Media/Baja | API | Límite de 10, nombre 3–20, paleta de 8 colores, duplicados sin distinguir mayúsculas, eliminación sin borrar movimientos |
| HU-G3-07 Clasificar | Media | API | Nota 100/101, categoría y movimiento ajenos (404), RN-11 (no cambia monto, fecha ni tipo) |
| HU-G3-08 Exportar CSV | Media | API (+ E2E la descarga) | Formato exacto del CSV, no pagina, mismas reglas de rango |

**Interpretaciones asumidas** (a confirmar con el docente): "máximo 90 días" se toma como `hasta − desde ≤ 90` días (hace 90 días → hoy es válido, hace 91 es `FILTRO_INVALIDO`); las rutas `GET /api/movimientos/recientes` y G1/G2/G4/G5/G6 quedan fuera del alcance.

## 2. Pruebas de API
*(Parte 1)*

**Herramienta: pytest + httpx + pytest-bdd.**

- **Enfoque:** los escenarios Gherkin (`features/*.feature`) son la fuente; pytest-bdd los enlaza con funciones de pasos Python (`tests/api/`). Cada `Scenario Outline` → un caso por fila de `Examples`; las etiquetas (`@HU-G3-01`, `@api`, `@DEF-07`) se vuelven marcadores de pytest y dan la trazabilidad HU → caso → resultado.
- **Ventajas:** un solo lenguaje que ya usa el repo; fixtures de pytest para aislar datos; el mismo código corre en el proceso (TestClient, sin levantar nada) o contra un servidor real con `QOLQE_URL`; `--cov` funciona directamente.
- **Limitaciones:** no trae reportes propios (hay que sumar `pytest-html`/Allure); los pasos con `parse` pueden resultar ambiguos si dos frases se parecen (nos pasó con "cambio la categoría… a nombre… y color…"); el pegamento Python crece con el número de frases.
- **Capacidades de IA:** la herramienta no incluye IA propia. Se usó un asistente (Claude Code) para proponer escenarios y pasos; ver `IA.md`.

**Contrato:** `tests/api/test_contrato.py` ejecuta Schemathesis contra `/openapi.json` de un uvicorn real en un subproceso (15 ejemplos por operación, `CONTRATO_EJEMPLOS` para cambiarlo). Se excluyen logout, sesiones, reloj, reinicio y cierre de cuenta (invalidan la sesión compartida). Se validan los checks de conformidad (sin 5xx, códigos de estado, content-type, cabeceras y esquema de respuesta) y **no** `positive/negative_data_acceptance` ni `Allow` en 405, que daban ruido: p. ej. aceptar `correo: ""` en el registro o rechazar `monto=0`, que son decisiones de negocio documentadas. **Resultado: 60 operaciones conformes** con ejemplos fijos (`derandomize`). Observación sin confirmar: en la primera corrida del CI de GitHub (semilla aleatoria, Python 3.12) Schemathesis obtuvo un `500` en `POST /api/usuarios` con `{"celular":"914710469","dni":"14710469","nombres":"00","pin":"0849","correo":"1@1.com"}`; ese cuerpo da `201` en una BD limpia y no se reprodujo en 6 corridas locales (3.12 y 3.14, hasta 100 ejemplos), así que depende del estado acumulado por la corrida de fuzzing. **No se registra como defecto** (no es reproducible); queda pendiente investigarlo con la traza del servidor.

**Corrida manual del CLI con todos los checks** (Schemathesis 4.31.1, `schemathesis run /openapi.json --max-examples 30 --checks all`, mismas exclusiones): 60 operaciones, 2 782 casos, 44 hallazgos, clasificados así: **(a) "rechazó una solicitud válida según el contrato" (23)**: el contrato es más laxo que las reglas de negocio (`monto=0` en recargas/solicitudes/comisión, categoría ajena como filtro, celular/color/tipo permitidos por el esquema pero no por la regla); es **imprecisión del contrato** (faltan `minimum`/`enum`), no defecto del código, porque las reglas están en `requisitos.md`. **(b) "aceptó una solicitud inválida según el contrato" (3)**: `pin` y `celular` más largos que `maxLength` en login/desbloqueo (responden 401/404 en vez de 422) y `cci` de tipo incorrecto en transferencias; **observaciones de bajo impacto** (el servidor igual no actúa), pendientes de decidir si se endurece el esquema. **(c) `Allow` inválido en 405 (17)**: ruido de FastAPI, no se considera defecto. **(d) "recurso no disponible tras crearlo" (1)**: por revisar. Ningún 5xx. Reporte JUnit generado localmente (no versionado).

**Cómo ejecutar** (desde la raíz del repo):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -rx                              # todo (≈1 min); los defectos conocidos salen como "xfailed"
pytest tests/api -m "HU-G3-01"         # una historia
MOSTRAR_DEFECTOS=1 pytest tests/api    # los defectos fallan a la vista
pytest tests/api --cov=qolqe           # cobertura
QOLQE_URL=http://localhost:8000 pytest tests/api/test_nucleo.py   # contra un servidor real
```

**Resultados** (Qolqe Wallet 1.0.0, 2026-10-17): `252 passed, 1 skipped, 24 xfailed` y 60 subpruebas de contrato. Los 24 xfailed son 24 casos que detectan los 12 defectos de la sección 5; el skipped es el escenario de concurrencia. Con `MOSTRAR_DEFECTOS=1` esos 24 fallan por el motivo descrito en `docs/defectos.md`. Cobertura de líneas de la app con estas pruebas: `api/movimientos.py` 100 %, `api/categorias.py` 100 %, `api/cuentas.py` 100 %, `api/autenticacion.py` 100 %, `reglas/nucleo.py` 100 %, `reglas/historial.py` 98 %, `api/transferencias.py` 88 %.

**Trazabilidad HU → escenarios** (cada escenario lleva su `@HU-…`; `Outline` cuenta una vez):

| HU | Archivo `.feature` | Escenarios | HU | Archivo `.feature` | Escenarios |
|---|---|---|---|---|---|
| HU-N-01 | nucleo_registro | 10 | HU-G3-01 | historial | 22 |
| HU-N-02 | nucleo_sesion | 11 | HU-G3-02 | historial | 4 |
| HU-N-03 | nucleo_sesion | 3 | HU-G3-03 | categorias | 10 |
| HU-N-04 | nucleo_cuenta | 3 | HU-G3-04 | categorias | 3 |
| HU-N-05 | nucleo_cuenta | 4 | HU-G3-05 | categorias | 8 |
| HU-N-06 | nucleo_cuenta | 7 | HU-G3-06 | categorias | 5 |
| HU-N-07 | nucleo_transferencias | 17 | HU-G3-07 | historial | 10 |
| HU-N-08 | nucleo_transferencias | 12 | HU-G3-08 | historial | 8 |
| HU-N-09 | nucleo_transferencias | 4 |  |  |  |

## 3. Pruebas web y CI/CD
*(Parte 2)*

**Herramienta web: WebdriverIO 10 + Cucumber + Page Objects + Allure** (`tests/e2e/`, README propio). Cinco casos E2E, solo para lo que existe en la interfaz (el resto se prueba por API):

| Caso | HU | Qué verifica |
|---|---|---|
| CP-W01 | HU-G3-03, HU-G3-07 | Crear categoría y clasificar el último movimiento con nota |
| CP-W02, CP-W03 | HU-G3-01 | Filtrar por tipo (Recargas, Pagos de servicios): todas las filas son de ese tipo |
| CP-W04 | HU-G3-01 | Paginar de 10 en 10 con Siguiente y Anterior ("Página 1 de 2") |
| CP-W05 | HU-G3-08 | Exportar CSV desde el botón: encabezado exacto, filas del filtro y mismos códigos que la tabla |
| CP-W90 | HU-G3-03, HU-G3-07 | El mismo flujo de CP-W01 con `browser.act()` (IA), repetido desde la caché |

Sin esperas fijas (solo `waitUntil`/`expect` con auto-espera); pasan 3 veces seguidas en local y en cada run del pipeline. DEF-14 (`@DEF-14`) corre aparte y debe fallar.

**CI/CD: GitHub Actions** (`.github/workflows/pruebas.yml`): `api` (pytest + Schemathesis, `@DEF` = xfail strict) → `web` (Qolqe en :8000, `npm test` ×3, `@ia` desde caché sin clave, DEF-14 invertido) → `reportes` (matriz + portada) → `publicar` (GitHub Pages: https://maykol-morales.github.io/cs5383-qolqe-wallet/). Quality gate: todo pasa salvo los defectos de `docs/defectos.md`. Trazabilidad: `docs/trazabilidad.md`, generada desde los JUnit de cada run.

**Comparativa de IA** (`docs/comparativa-ia.md`): para la misma tarea, Page Objects 3,6 s y 0 tokens; `browser.act` graba una vez (~137k tokens, US$ 0,29, 34 s) y repite gratis en 6,8 s; un agente Claude (`claude -p`) cuesta en cada corrida (US$ 0,36 con Sonnet 5, US$ 0,04 con Sonnet 5.5) y tarda 17–165 s. Conclusión: Page Objects para la regresión; `act` con caché versionada si se quiere escribir pasos como intención; el agente, para explorar y generar pasos, no como suite.

## 4. Pruebas de rendimiento
*(Parte 3)* · Entregable: [`tests/performance/Informe_Rendimiento_G3.docx`](../tests/performance/Informe_Rendimiento_G3.docx) (plantilla del enunciado completa). Esta sección lo resume con las mismas cifras. Scripts y cómo correrlos en `tests/performance/` (README); plan y trazabilidad de cada valor en [`plan-rendimiento.md`](plan-rendimiento.md); reportes, CSV y gráficos de cada corrida en `tests/performance/resultados/<prueba>-<fecha>-docker/`.

**Grupo:** G3 (Sebastian, Maykol) · **Fecha:** 2026-11-12 · **Aplicación:** Qolqe Wallet (FastAPI + SQLite) · **Herramienta:** k6 2.4.0

### 4.1 Alcance y justificación

**Contexto de negocio.** Antes de la campaña «Quincena Qolqe» (días 15 y último de cada mes, de 12:00 a 12:15, con el triple de usuarios simultáneos que en hora punta) hay que saber si Qolqe cumple en la hora punta (3 000 sesiones por hora) y en el pico de la campaña (300 usuarios simultáneos), y hasta cuántos usuarios simultáneos puede crecer antes de dejar de cumplir.

**Flujos críticos.** Cada sesión es el login más uno de 4 flujos de 6 operaciones:

| Flujo | Peso | Operaciones | Criterio |
|---|---|---|---|
| Inicio de sesión | toda sesión | login | **Frecuencia** (3 000 por hora) y **riesgo**: PBKDF2 de 200 000 iteraciones consume CPU |
| 1. Chequear mi plata | 20 % | saldo y perfil, movimientos, límites o alertas, saldo, movimientos | **Frecuencia** (la consulta es el 30 % del tráfico) y **riesgo**: el saldo posterior de cada movimiento se calcula con una subconsulta por fila |
| 2. Pago a los míos | 40 % | saldo, contactos, transferencia, saldo, segunda transferencia, movimientos | **Impacto en el dinero**: cada transferencia debita y acredita dos cuentas |
| 3. Recargo celulares | 25 % | saldo, contactos, recarga propia, recarga a un familiar, saldo, límites o alertas | **Dinero y riesgo**: el antifraude simulado ocupa un hilo 40–120 ms |
| 4. Pago mis servicios | 15 % | saldo, consultar deuda, pagar, otra deuda, pagar, movimientos | **Dinero**: siempre se paga la deuda consultada antes |

Sumados, los pesos reproducen la tabla de operaciones del requerimiento con una desviación máxima de 1,7 puntos (§4.4).

**Capa objetivo: API.** El requerimiento se expresa en operaciones y tiempos del servicio, y la web es HTML estático que llama a la misma API: el navegador no agrega trabajo al servidor y solo encarecería al generador.

### 4.2 Herramienta seleccionada

**k6** (Grafana; scripts en JavaScript, motor en Go). Cada parte del requerimiento cabe en el script sin plugins:

- **Umbrales nativos** por percentil y etiqueta (`http_req_duration{tipo:consulta}` p(95) < 800, `{tipo:dinero}` p(95) < 1500); la corrida sale con código ≠ 0 si se incumplen (quality gate).
- **Dos modelos de carga:** `ramping-arrival-rate` (abierto) para «sesiones por hora», donde `dropped_iterations` mide «sin acumular retrasos», y `ramping-vus` para «usuarios simultáneos» del pico y del estrés.
- **Generador liviano:** 0,5 % de CPU en la carga, lejos del 80 % que invalida la corrida.
- Los 4xx esperados se contabilizan aparte (`errores_negocio`) y el dashboard HTML se exporta con la corrida.

| Herramienta | Ventajas | Limitaciones |
|---|---|---|
| JMeter | Interfaz gráfica, muchos plugins, la más conocida | Sin criterio por percentil sin Taurus; modelo abierto experimental; un hilo de JVM por usuario; la lógica queda en Groovy dentro de un `.jmx` |
| Locust | Python (el lenguaje del SUT), interfaz web en vivo | Modelo cerrado por defecto, sin umbrales nativos, un núcleo por proceso |
| Gatling | Muy eficiente, modelo abierto y assertions por percentil, gran reporte | El umbral por tipo pide agrupar peticiones; Node más una JVM. La alternativa más cercana |
| Artillery | YAML simple, modelo abierto (`arrivalRate`) | Generador Node de un hilo; p95 por tipo con plugin |
| Taurus | Capa YAML con `passfail` | No genera carga; k6 ya trae los umbrales |

Limitaciones de k6: su runtime JavaScript no es Node (sin npm), no mide los recursos del servidor (lo hace `monitor.py`) y el script es código. Comparativa medida de CPU del generador (k6 vs Locust) en [`comparativa-rendimiento.md`](comparativa-rendimiento.md).

### 4.3 Tipos de prueba seleccionados

| Tipo | ¿Aplica? | Justificación |
|---|---|---|
| Carga | Sí | «Sostener el volumen de la hora punta sin acumular retrasos»: 3 000 sesiones/h con los umbrales y < 1 % de fallas |
| Estrés | Sí | «Hasta cuántos usuarios simultáneos podemos crecer»: escalones de +100 desde el pico hasta el quiebre |
| Pico | Sí | El triple de usuarios, la mayoría entrando en los primeros 5 min; degradación razonable, ninguna operación de dinero a medias ni duplicada |
| Resistencia | No | El requerimiento no la pide («6:00 a 24:00 sin reinicios» no tiene umbral); la real serían 18 h, y 1 h no permite concluir sobre 18; lo que vigila ya se registra por minuto en las otras pruebas. Riesgo no cubierto en §4.8 |

Además, una prueba de humo (1 VU, 3 sesiones) valida el script y mide la latencia sin contención.

### 4.4 Modelo de carga

| Parámetro | Carga (hora punta) | Pico (campaña) | Estrés |
|---|---|---|---|
| VUs | 50 sesiones/min (abierto) ≈ 100 VUs; máx. 120 | 300 | 300 → 1 000, +100 por escalón |
| Ramp-up | 120 s | 300 s (lineal) | 300 s al primer escalón; 60 s cada siguiente |
| Duración | 900 s estables (1 020 con rampa) | 900 s con rampa (12:00–12:15) | 180 s por escalón; 8 escalones, 2 160 s |
| Think time | Triangular 10–25 s (media 18 s) | Igual | Igual |
| Distribución | 4 flujos 20/40/25/15 → saldo y perfil 30,8 · movimientos 15,8 · transferencia 13,3 · contactos 10,8 · recarga 8,3 · deuda 5,0/5,0 · otras 10,8 | Igual | Igual |

- **Little:** 3 000 sesiones/h × 2 min / 60 = 100 usuarios simultáneos; 50 llegadas por minuto. Campaña = 300.
- **Sesión:** login + 6 operaciones con 6 pausas de 18 s ≈ 2 min. La triangular(10, 19, 25) tiene media 18 s exacta dentro del rango 10–25 s.
- **Pesos:** con flujos enteros de 6 operaciones no puede ser exacto; la mayor desviación es 1,7 puntos (transferencia 13,3 % vs 15 %, recarga 8,3 % vs 10 %).
- **Throughput esperado:** 18 000 operaciones/h = 5 operaciones/s ≈ 7,9 peticiones/s (9,5 peticiones por sesión).
- **Datos:** 1 000 usuarios (los 200 de la semilla + 800 copias, ~1 000 movimientos c/u), S/ 10 000, 5 contactos y un suministro con 30 deudas; un usuario por VU y una referencia propia por operación de dinero para cruzarla con la BD.

### 4.5 Criterios de aceptación

| Criterio | Umbral | Fuente |
|---|---|---|
| p95 consultas e inicio de sesión | < 800 ms | «el 95 % debe responder en menos de 800 ms» |
| p95 operaciones de dinero | < 1 500 ms | «el 95 % en menos de 1,5 segundos» |
| Fallas técnicas | < 1 % (5xx, timeout, red); 0 errores de negocio | «no más del 1 % de las operaciones puede fallar» |
| Throughput | ≥ 50 sesiones/min, ≥ 5 operaciones/s | 3 000 sesiones/h × 6 operaciones |
| Sin acumular retrasos | 0 `dropped_iterations`, sesión p95 < 130 s | «sin acumular retrasos» |
| Integridad del dinero | 0 operaciones a medias o duplicadas (cruce con la BD) | «ninguna operación … a medias ni aplicarse dos veces» |

**Supuestos:** «degradación razonable» en el pico = p95 ≤ 2× el umbral y fallas < 5 %, integridad siempre en 0; «operación» = operación de negocio para el throughput y petición HTTP para el tiempo; la capacidad es el último escalón del estrés que cumple los umbrales de hora punta; el historial se consulta sin fechas (30 días) y la sesión termina sin logout. **Integridad:** por usuario, saldo final − inicial = suma de sus movimientos nuevos; 2 movimientos por transferencia y 1 por recarga o pago; cada deuda pagada una vez; cada referencia 2xx de k6 existe una vez en la BD.

### 4.6 Restricciones del entorno

- **Entorno:** Docker. Qolqe en `python:3.12-slim` con `--cpus=1 --memory=1g`, un proceso uvicorn y SQLite en un volumen, en :8001. k6 en el mismo equipo, fuera del contenedor (`correr.py`).
- **Máquina:** AMD Ryzen 7 7800X3D (8 núcleos/16 hilos), 31 GB, Windows 11 Pro, Docker Desktop 29.9.3 (VM de 16 CPU y 15 GB).
- **Medición:** `monitor.py` cada segundo: Qolqe con `docker stats` (% de un núcleo, máx. 100 %) y k6 con psutil → `recursos-qolqe.csv`, `recursos-k6.csv`; `horario.txt` marca inicio y fin y `graficos.py` cruza todo con k6.
- **Limitaciones:** línea base relativa (1 núcleo por cgroups, SQLite local), generador y SUT en el mismo equipo (k6: 0,5 % CPU en carga, 1,4 % en pico, 1,9 % en estrés), latencia de localhost, una corrida por prueba, la memoria de `docker stats` incluye caché, Qolqe en modo prueba, sin resistencia.
- **Plan vs ejecución:** resistencia descartada (§4.3); el primer escalón del estrés sube en 5 min, como el pico, para medir capacidad y no una avalancha de logins.

### 4.7 Resultados

#### Carga (hora punta, 15 min) · `resultados/carga-20261112-1949-docker/`

| Criterio | Umbral | Medido | ¿Cumple? |
|---|---|---|---|
| p95 consultas e inicio de sesión | < 800 ms | 25 ms | Sí |
| p95 dinero | < 1 500 ms | 114 ms | Sí |
| Fallas técnicas | < 1 % | 0,00 % (0 de 7 328) | Sí |
| Errores de negocio | 0 | 0 | Sí |
| Throughput (meseta) | ≈ 7,9 peticiones/s | media 7,8 (7,6–8,0); 4 621 operaciones | Sí |
| Sin acumular retrasos | 0 descartadas; sesión p95 < 130 s | 0; p95 120 s (media 108) | Sí |
| Integridad | 0 a medias o duplicadas | 1 213 confirmadas / 1 214 filas → OK | Sí |

Más lentos: transferencias p95 120 ms, login 28 ms, movimientos 18 ms, pagos 4 ms. Qolqe: CPU prom. 4,0 % (máx. 58,4 %), memoria 55–102 MB; k6: 0,5 % (máx. 25 %).

#### Pico (campaña, 300 VUs) · `resultados/pico-20261112-2008-docker/`

| Criterio | Umbral | Medido | ¿Cumple? |
|---|---|---|---|
| p95 consultas | < 800 ms (pico < 1 600) | 25 ms | Sí |
| p95 dinero | < 1 500 ms (pico < 3 000) | 115 ms | Sí |
| Fallas técnicas | < 1 % (pico < 5 %) | 0,00 % (0 de 20 411) | Sí |
| Throughput (meseta) | ~3× hora punta | media 26,3 peticiones/s; 12 767 operaciones | — |
| Sesiones completas | — | 2 008; p95 120 s | — |
| Integridad | 0 | 3 407 / 3 407 → OK | Sí |

Qolqe: CPU prom. 12,0 % (máx. 44,6 %), memoria 71–115 MB; k6: 1,4 % (máx. 28,1 %).

#### Estrés (300 → 1 000 VUs) · `resultados/estres-20261112-2024-docker/`

| Escalón | p95 consultas (peor min) | p95 dinero (peor min) | Fallas (peor min) | ¿Cumple? |
|---|---|---|---|---|
| 300–700 VUs | 26–27 ms | 114–118 ms | 0,0 % | Sí |
| 800 VUs | ≥ 60 s (timeout) | ≥ 60 s | 100 % | **No** |
| 900 VUs | ≥ 60 s | ≥ 60 s | 100 % | **No** |

Fallas en total: 6 080 de 60 674 (10,0 %; k6 cortó con `abortOnFail` a los 32 min y 924 VUs). Integridad OK, con **3 operaciones aplicadas aunque k6 recibió error o timeout**. 1 971 «database is locked» en el log. Qolqe: 34 % CPU a 700 VUs, 12 % durante el colapso, memoria 142–150 → 297–538 MB; k6: 1,9 % (máx. 46,8 %).

Gráficos: `k6.png` y `recursos.png` en cada carpeta.

#### Validación en EC2 · `resultados/{humo,carga,pico,estres}-20261120-*-docker-ec2/`

Mismo `correr.py` y mismos 4 flujos en una AWS EC2 `c7i.large` (2 vCPU, Ubuntu 22.04): Qolqe en Docker con `--cpus=1 --memory=1g` fijado al núcleo 1 (`CPUSET=1`) y k6 con `taskset -c 0` en el núcleo 0, sin red de por medio.

| Prueba | p95 consultas | p95 dinero | Fallas | Throughput (meseta) | Integridad | CPU Qolqe prom. |
|---|---|---|---|---|---|---|
| Carga | 36 ms | 115 ms | 0 de 7 374 | 7,9 peticiones/s | 1 225 / 1 225 OK | 5 % |
| Pico | 39 ms | 116 ms | 0 de 20 431 | 26,2 peticiones/s | 3 387 / 3 387 OK | 16 % |
| Estrés 300 → 1 000 | ≤ 118 ms por minuto | ≤ 127 ms por minuto | 0 de 112 387 | 26 → 88 peticiones/s | 18 789 / 18 789 OK | 36 % (43 % a 700, 61 % a 1 000) |

Carga y pico repiten las cifras de Docker en Windows. **El estrés no quiebra**: llega al tope de 1 000 usuarios preparados sin una falla, con el p95 de consultas subiendo de forma gradual (40 → 118 ms) y el throughput creciendo con los usuarios; 0 «database is locked» en el log. k6: 3,4 % de CPU en promedio (máx. 59 %).

### 4.8 Análisis, conclusiones y recomendaciones

**¿Se cumplieron los umbrales?** Hora punta y pico, sí, con amplio margen (el pico cumple incluso los umbrales estrictos). En el estrés se cumplen hasta **700 usuarios**; al pasar a 800, en un solo minuto (20:49) el p95 salta de 27 ms a 39 s y las fallas a 24,9 % y luego a 98–100 %; el throughput cae de 62 a 12–16 peticiones/s.

**Cuello de botella: el candado de escritura de SQLite, no el CPU** ([DEF-16](defectos.md)).
- Patrón de acantilado: p95 plano (~26 ms) hasta 700 y colapso total a 800, también en consultas de saldo.
- El CPU estaba libre: 34 % a 700 VUs y 12 % durante el colapso → hilos esperando, no trabajando.
- 1 971 «database is locked», todos en escrituras y ninguno antes de las 20:49:15: login (`autenticacion.py:136`, 1 574 trazas) y `mover_saldo` (`operaciones.py:23`, 334).
- Fallas: 5 746 timeouts o conexiones cortadas y 334 respuestas 500 (177 en login); 0 de negocio.
- Mecanismo (hipótesis consistente): SQLite admite un escritor; el commit se hace al cerrar la dependencia, después de responder, y necesita un hilo del pool de 40. Con muchas peticiones esperando el candado (`busy_timeout` 10 s) el pool se llena y quien tiene el candado no consigue hilo para el commit (misma raíz que DEF-15).
- La predicción por CPU (≈ 5,6 ms por petición → ~2 000 usuarios) sobrestima: el recurso que se agota es el candado junto con el pool.
- Recuperación: con k6 ya cerrado, Qolqe siguió ~5 min vaciando la cola (1 100 «locked» más) con ~605 MB.
- Límite: sin flamegraph en esta corrida (`correr.py` no graba py-spy); solo el CPU total del contenedor.

**Capacidad:** **700 usuarios simultáneos ≈ 21 000 sesiones/h ≈ 7× la hora punta y 2,3× el pico**, con entrada gradual (+100 cada 4 min) y precisión de ±100. Línea base relativa (1 CPU, 1 GB, una corrida). En la EC2, con el mismo límite de 1 CPU, la capacidad es **≥ 1 000 usuarios (≈ 30 000 sesiones/h, ≥ 10× la hora punta)** y el quiebre no llegó a verse: DEF-16 depende de cuántas escrituras coinciden, y con login y disco más rápidos coinciden menos. El defecto no desaparece; se vuelve menos probable.

**Riesgos:** el margen se midió con entrada gradual, y una notificación que haga entrar a todos a la vez es justo la avalancha que dispara la contención; el colapso afecta a todos y dura más que la carga; 3 operaciones se aplicaron con error para el cliente, así que un reintento puede cobrar dos veces (sin idempotencia); la acumulación de 18 h no se midió.

**Recomendaciones (para el equipo de Qolqe):**
1. Commit dentro del endpoint y transacciones cortas (escribir al final, tras el antifraude).
2. 503 con `Retry-After` en vez de 500, reintento con espera aleatoria y clave de idempotencia en transferencias, recargas y pagos.
3. Escalonar la entrada en la campaña (notificaciones por tandas, sala de espera para el login).
4. Alertar sobre ~600 usuarios simultáneos (85 % de la capacidad) o p95 de consultas > 200 ms.
5. Medir de nuevo tras el cambio; el siguiente límite será el CPU del login (PBKDF2).
6. Si el negocio exige las 18 h, resistencia en un entorno dedicado con memoria y tamaño de la BD como criterios.

**Corridas anteriores (historial, no forman parte del informe):** las carpetas `resultados/*-20261110*`, `*-20261111*` y `*-20261112-0*-ec2` se hicieron con el modelo de carga anterior (pesos por operación, sin flujos) y con `correr.sh`, por eso sus cifras no se comparan con las de arriba.

## 5. Defectos encontrados
*(Todas las partes)* · Detalle, pasos y evidencia en [`defectos.md`](defectos.md).

| ID | Título | Severidad | Estado |
|---|---|---|---|
| DEF-01 | La comisión interbancaria no usa redondeo comercial (0.005 no sube) | Media | Abierto |
| DEF-02 | El PIN con secuencia descendente (4321, 9876, 3210) se acepta al registrarse | Media | Abierto |
| DEF-03 | Un inicio de sesión exitoso no reinicia el conteo de intentos fallidos | Alta | Abierto |
| DEF-04 | Una transferencia interbancaria puede dejar el saldo negativo | Crítica | Abierto |
| DEF-05 | Cerrar sesión responde 204 pero el token sigue siendo válido | Crítica | Abierto |
| DEF-06 | Se puede transferir a una cuenta cerrada y el dinero se pierde | Crítica | Abierto |
| DEF-07 | El historial excluye el día completo de `hasta`, incluidos los movimientos de hoy | Alta | Abierto |
| DEF-08 | El detalle de un movimiento de otro usuario es visible (200 en lugar de 404) | Alta | Abierto |
| DEF-09 | El destinatario de una transferencia ve el movimiento del emisor en el detalle | Media | Abierto |
| DEF-10 | Editar una categoría permite repetir el nombre de otra categoría | Baja | Abierto |
| DEF-11 | El token deja de ser válido a los 30 minutos exactos | — | Descartado (el requisito no precisa el minuto 30; se acepta el comportamiento) |
| DEF-12 | Dos operaciones del mismo usuario en el mismo segundo comparten el código de operación | Alta | Abierto |
| DEF-13 | El límite diario no cuenta las transferencias interbancarias | Alta | Abierto |
| DEF-14 | De noche en Lima, con el celular en otra zona horaria, el historial sale vacío (UI, Parte 2) | Media | Abierto |
| DEF-16 | Con más de 40 inicios de sesión a la vez, Qolqe responde 500 «database is locked» (rendimiento, Parte 3) | Alta | Abierto |

## 6. Conclusiones y recomendaciones
*(Entrega final)*
