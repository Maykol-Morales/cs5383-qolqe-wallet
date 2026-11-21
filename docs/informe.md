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

**Contrato:** el CLI de Schemathesis (`python demo.py schemathesis`) se ejecuta contra `/openapi.json` de un uvicorn real en un subproceso (30 ejemplos por operación, `--seed 1`). Es la única ejecución del contrato: en el CI es el primer job (`contrato`) y su código de salida es el gate, antes de los escenarios BDD y la web; deja VCR + HAR (cada caso con su petición y respuesta, base del dashboard de contrato) y JUnit para la trazabilidad. Hasta la Parte 2 corría además dentro de pytest (`tests/api/test_contrato.py`, 15 ejemplos con `derandomize`); se retiró para no ejecutar dos veces lo mismo con configuraciones distintas. Se excluyen logout, sesiones, reloj, reinicio y cierre de cuenta (invalidan la sesión compartida). Se validan los checks de conformidad (sin 5xx, códigos de estado, content-type, cabeceras y esquema de respuesta) y **no** `positive/negative_data_acceptance` ni `Allow` en 405, que daban ruido: p. ej. aceptar `correo: ""` en el registro o rechazar `monto=0`, que son decisiones de negocio documentadas. **Resultado: 60 operaciones conformes** con ejemplos fijos (`derandomize`). Observación sin confirmar: en la primera corrida del CI de GitHub (semilla aleatoria, Python 3.12) Schemathesis obtuvo un `500` en `POST /api/usuarios` con `{"celular":"914710469","dni":"14710469","nombres":"00","pin":"0849","correo":"1@1.com"}`; ese cuerpo da `201` en una BD limpia y no se reprodujo en 6 corridas locales (3.12 y 3.14, hasta 100 ejemplos). Se explicó después: es **DEF-15** (la respuesta sale antes del commit, así que repetir el registro en milisegundos da `500` por `UNIQUE constraint failed`). El HAR del run 42991620965 lo mostró con dos `POST /api/usuarios` idénticos seguidos, y `tests/api/reproducir_def15.py` lo reproduce de forma determinista (§5).

**Corrida manual del CLI con todos los checks** (Schemathesis 4.31.1, `schemathesis run /openapi.json --max-examples 30 --checks all`, mismas exclusiones): 60 operaciones, 2 782 casos, 44 hallazgos, clasificados así: **(a) "rechazó una solicitud válida según el contrato" (23)**: el contrato es más laxo que las reglas de negocio (`monto=0` en recargas/solicitudes/comisión, categoría ajena como filtro, celular/color/tipo permitidos por el esquema pero no por la regla); es **imprecisión del contrato** (faltan `minimum`/`enum`), no defecto del código, porque las reglas están en `requisitos.md`. **(b) "aceptó una solicitud inválida según el contrato" (3)**: `pin` y `celular` más largos que `maxLength` en login/desbloqueo (responden 401/404 en vez de 422) y `cci` de tipo incorrecto en transferencias; **observaciones de bajo impacto** (el servidor igual no actúa), pendientes de decidir si se endurece el esquema. **(c) `Allow` inválido en 405 (17)**: ruido de FastAPI, no se considera defecto. **(d) "recurso no disponible tras crearlo" (1)**: crear un recurso y leerlo de inmediato da 404. Es la misma ventana de DEF-15 (la lectura llega antes del commit); no reapareció al repetir la corrida el 2026-11-20 (40 hallazgos: 19 de (a), 4 de (b), 17 de (c), ninguno de (d) ni 5xx), así que se atribuye a DEF-15 sin registrarlo aparte. Ningún 5xx. Reporte JUnit generado localmente (no versionado).

