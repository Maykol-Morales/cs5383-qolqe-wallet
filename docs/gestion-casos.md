# Gestión de casos: Qase y trazabilidad entre ejecuciones

Punto 3 del feedback: la trazabilidad no debe mirar solo el último run. Se usa una herramienta de gestión de casos
(**Qase**) y, además, el sitio de Pages guarda el resultado de cada caso en cada run (no se depende de la cuenta externa).

## Comparación (consultado el 2026-11-10)

Contexto: 2 estudiantes, ~160 escenarios Gherkin (pytest-bdd en la API, WebdriverIO + Cucumber en la web), CI en
GitHub Actions, sin servidor propio.

| Criterio | Qase | Kiwi TCMS |
|---|---|---|
| Costo / plan gratuito | Plan Free sin costo, "para estudiantes, hobbyistas, educadores": 4 usuarios, 2 proyectos, 2 runs activos, 5 000 resultados por API al mes, historial de 30 días ([precios](https://qase.io/pricing)) | Código abierto (GPLv2) y gratis si lo hospedas tú; el SaaS (*Private Tenant*) cuesta 150 USD/mes ([kiwitcms.org](https://kiwitcms.org/)) |
| Hospedaje | SaaS (app.qase.io); no hay nada que instalar | Autohospedado con Docker (`pub.kiwitcms.eu/kiwitcms/kiwi`) o el tenant de pago; la demo pública no es para datos reales ([kiwitcms.org](https://kiwitcms.org/)) |
| API de resultados | REST JSON con token en la cabecera `Token`: crear run, resultados en lote (200 por petición), cerrar run ([crear run](https://developers.qase.io/reference/create-run), [resultados en lote](https://developers.qase.io/reference/create-result-bulk), [completar run](https://developers.qase.io/reference/complete-run)) | JSON-RPC / XML-RPC (biblioteca `tcms-api`) ([kiwitcms.org](https://kiwitcms.org/)) |
| JUnit / pytest / WebdriverIO | Reporters oficiales `qase-pytest` (con soporte de pytest-bdd) y `wdio-qase-reporter` (opción `useCucumber`) ([pytest](https://developers.qase.io/docs/pytest), [WebdriverIO](https://developers.qase.io/docs/webdriverio)) | Plugin `kiwitcms-junit.xml-plugin` que lee junit.xml ([repo](https://github.com/kiwitcms/junit.xml-plugin)); otros plugins por framework ([lista](https://kiwitcms.readthedocs.io/en/stable/plugins/automation-frameworks.html)) |
| Historial por caso | Sí, por caso y por run; en Free se conservan 30 días | Sí, sin límite (es tu base de datos) |
| Trazabilidad a requisitos | Tags, suites y enlace a issues (las integraciones como GitHub son de pago) | Requisitos en el plan de prueba y enlace a bugs/issues |

**Elegimos Qase.** Kiwi TCMS es la opción abierta, pero sin servidor propio exige pagar el tenant o montar y mantener
un Docker con base de datos fuera del CI; Qase Free cubre un equipo de 2 sin costo y solo pide un token. Sus límites
caben en el uso del curso: subimos **un resultado por caso y run** (~160), unos 31 runs al mes dentro de los 5 000 (cada push a una rama vigilada y cada PR es un run: si se pasa, Qase rechaza los resultados y el paso, con `continue-on-error`, no tumba el pipeline)
resultados; cada run se cierra al terminar (máx. 2 activos). Los 30 días de historial de Qase se compensan con el
historial propio de Pages (abajo).

No usamos los reporters oficiales: el mapeo escenario ↔ JUnit ya existe en `.github/scripts/reportes.py` (el que arma
la matriz), así que `.github/scripts/qase.py` lo reutiliza (`casos_con_resultados()`) y Qase muestra lo mismo que
`trazabilidad.html`, sin tocar `tests/api/` ni `tests/e2e/` ni agregar dependencias.

## Mapeo de nuestros IDs

| Nuestro | En Qase |
|---|---|
| `CP-A-<feature>-nn` (API, n.º de escenario en su `.feature`) y `CP-Wnn` (web, etiqueta `@CP-Wnn`) | Comienzo del título: `CP-A-historial-03 · <escenario>`. El script reconoce un caso ya creado por ese prefijo; si no existe, lo crea (`POST /case/{proyecto}/bulk`) |
| `@HU-…` | Tag del caso (filtrar por tag = casos de una historia) |
| `@DEF-nn` | Tag del caso; su resultado va como `failed` con `defect: true` y el comentario `defecto conocido` |
| Nivel (`API`, `Web E2E`, `Web E2E (IA)`) | Tag del caso |
| Run de CI | Un *test run* por run: `CI run #<n> · <commit> <rama>`, descripción con el enlace al run y al commit |
| Resultado de la matriz (`pasa k/n`, `defecto conocido`, `FALLA`, `omitido`) | `passed` / `failed` (defect) / `failed` / `skipped`, con el texto de la matriz como comentario |

Un caso con varias ejecuciones en el run (ejemplos de un Outline, 3 corridas web) sube un solo resultado: el agregado
de la matriz. Si se renombra un escenario, Qase conserva el caso viejo (el ID manda); el título nuevo se corrige a mano.

## Configuración (una vez)

1. Crear cuenta en https://qase.io (plan Free) y un proyecto con código `QOLQE` (Project code).
2. Generar un token personal de API en el perfil (*API tokens*, https://app.qase.io/user/api/token).
3. En GitHub: *Settings → Secrets and variables → Actions → New repository secret*, nombre `QASE_API_TOKEN`.
   Si el código del proyecto no es `QOLQE`, agregar la variable de repositorio `QASE_PROJECT`.
4. El paso `Qase` del job `reportes` sube cada run. Sin el secret (forks, PR) avisa y sale con 0.

Local: `python .github/scripts/qase.py --seco` imprime las peticiones (JSON) que enviaría con los JUnit que haya en
`reportes/`, `reporte-schemathesis/` y `tests/e2e/reportes/`; con `QASE_API_TOKEN=…` las envía.

## Historial propio en Pages

`reportes.py sitio` suma cada run a `historial.json` (últimos 30). Además de los totales, cada fila guarda
`casos` = `{ID: p|d|f|o}` (pasa, defecto conocido, falla, omitido). `trazabilidad.html` y `docs/trazabilidad.md`
muestran los últimos 10 runs de cada caso y la marca **inestable** cuando un caso pasó y falló entre esos runs
o dentro del mismo run (p. ej. una corrida web de 3). Las filas anteriores a este cambio solo tienen totales y se
saltan en la serie por caso; la tendencia del dashboard las sigue usando.
