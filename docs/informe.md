# Informe del proyecto – Grupo 3 (G3 · Historial y categorías)

## 1. Datos generales y alcance
*(Parte 1; se actualiza en cada parte)*

| Campo | Valor |
|---|---|
| Integrantes | Sebastian, Maykol |
| Módulo | G3 · Historial (filtros, paginación, exportación CSV) y categorías, más el núcleo común |
| Herramienta de API | pytest + httpx + pytest-bdd (**provisional**: la celda de la herramienta asignada está vacía en el sorteo; si cambia, los `.feature` se reutilizan tal cual) + Schemathesis para contrato |
| Herramienta web | WebdriverIO 10 + Cucumber + Page Objects + Allure; CI/CD con GitHub Actions y GitHub Pages |
| Herramienta de rendimiento | *(Parte 3)* |

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

**Contrato:** el CLI de Schemathesis (`python demo.py schemathesis`) se ejecuta contra `/openapi.json` de un uvicorn real en un subproceso (30 ejemplos por operación, `--seed 1`). Es la única ejecución del contrato: en el CI es el primer job (`contrato`) y su código de salida es el gate, antes de los escenarios BDD y la web; deja VCR + HAR (cada caso con su petición y respuesta, base del dashboard de contrato) y JUnit para la trazabilidad. Hasta la Parte 2 corría además dentro de pytest (`tests/api/test_contrato.py`, 15 ejemplos con `derandomize`); se retiró para no ejecutar dos veces lo mismo con configuraciones distintas. Se excluyen logout, sesiones, reloj, reinicio y cierre de cuenta (invalidan la sesión compartida). Se validan los checks de conformidad (sin 5xx, códigos de estado, content-type, cabeceras y esquema de respuesta) y **no** `positive/negative_data_acceptance` ni `Allow` en 405, que daban ruido: p. ej. aceptar `correo: ""` en el registro o rechazar `monto=0`, que son decisiones de negocio documentadas. **Resultado: 60 operaciones conformes** con ejemplos fijos (`derandomize`). Observación sin confirmar: en la primera corrida del CI de GitHub (semilla aleatoria, Python 3.12) Schemathesis obtuvo un `500` en `POST /api/usuarios` con `{"celular":"914710469","dni":"14710469","nombres":"00","pin":"0849","correo":"1@1.com"}`; ese cuerpo da `201` en una BD limpia y no se reprodujo en 6 corridas locales (3.12 y 3.14, hasta 100 ejemplos), así que depende del estado acumulado por la corrida de fuzzing. **No se registra como defecto** (no es reproducible); queda pendiente investigarlo con la traza del servidor.

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

**Herramienta web: WebdriverIO 10 + Cucumber + Page Objects + Allure** (`tests/e2e/`, README propio). Casos E2E solo para lo que existe en la interfaz (el resto se prueba por API); `docs/trazabilidad.md` tiene el resultado de cada run:

| Caso | HU | Qué verifica |
|---|---|---|
| CP-W01 | HU-G3-03, HU-G3-07 | Crear categoría y clasificar el último movimiento con nota |
| CP-W02, CP-W03 | HU-G3-01 | Filtrar por tipo (Recargas, Pagos de servicios): todas las filas son de ese tipo |
| CP-W04 | HU-G3-01 | Paginar de 10 en 10 con Siguiente y Anterior ("Página 1 de 2") |
| CP-W05 | HU-G3-08 | Exportar CSV desde el botón: encabezado exacto, filas del filtro y mismos códigos que la tabla |
| CP-W06 | HU-N-01, HU-N-02 | Registrarse e ingresar con la cuenta nueva (saludo y saldo S/ 0.00) |
| CP-W07 | HU-N-01 | El registro rechaza un PIN secuencial y no sale de `/registro` |
| CP-W08 | HU-N-02 | PIN incorrecto: mensaje genérico y PIN vacío |
| CP-W09 | HU-N-03 | Cerrar sesión: aviso y `/inicio` vuelve a `/login` |
| CP-W10 | HU-N-04 | Ver y ocultar el saldo en el inicio |
| CP-W11 | HU-N-04, HU-N-05 | Perfil con DNI enmascarado; cambiar los nombres |
| CP-W12 | HU-N-07, HU-N-09 | Transferir S/ 50.00 a Qolqe: confirmación sin comisión y comprobante con el saldo nuevo |
| CP-W13 | HU-N-07 | S/ 500.01 se rechaza antes de confirmar |
| CP-W14 | HU-N-08, HU-N-09 | Interbancaria de S/ 100.00: comisión 1.5 % y CCI enmascarado en el comprobante |
| CP-W15 | HU-N-06 | Cerrar la cuenta con saldo se rechaza (`SALDO_PENDIENTE`) |
| CP-W16 | HU-N-01, HU-N-06 | Cuenta nueva con S/ 0.00: se cierra y ya no puede ingresar |
| CP-W90 | HU-G3-03, HU-G3-07 | El mismo flujo de CP-W01 con `browser.act()` (IA), repetido desde la caché |