**Comparativa detallada Schemathesis vs. features** (corrida del 2026-11-20, 50 hallazgos, 2 321 casos, la misma del dashboard): `docs/comparativa-schemathesis.md` lista cada hallazgo con su petición y respuesta, indica si un escenario nuestro ya cubría esa regla, qué descubrió Schemathesis que los features no (campo `cci` sobrante ejecutando una transferencia `QOLQE`, fecha numérica `hasta=0`, ids fuera de rango, DEF-15) y qué defectos solo detectan los features (13 de 15).

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
| CP-W17, CP-W18, CP-W19 | HU-N-01 | El registro rechaza DNI de 7 dígitos, celular ya registrado y celular que no empieza con 9 (mensaje exacto y sin salir de `/registro`) |
| CP-W20 | HU-N-02 | Tres PIN incorrectos bloquean la cuenta (423); un cuarto intento con el PIN correcto sigue bloqueado |
| CP-W21 | HU-N-02 | Una cuenta cerrada (semilla Fabián) no puede ingresar |
| CP-W22 | HU-N-05 | El perfil rechaza nombres de 1 carácter (valor límite inferior, 2 a 80) |
| CP-W23 | HU-N-06 | Cerrar la cuenta con PIN incorrecto (`PIN_INCORRECTO`) y la cuenta sigue abierta |
| CP-W24, CP-W25 | HU-N-07 | Transferirse a uno mismo y a un celular no registrado se rechazan al confirmar |
| CP-W26 | HU-N-07 | Una cuenta nueva con S/ 0.00 recibe `SALDO_INSUFICIENTE` al transferir |
| CP-W27 | HU-N-08 | CCI de 10 dígitos rechazado |
| CP-W28 | HU-N-08, HU-N-09 | Comisión interbancaria mínima: S/ 10.00 paga S/ 1.00 (no 1.5 % = S/ 0.15) |
| CP-W29 | HU-G3-01 | Un rango de 91 días se rechaza (valor límite del máximo de 90) |
| CP-W30 | HU-G3-01 | Filtrar por "Transferencias enviadas" |
| CP-W31 | HU-G3-02 | Detalle del movimiento más reciente: mismo código, tipo e importe |
| CP-W32, CP-W33 | HU-G3-03 | Categoría de 2 caracteres y nombre repetido en otra capitalización se rechazan |
| CP-W34 | HU-G3-06 | Eliminar una categoría la quita de la lista y baja el contador a "2 de 10" |
| CP-W35, CP-W36 | HU-G3-05 | Editar una categoría (nombre y color) y rechazar un nombre de 2 caracteres desde el diálogo |
| CP-W37 | HU-G3-04 | Categorías en orden alfabético con su contador (Comida 0, Familia 5, Servicios 5) y «3 de 10» |
| CP-W38, CP-W39 | HU-G3-08 | El CSV trae los 20 movimientos del rango aunque la tabla muestre 10 por página, y exportar filtrado por categoría |
| CP-W40 | HU-G3-08 | Exportar un rango de 91 días se rechaza y no se descarga ningún archivo |
| CP-W41, CP-W42 | HU-G3-01 | Filtrar por categoría y por un rango de fechas que excluye los últimos 30 días |
| CP-W43, CP-W44 | HU-G3-07 | Valor límite de la nota: 101 caracteres se rechazan, 100 se guardan |
| CP-W45 | HU-G3-07 | Quitar la categoría de un movimiento ya clasificado |
| CP-W46 | HU-N-03 | Sin sesión, `/inicio`, `/transferir`, `/perfil` y `/historial` llevan a `/login` |
| CP-W47, CP-W48 | HU-N-05 | Cambiar el correo (queda guardado tras recargar) y rechazar uno con formato inválido |
| CP-W49 | HU-N-07 | Límite diario (Diego, S/ 1 000): dos transferencias de S/ 500 y la siguiente de S/ 0.01 se rechaza |
| CP-W50 | HU-N-07 | El destinatario (Bruno) ve su saldo de S/ 850.00 y la transferencia recibida en el inicio |
| CP-W90 | HU-G3-03, HU-G3-07 | El mismo flujo de CP-W01 con `browser.act()` (IA), repetido desde la caché |

Entrega final: se pasó de 16 a **50 escenarios web** (Núcleo 11 → 28, G3 5 → 22, más el `@ia`). Sin esperas fijas (solo `waitUntil`/`expect` con auto-espera). Como DEF-15 hace que Qolqe responda antes de guardar, las verificaciones de estado guardado usan `recargarHasta` (`tests/e2e/pages/espera.js`: recarga y comprueba hasta que aparece o vence a los 20 s), que no oculta un defecto real: si el dato nunca se guarda, el caso falla. Pasan 3 veces seguidas en local y en cada run del pipeline. DEF-14 (`@DEF-14`) corre aparte y debe fallar.

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
**IA en el ciclo** (`docs/ia-en-el-ciclo.md`, 2026-11-21): se aprovechó la IA de las herramientas que ya usamos. (1) **El MCP de WebdriverIO dentro del ciclo**: el job `exploracion` de `pruebas.yml` lanza un agente de Claude que, con solo las herramientas del MCP, explora la interfaz de Qolqe buscando comportamientos que contradigan las reglas de negocio; recibe la lista de defectos conocidos para buscar cosas nuevas y entrega un resumen del run con los hallazgos candidatos y el costo de la sesión (unos US$ 0,5). Corre solo a pedido (*Run workflow*, casilla `exploracion`) y con el secreto `ANTHROPIC_API_KEY`; sin él se omite, y nunca forma parte del gate. Respalda el análisis de `docs/comparativa-mcp-agentes.md`, cuya sesión exploratoria halló 4 defectos conocidos sin ningún falso positivo. (2) El resumen de `@wdio/ai-service` (llamadas de IA, cuántas salen de la caché, pasos curados y tokens) que antes se perdía en el log se publica ahora en el dashboard del run. Se evaluó y descartó Allure Agent Mode (solo reordena datos), la IA de Qase es de pago, y se construyó y retiró un triage de fallas con Claude. El job de exploración no se ha ejecutado en el CI (no hay clave en la máquina de desarrollo); el flujo se probó en local.

**Comparativa de IA** (`docs/comparativa-ia.md`): para la misma tarea, Page Objects 3,6 s y 0 tokens; `browser.act` graba una vez (~137k tokens, US$ 0,29, 34 s) y repite gratis en 6,8 s; un agente Claude (`claude -p`) cuesta en cada corrida (US$ 0,36 con Sonnet 5, US$ 0,04 con Sonnet 5.5) y tarda 17–165 s. Conclusión: Page Objects para la regresión; `act` con caché versionada si se quiere escribir pasos como intención; el agente, para explorar y generar pasos, no como suite.

**Comparativa del conector MCP de WebdriverIO frente a un agente de código** (`docs/comparativa-mcp-agentes.md`, 2026-11-21): la misma tarea con Claude Code (Sonnet 5.5, 3 corridas por enfoque, todas correctas). El MCP (`@wdio/mcp`) tarda 24 s y cuesta US$ 0,078; `wdio session` en la terminal, 45 s y US$ 0,067; scripts propios del agente, 42 s y US$ 0,103. El MCP gasta casi el doble de contexto (177 k frente a ~96 k tokens) porque hace más llamadas pequeñas, y suma unos 3 mil tokens fijos por sus herramientas; entre MCP y CLI no hay diferencia de precio demostrable con 3 corridas. Claude in Chrome (la extensión, en el Chrome real) es el más caro y lento: US$ 0,140 y 87 s (+79 % frente al MCP), con 30 turnos y el mayor costo fijo (15 k tokens), sobre todo por sus 19 a 21 acciones de `computer` una por una. Conclusión: ninguno sirve como regresión en cada push (paga tokens y no es determinista); para explorar y escribir pruebas cuestan de 7 a 10 centavos por tarea y valen la pena. La documentación oficial no publica cifras de tokens ni de costo, así que las medidas son propias. El MCP se usó además de verdad: una sesión exploratoria (US$ 0,49, 2,5 min) halló 4 problemas, todos defectos ya registrados (DEF-02, DEF-03, DEF-06 y DEF-07), sin ningún falso positivo ni defecto nuevo, y se le pasaron 4 de los 8 alcanzables por interfaz; complementa a la suite. La regla de trabajo (la IA explora, el Page Object corre en el CI) y el `.mcp.json` están en `tests/e2e/README.md` §6.

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