Sin esperas fijas (solo `waitUntil`/`expect` con auto-espera); pasan 3 veces seguidas en local y en cada run del pipeline. DEF-14 (`@DEF-14`) corre aparte y debe fallar.

### 3.1 Patrón de diseño: por qué Page Object

**El problema.** Un paso Cucumber dice *qué* hace el usuario ("filtro mis movimientos por el tipo Recargas"). Para ejecutarlo hay que saber *cómo* está hecha la pantalla: los selectores (`[data-testid=select-tipo]`, `aria/Movimientos`), el orden de los clics y cuándo terminó de responder la UI. Si ese conocimiento vive en los pasos, se copia en cada paso que toca la misma pantalla, y un cambio de la UI obliga a buscar y corregir todas las copias. En Qolqe el riesgo es concreto: la UI se repinta por JavaScript (`qolqe/web/static/app.js`), muestra un esqueleto de carga mientras llega la respuesta y los avisos duran milisegundos. Una espera mal hecha en un solo lugar basta para tener pruebas intermitentes.

**Qué hace el patrón** (Fowler, [*PageObject*](https://martinfowler.com/bliki/PageObject.html); WebdriverIO, [*Page Object Pattern*](https://webdriver.io/docs/pageobjects); Selenium, [*Page object models*](https://www.selenium.dev/documentation/test_practices/encouraged/page_object_models/)). Cada pantalla es una clase que ofrece operaciones del dominio (`ingresarComo`, `filtrar`, `clasificar`) y esconde los selectores y la sincronización. El repo separa tres capas: `features/` (qué se prueba), `steps/` (traducción de Gherkin) y `pages/` (cómo se usa la pantalla). A eso se suma el fixture de `wdio.conf.js`: en `beforeScenario` devuelve el reloj a la hora real, llama a `POST /api/pruebas/reiniciar` y fija la zona horaria de Lima. Las aserciones del caso quedan en los pasos, como prefiere Fowler. Los Page Objects solo esperan lo necesario para saber que la acción terminó.

**Beneficios medidos en este repo.** Conteo con `grep` sobre `tests/e2e/pages` y `tests/e2e/steps` al 2026-11-10; las cifras pueden subir cuando se agreguen escenarios.

- **Cada selector vive en un solo lugar.** `[data-testid=fila-movimiento]` aparece 2 veces, las dos en `pages/historial.page.js` (`get filas()` y `fila(codigo)`). Los pasos lo usan 10 veces a través de `HistorialPage.filas` y `HistorialPage.fila(...)`: 2 en `clasificar.steps.js`, 7 en `historial.steps.js` y 1 en `ia.steps.js`. El propio Page Object lo usa 2 veces más (`abrir`, `abrirPrimerMovimiento`). Si Qolqe cambia ese atributo, **con Page Object se corrigen 2 líneas de 1 archivo; sin él, 12 líneas repartidas en 3 archivos**. Basta olvidar una para que falle un escenario que no tiene nada que ver con el cambio.
- **La sincronización se escribe una vez.** `cambiarA(testid)` hace clic y espera a que la tabla quite su esqueleto (`.esqueleto`). La usan `filtrar` (botón Buscar) y los pasos "paso a la página siguiente" y "vuelvo a la página anterior". `crearCategoria` recarga la página y comprueba que la categoría quedó guardada, porque en la CI de Windows la UI a veces no repintaba. `clasificar` espera la respuesta del `PUT` con `browser.mock`, porque el aviso desaparece antes de poder leerlo. Cada arreglo contra una intermitencia se hizo en un solo método y lo heredan todos los escenarios que pasan por ahí.
- **Los detalles de plataforma quedan ocultos.** `filtrar` escribe la fecha `desde` por JavaScript porque lo que se teclea en un `<input type=date>` depende del idioma del navegador. Ningún paso necesita saberlo.
- **Se reutiliza entre estilos de prueba.** El escenario `@ia` (`clasificar-ia.feature`) cambia las acciones por `browser.act()` pero reutiliza los pasos `Then` de `clasificar.steps.js` y `HistorialPage.filas`. La comparativa (`docs/comparativa-ia.md`) mide el mismo flujo con Page Objects: 3,6 s y 0 tokens.
- **Los pasos se leen como el escenario.** Los `Given` y `When` de `clasificar.steps.js` delegan en el Page Object en una o dos líneas. El `.feature` y su implementación se revisan juntos sin leer HTML.

**Alternativas consideradas**

| Alternativa | Qué propone | Por qué no se eligió aquí |
|---|---|---|
| Pasos con selectores directos | Cada paso Cucumber usa `$()` con su selector | Es justo lo que se quiere evitar: 12 lugares para un selector y la sincronización (esqueleto, `PUT`, recarga) copiada en cada paso. Sirve para un prototipo de un escenario, no para una suite que corre 3 veces por run |
| Screenplay ([Serenity/JS](https://serenity-js.org/handbook/design/screenplay-pattern/)) | Actores con habilidades que ejecutan tareas, interacciones y preguntas; escala mejor con muchos roles y pantallas | Con 6 pantallas (login, registro, inicio, perfil, transferir, historial) y un solo actor por escenario, suma capas (Actor, Ability, Task, Question) y otra dependencia sin un beneficio visible. El equipo ya conocía Page Object del laboratorio de la Clase 11. Si el alcance creciera a varios módulos y usuarios, sería la evolución natural |
| App Actions o atajos por API ([Bahmutov, Cypress](https://www.cypress.io/blog/stop-using-page-objects-and-start-using-app-actions)) | Preparar el estado llamando a la app o a la API en vez de recorrer la UI | Se usan donde corresponde: el fixture reinicia los datos y el reloj por la API de soporte, y el paso de DEF-14 fija la hora con `PUT /api/pruebas/reloj`. Pero la acción bajo prueba tiene que pasar por la UI. DEF-14 solo aparece cuando la UI arma el rango con la hora del navegador, y un atajo por API lo habría escondido. Además, App Actions en sentido estricto necesita exponer funciones del front (`window.app`), y `qolqe/` no se modifica |

**Límites y costos del patrón**

- Es código extra que hay que escribir y mantener. Con pocas pantallas el ahorro es moderado: aquí son 6 clases cortas (14–71 líneas).
- La herramienta no obliga a respetarlo. `historial.steps.js` todavía usa selectores directos en 4 líneas (`aria/Movimientos`, `historial-error`, `boton-exportar`, `td:nth-child(2)`). Además, `aria/Movimientos` está repetido en `HistorialPage.abrir()`, así que un cambio en ese enlace hoy se corrige en 2 lugares. Es deuda conocida: falta moverlos al Page Object.
- Un Page Object grande termina siendo una clase que sabe de todo. `historial.page.js` junta movimientos, detalle y categorías porque la UI los muestra en la misma página. Si crece, conviene dividirlo por componente (tabla, detalle, panel de categorías); Fowler aclara que un Page Object no tiene por qué cubrir una página entera.
- No protege contra cambios de flujo, como otro orden de pantallas o un campo nuevo en el formulario. Ahí cambia el método y a veces también el escenario.

**CI/CD: GitHub Actions** (`.github/workflows/pruebas.yml`): `contrato` (CLI de Schemathesis, una sola vez) → `api` (pytest-bdd, `@DEF` = xfail strict) en paralelo con `web` (Qolqe en :8000, `npm test` ×3, `@ia` desde caché sin clave, DEF-14 invertido) → `reportes` (matriz, sitio y quality gate) → `publicar` (GitHub Pages: https://maykol-morales.github.io/cs5383-qolqe-wallet/). Quality gate (`reportes.py gate`, al final de `reportes`; el sitio se publica igual con el estado real): G1 contrato 0 fallos (DEF-15 = defecto conocido) · G2 API sin fallas inesperadas ni XPASS (`@DEF-nn` = xfail estricto) · G3 cobertura ≥ 60 % (meta 75 %) · G4 web 3/3 corridas, `@ia` pasa y DEF-14 falla · G5 toda HU del alcance (Núcleo + G3) con caso ejecutado · G6 pruebas ≤ 10 min. Trazabilidad: `docs/trazabilidad.md`, generada desde los JUnit de cada run. Trazabilidad entre runs: columna «Últimos 10 runs» con marca *inestable* en `trazabilidad.html` (desde `historial.json`) y, como herramienta de gestión de casos, **Qase** (un test run por run de CI; elección y configuración en [`docs/gestion-casos.md`](gestion-casos.md)).

**Comparativa de IA** (`docs/comparativa-ia.md`): para la misma tarea, Page Objects 3,6 s y 0 tokens; `browser.act` graba una vez (~137k tokens, US$ 0,29, 34 s) y repite gratis en 6,8 s; un agente Claude (`claude -p`) cuesta en cada corrida (US$ 0,36 con Sonnet 5, US$ 0,04 con Sonnet 5.5) y tarda 17–165 s. Conclusión: Page Objects para la regresión; `act` con caché versionada si se quiere escribir pasos como intención; el agente, para explorar y generar pasos, no como suite.

### 3.2 Estrategia de herramientas: cómo se complementan

Cada herramienta cubre un riesgo que las otras dejan abierto. Ninguna reemplaza a otra: si se quitara una, quedaría sin cubrir una clase de defecto concreta.

| Herramienta | Nivel (pirámide) | Riesgo que cubre / qué detecta | Qué **no** detecta |
|---|---|---|---|
| **Schemathesis** (CLI, job `contrato`) | Servicio · contrato | Respuestas que no cumplen el OpenAPI (esquema, código de estado, content-type, cabeceras) y 5xx ante entradas generadas automáticamente: miles de casos por corrida (2 782 en la corrida de §2) sin escribirlos a mano | Reglas que el OpenAPI no expresa: tope de S/ 500, comisión, rango de 90 días, propiedad de los datos, efectos sobre el saldo o el historial. Tampoco la UI |
| **pytest-bdd + httpx** (job `api`) | Servicio · reglas de negocio | Reglas, valores límite y códigos de error de `requisitos.md`, con Gherkin como fuente de verdad. También los efectos persistidos (saldo, movimientos, notificaciones) y la seguridad de la sesión (bloqueo, token, logout) | La lógica que corre en el navegador (fechas locales, paginación en pantalla, descarga), el contrato de forma exhaustiva y la concurrencia real (Parte 3) |
| **WebdriverIO + Cucumber + Page Objects** (job `web`) | E2E · interfaz | Flujos de usuario en Chrome: integración UI ↔ API, la lógica del front y el entorno del navegador (zona horaria, idioma, descargas) | Combinaciones de reglas (es lento: se deja a la API) y el contrato |
| **Allure 3** (API y web) | Transversal · evidencia | No detecta defectos: deja evidencia por paso (petición y respuesta HTTP en la API, captura del paso fallido en la web) y, en la API, agrupa por módulo, HU y severidad (`@DEF` → issue) | — |
| **GitHub Actions + `reportes.py`** | Transversal · pipeline | Regresiones en cada push, XPASS (un defecto corregido sin retirar su marca), escenarios sin ejecución (`::warning::`), quality gate G1–G6 y matriz HU → caso → resultado en Pages | Nada por sí solo: depende de las pruebas que ejecuta |

La base de la pirámide (unitarias) no tiene pruebas propias porque el SUT se prueba como caja negra y `qolqe/` no se modifica. Su papel de retroalimentación rápida lo cumple la suite de API, que corre en el mismo proceso (TestClient) en un minuto aproximadamente y además mide cobertura de `qolqe/`.

**Evidencia de complementariedad en el propio repo**

- **Cada nivel encontró defectos que los otros no veían.** Los 12 defectos abiertos de la API (DEF-01 a DEF-10, DEF-12 y DEF-13; `docs/defectos.md`) los detectó pytest-bdd. Todos son reglas de negocio con peticiones válidas según el OpenAPI (redondeo, saldo, límite diario, propiedad, sesión), así que el contrato no podía verlos. **DEF-14 solo se ve en la web**: la API responde según el requisito, y es la UI la que arma el rango con la fecha del navegador. Apareció en la CI de GitHub, con el navegador en UTC. **DEF-15 lo encontró Schemathesis**: un 500 intermitente al repetir el registro (la respuesta sale antes del commit), que ninguna prueba escrita a mano provocaba porque exige dos peticiones idénticas en milisegundos; en la web se veía como un rebote del login. Además dejó 44 hallazgos de **imprecisión del contrato** (faltan `minimum`/`enum`; §2).
- **Una herramienta mide el solapamiento de otra.** El dashboard de contrato (`tests/dashboard/dashboard.py`) valida contra el OpenAPI la petición del paso `When` de cada escenario BDD, que saca de los adjuntos de Allure. Si esa petición ya viola el esquema y el `Then` solo mira el código de estado, marca el escenario como candidato a redundante con Schemathesis. Eran **44**. En lugar de borrarlos, se les agregó el paso «no se persiste ningún cambio si la operación fue rechazada» (16 escenarios en 4 `.feature`, commit `733b000`), que verifica algo que el contrato no puede ver: que la cuenta quedó igual. Quedaron **12** candidatos, que son lecturas sin estado y los de «requiere sesión».
- **El pipeline las ordena por costo.** `contrato` va primero y es el gate barato. `api` y `web` corren en paralelo después. `reportes` junta los JUnit de todas, arma la trazabilidad y aplica el quality gate. Un fallo se ve en el nivel más bajo que lo detecta.

**Por qué estas herramientas y no otras**

Criterios: lenguaje que ya usa el equipo, soporte de BDD (Gherkin como fuente de verdad desde la Parte 1), costo, integración con la CI y curva de aprendizaje.

| Elección | Alternativas | Criterio decisivo |
|---|---|---|
| **pytest + httpx + pytest-bdd** (API; provisional, ver §1) | Postman/Newman · RestAssured | El SUT está en Python. pytest-bdd lee los mismos `.feature` y el TestClient de FastAPI corre la app en el proceso, sin levantar un servidor, lo que también permite `--cov=qolqe`. Postman/Newman guarda colecciones JSON con las aserciones en JavaScript: sin Gherkin, difíciles de revisar en un diff y sin cobertura del servidor. RestAssured exige Java, Maven/Gradle y Cucumber-JVM: otro lenguaje y otro build para el mismo resultado. Las tres son gratuitas y corren en la CI |
| **Schemathesis** (contrato) | Escribir los casos negativos a mano en pytest-bdd o Postman | Genera los casos desde el `/openapi.json` que FastAPI ya publica, en Python y con semilla fija (`--seed 1`) para que sea repetible. Escribir esos miles de casos a mano no tiene sentido |
| **WebdriverIO 10 + Cucumber** (web) | Playwright · Cypress · Selenium WebDriver | Es la herramienta del laboratorio de la Clase 11, así que la curva ya estaba pagada. Tiene integración oficial con Cucumber (`@wdio/cucumber-framework`), Allure y JUnit. Usa WebDriver BiDi, con el que se espera el `PUT` (`browser.mock`) y se emulan el reloj y la zona horaria (necesarios para DEF-14), y trae `browser.act()` con caché versionada (§3, comparativa de IA). Playwright tiene capacidades parecidas, pero su runner no trae Cucumber: haría falta un adaptador de terceros. Cypress corre dentro del navegador y su soporte de Cucumber también viene de la comunidad. Selenium es el estándar de base (el mismo protocolo W3C), pero sin auto-espera ni runner BDD integrado, lo que obliga a escribir más código de infraestructura |
| **Allure 3** | pytest-html, reporte de consola de cada runner | Un mismo formato de reporte para API y web, agrupado por epic/story (en la API, epic = módulo y story = HU) y con historial entre corridas. La versión 3 corre con `npx`, sin Java |
| **GitHub Actions + GitHub Pages** | Jenkins, GitLab CI | El repo ya está en GitHub. No hay servidor que mantener y Pages publica gratis la matriz y los reportes de cada run |

## 4. Pruebas de rendimiento
*(Parte 3)*

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
| DEF-15 | Qolqe responde antes de guardar la operación: una petición inmediata no ve el cambio (500 al repetir el registro, 401 con un token recién emitido) | Alta | Abierto |

## 6. Conclusiones y recomendaciones
*(Entrega final)*