- **Cada nivel encontró defectos que los otros no veían.** Los 12 defectos abiertos de la API (DEF-01 a DEF-10, DEF-12 y DEF-13; `docs/defectos.md`) los detectó pytest-bdd. Todos son reglas de negocio con peticiones válidas según el OpenAPI (redondeo, saldo, límite diario, propiedad, sesión), así que el contrato no podía verlos. **DEF-14 solo se ve en la web**: la API responde según el requisito, y es la UI la que arma el rango con la fecha del navegador. Apareció en la CI de GitHub, con el navegador en UTC. **DEF-15 lo encontró Schemathesis**: un 500 intermitente al repetir el registro (la respuesta sale antes del commit), que ninguna prueba escrita a mano provocaba porque exige dos peticiones idénticas en milisegundos; en la web se veía como un rebote del login. Además, con todos los checks, dejó 50 hallazgos (28 de **imprecisión del contrato**: faltan `minimum`/`enum`; 4 de datos inválidos aceptados, 17 de `Allow` y DEF-15), de los que uno terminó como **DEF-17** (`cci` inválido ignorado en una transferencia a Qolqe); §2 y `docs/comparativa-schemathesis.md`.
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

Gráficos: `k6.png` y `recursos.png` en cada carpeta. **Resumen por corrida:** el dashboard web de k6 (`dashboard.html`) solo grafica las métricas globales, sin etiquetas: no trae los percentiles por tipo de operación (consulta frente a dinero), no dice si cada umbral pasó y abrevia el total de peticiones («7.3k»). Esos datos sí están en la consola (`k6.txt`) y en `summary.json`, así que `resumen.py` arma con ellos un `resumen.html` por carpeta (percentiles por tipo, ✓/✗ de cada umbral, totales exactos, recursos, integridad y endpoints) y `resultados/index.html` con una fila por corrida.

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
| DEF-15 | Qolqe responde antes de guardar la operación: una petición inmediata no ve el cambio (500 al repetir el registro, 401 con un token recién emitido) | Alta | Abierto |
| DEF-16 | Con más de 40 inicios de sesión a la vez, Qolqe responde 500 «database is locked» (rendimiento, Parte 3) | Alta | Abierto |
| DEF-17 | Una transferencia a Qolqe con un `cci` inválido se ejecuta aunque el OpenAPI lo declara de 20 dígitos (lo halló Schemathesis, entrega final) | Baja | Abierto |

## 6. Conclusiones y recomendaciones
*(Entrega final)*

### 6.1 Estado de calidad

**Qolqe Wallet 1.0.0 no está listo para producción.** Las 17 HU del alcance (Núcleo + G3) tienen casos ejecutados en cada run del pipeline. La mayoría de los criterios se cumple, pero quedan **16 defectos abiertos: 3 críticos, 7 de severidad alta, 4 media y 2 baja** (§5). Los tres críticos tocan el dinero o la sesión:

- DEF-04: una interbancaria deja el saldo negativo.
- DEF-06: se transfiere a una cuenta cerrada y el dinero se pierde.
- DEF-05: el logout no invalida el token.

| Nivel | Resultado (2026-11-20) | Qué dice de la calidad |
|---|---|---|
| Contrato (Schemathesis) | 60 operaciones conformes con los checks del gate; ningún 5xx salvo DEF-15 | La API respeta su OpenAPI, pero el OpenAPI es más laxo que las reglas (44 hallazgos de imprecisión, §2) |
| API (pytest-bdd) | 371 pasan (251 del alcance y 120 de los módulos de otros grupos, `features/otros_*.feature`), 24 *xfail* estrictos (los defectos de API), 1 omitido (`@concurrencia`); cobertura de `qolqe/` 90 % en local (antes 64 %; la meta era 75 %) | Las reglas de G3 se cumplen salvo el día `hasta` (DEF-07), la propiedad de los datos (DEF-08, DEF-09) y los nombres duplicados (DEF-10). En el núcleo fallan las reglas de dinero y de sesión |
| Web (WebdriverIO) | 17 casos (CP-W01–W16, W90), 3/3 corridas en verde por run; DEF-14 falla como se espera | Los flujos principales funcionan en Chrome. El historial depende de la hora del navegador (DEF-14) |
| Rendimiento (k6) | Hora punta y pico cumplen con amplio margen (p95 25 ms consultas, 115 ms dinero, 0 fallas, integridad OK); capacidad 700 usuarios simultáneos ≈ 7× la hora punta | La campaña «Quincena Qolqe» se sostiene si la entrada es gradual. Al pasar de 700 usuarios el servicio colapsa del todo (DEF-16) |

El quality gate (G1–G6) pasa en `final` (run 44710360962). Pasa porque los defectos conocidos están marcados (`@DEF-nn` como *xfail* estricto, DEF-14 invertido, DEF-15 tolerado en G1). Un gate en verde quiere decir que no apareció ninguna falla nueva, no que la aplicación esté sana.

### 6.2 Riesgos abiertos

Ordenados por impacto para el usuario:

1. **Pérdida o descuadre de dinero:** DEF-04 y DEF-06 (críticos) y DEF-13, porque el límite diario se evade con interbancarias. Bajo estrés, además, 3 operaciones se aplicaron aunque el cliente recibió error o timeout. Sin clave de idempotencia, un reintento cobra dos veces (§4.8).
2. **Sesión y privacidad:** DEF-05 (un token robado sigue sirviendo tras el logout), DEF-03 (los fallos de PIN se acumulan aunque haya un ingreso correcto en medio, así que se bloquea al usuario legítimo), DEF-08 y DEF-09 (movimientos de otro usuario visibles).
3. **Escritura después de responder (DEF-15, DEF-16):** una sola causa, el commit en el cierre de `obtener_bd`, produce tres síntomas. Con poca carga, una petición inmediata no ve lo recién guardado (500 al repetir el registro, 401 con un token nuevo). Con mucha carga, el colapso por «database is locked». Es el defecto con más alcance: afecta a todas las operaciones que escriben.
4. **Comprobantes ambiguos:** DEF-12 (dos operaciones del mismo segundo comparten código) y DEF-01 (redondeo de la comisión).
5. **Lo que no se probó:**
   - la resistencia de 18 h (§4.3);
   - la concurrencia real de HU-N-07 CA5 (`@concurrencia`; el estrés la ejercita, pero sin un caso que la aísle);
   - los navegadores distintos de Chrome;
   - los módulos G1, G2, G4, G5 y G6 en profundidad: tienen 73 escenarios de camino feliz y errores principales para cobertura, sin análisis de valores límite. Al escribirlos aparecieron 15 comportamientos que contradicen `requisitos.md` (bono desde S/ 30, 6.ª recarga, mora del día de vencimiento, alias con ñ, PIN reutilizado, entre otros); se quitaron de la suite y no se registraron como defectos porque son de otros grupos ([`hallazgos-otros-modulos.md`](hallazgos-otros-modulos.md));
   - las interpretaciones de §1, que siguen sin confirmar con el docente.

### 6.3 Lecciones aprendidas

- **Cada nivel de prueba encontró defectos que los otros no podían ver** (§3.2):
  - pytest-bdd encontró los 12 de reglas de negocio;
  - la web, DEF-14;
  - Schemathesis, DEF-15;
  - k6, DEF-16.

  Ninguna herramienta habría bastado sola. DEF-15 y DEF-16 tienen la misma raíz y salieron por caminos distintos: el contrato lo vio como un 500 aislado en la CI y el estrés como un colapso.
- **Diseñar los casos desde los requisitos y no desde el código.** El análisis de particiones y valores límite (`casos-equivalencia-limites.md`) se hizo solo con `requisitos.md` y después se contrastó con los `.feature`. Al contrastarlo salieron fronteras que los escenarios no tenían (los 90 días exactos, las páginas 10/11/20/21, la página 0, el monto de S/ 500.00 contra 500.01). DEF-07 es justamente un defecto de frontera: el día `hasta` del rango queda fuera.
- **Un caso que solo mira el código de estado puede pasar sin probar nada.** El dashboard de contrato encontró 44 escenarios BDD que el contrato ya cubría. Se reforzaron con el paso «no se persiste ningún cambio» y quedaron 12. Pasa algo parecido con el escenario de HU-N-03 CA2, que hoy pasa sin probar nada porque DEF-05 lo vacía.
- **Lo intermitente se vuelve determinista o se registra como defecto.** El 500 «no reproducible» de la primera CI resultó ser DEF-15 cuando se tuvo el HAR del run. Las esperas de la UI se resolvieron esperando el `PUT` y no con pausas fijas. La zona horaria del navegador quedó fijada después de ver el historial vacío en un runner UTC.
- **El entorno cambia la conclusión de rendimiento.** Con el modelo anterior, el mismo script quebraba a 400 usuarios en Docker local y no quebraba a 1 000 en EC2. Por eso la capacidad se informa como línea base relativa a un entorno fijo (1 CPU, 1 GB) y no como cifra absoluta.
- **Marcar los defectos conocidos en el pipeline** (*xfail* estricto, DEF-14 invertido) mantiene el gate útil: si alguien corrige un defecto sin retirar su marca, la CI falla y avisa.

### 6.4 Recomendaciones para el equipo de desarrollo

1. **Corregir primero los críticos y los de dinero:** DEF-04, DEF-06, DEF-05 y DEF-13, y después DEF-03, DEF-08 y DEF-09 (seguridad y privacidad). Los escenarios `@DEF` ya existen: al corregir cada uno, su caso pasa a XPASS y basta con retirar la marca.
2. **Hacer el commit dentro del endpoint y acortar las transacciones** (DEF-15 y DEF-16). Es un solo cambio en `qolqe/bd.py` y en las operaciones que escriben, y resuelve a la vez la lectura inmediata y el colapso por candado. Después hay que repetir el estrés, porque el siguiente límite esperado es el CPU del login (PBKDF2).
3. **Agregar idempotencia en las operaciones de dinero** (una clave por transferencia, recarga y pago) y responder 503 con `Retry-After` en lugar de 500 cuando el servicio no da abasto.
4. **Ajustar el OpenAPI a las reglas** (`minimum`, `maxLength`, `enum` en monto, PIN, celular, color y tipo). Así Schemathesis puede validar también los rechazos y no solo la forma de las respuestas.
5. **Calcular las fechas del historial en el servidor o en hora de Lima** (DEF-14) y no con la hora del navegador.
6. **Mantener el pipeline y la cobertura** (90 % en local tras sumar los módulos de otros grupos) y pasar a sus equipos los 15 comportamientos que contradicen `requisitos.md` en G1, G2, G4, G5 y G6.
7. **Para la campaña:** escalonar las notificaciones, alertar cerca de 600 usuarios simultáneos (85 % de la capacidad) y medir la resistencia de 18 h en un entorno dedicado si el negocio la exige (§4.8).
