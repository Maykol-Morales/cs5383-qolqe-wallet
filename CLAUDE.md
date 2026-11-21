# CLAUDE.md

## Qué es este repo

Proyecto 2 del curso **CS5383 Pruebas y Verificación de Software** (UTEC). Contiene **Qolqe Wallet**, una billetera digital ficticia (FastAPI + SQLite, UI en HTML estático) que es el **sistema bajo prueba (SUT)**, y el trabajo de pruebas del **Grupo 3 (G3 · Historial y categorías)** — integrantes Sebastian y Maykol.

**Regla principal: NO modificar `qolqe/`.** El trabajo es probarlo, no repararlo. Todo cambio va en `features/`, `tests/`, `docs/`, `.github/`, `IA.md`.

## Estado por partes

| Parte | Contenido | Estado |
|---|---|---|
| 1 | Pruebas de API (núcleo + G3), contrato con Schemathesis, 12 defectos, análisis EP/VL mapeado a escenarios | Hecha |
| CI | `.github/workflows/pruebas.yml`: contrato → (api ∥ web ×3) → reportes (gate G1–G6, Qase vía `.github/scripts/qase.py`) → Pages; matriz `docs/trazabilidad.md` | Hecha (Pages publica desde `final`) |
| Reportes | Allure 3 (`demo.py reporte`) y dashboard de Schemathesis + comparativa con BDD (`demo.py schemathesis` / `dashboard`) | Hecha |
| Presentación | Deck final de 13 slides, mapa visual y guion `demo.py` | Hecha (ver "Presentación y demo") |
| 2 | Pruebas web E2E: WebdriverIO 10 + Cucumber + Page Objects + Allure en `tests/e2e/` (migrado del repo `cs5383-webdriverio`) | Hecha: G3 (CP-W01–W05, W90) + Núcleo (CP-W06–W28 y W46–W50, `nucleo.feature`) + G3 ampliado (CP-W29–W45); 50 escenarios web + 1 `@ia`; informe §3, §3.1 Page Object y §3.2 herramientas |
| Final | Parte 3 traída a `final` sin merge (copia de archivos, 2026-11-20); informe §6; cobertura 90 % con `features/otros_*.feature`; `demo.py final`; deck final de 16 slides (ver "Presentación y demo") | Hecha (commits `1898475` Maykol, `b74e6b0` Sebastián; CI del run 44796177354 por confirmar) |
| 3 | Rendimiento con k6 (`tests/performance/`, `correr.py` + Docker 1 CPU/1 GB, 4 flujos 20/40/25/15); entregable `tests/performance/Informe_Rendimiento_G3.docx`, resumen en `docs/informe.md` §4 | Hecha en Docker/Windows (capacidad 700 VUs); falta re-correr en EC2 con el modelo nuevo |

## Estructura

```
qolqe/                 SUT (no tocar)
  main.py              app FastAPI; config.py (env vars); bd.py (SQLite); semilla.py (datos de prueba)
  api/                 routers por módulo: autenticacion, cuentas, transferencias, movimientos, categorias,
                       recargas, servicios, contactos, solicitudes, limites, seguridad, soporte_pruebas
  reglas/              reglas de negocio puras (sin BD ni red): nucleo, historial, recargas, servicios,
                       contactos, limites, seguridad
  contrato.py, errores.py, dinero.py, reloj.py, credenciales.py, dependencias.py, operaciones.py, transacciones.py
  web/                 páginas HTML + static/app.js, estilos.css
features/              escenarios Gherkin: nucleo_{registro,sesion,cuenta,transferencias}, historial, categorias;
                       otros_{recargas,servicios,contactos,limites,seguridad} (G1, G2, G4–G6, @fuera-de-alcance, solo cobertura)
tests/
  api/conftest.py      fixtures (http, Contexto) y pasos comunes
  api/test_{nucleo,historial,contrato}.py   pasos pytest-bdd + contrato Schemathesis
  test_humo.py         prueba de humo
  e2e/                 Parte 2, proyecto Node propio: features/, steps/, pages/ (Page Objects), wdio.conf.js,
                       allurerc.mjs, demo.mjs; npm se corre dentro de tests/e2e/ (README propio)
docs/                  requisitos.md (HU, CA, RN), informe.md, defectos.md, plantilla-informe.md, gestion-casos.md (Qase),
                       casos-equivalencia-limites.md (análisis EP/VL), formato-particiones.md (formatos A1/B1),
                       hallazgos-otros-modulos.md (15 comportamientos de G1/G2/G4–G6 que contradicen requisitos.md)
demo.py                guion de la demo, multiplataforma (preparar, ensayo, demo, schemathesis, plan-b)
demo.sh                Linux/macOS: prepara .venv, node_modules y revisa gh; lanzar | mostrar (demo CI) | web (plan B) | resto → demo.py
IA.md                  declaración de uso de IA (actualizar al usar IA en nuevas tareas)
```

## Comandos

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn qolqe.main:app --reload        # SUT en :8000 (un solo proceso, sin --workers); /docs = Swagger
pytest -rx                             # todo (~1 min); defectos conocidos salen xfailed
pytest tests/api -m "HU-G3-01"         # una historia (cada escenario lleva etiqueta @HU-…)
MOSTRAR_DEFECTOS=1 pytest tests/api    # los defectos fallan a la vista
EVIDENCIA=fallos|todo|no pytest …      # adjuntos Allure (también npm test en tests/e2e: capturas); en CI, input evidencia
QOLQE_URL=http://localhost:8000 pytest tests/api/test_nucleo.py   # contra servidor real
pytest --cov=qolqe                     # cobertura (90 % local; incluye features/otros_*.feature de G1, G2, G4–G6)
python demo.py preparar | ensayo | demo | schemathesis [g3] [todos] | plan-b   # Windows: py demo.py …; ver "Presentación y demo"
cd tests/e2e && npm install && npm run demo   # Parte 2: levanta Qolqe desde la raíz, flujo, mutación, Allure
npm test                               # (en tests/e2e, con Qolqe en :8000) escenarios web; HEADED=1 muestra Chrome
```

Resultado de referencia (Parte 1, 2026-10-17): `252 passed, 1 skipped, 24 xfailed` + 60 subpruebas de contrato (desde la rama `final` el contrato ya no corre en pytest: `251 passed`), 141 escenarios Gherkin (G3 70, núcleo 71), 12 defectos abiertos, unos 70 s. El skip es el escenario `@concurrencia` (pertenece a la Parte 3).

Resultado actual (`final`, 2026-11-20): `371 passed, 1 skipped, 24 xfailed` (251 del alcance + 120 de `otros_*`, en `tests/api/test_otros_modulos.py`), cobertura de `qolqe/` 90 % local (antes 64 %; CI daba 69 % por otra versión de Python), 16 defectos abiertos (con DEF-17 agregado en la entrega final: `371 passed, 1 skipped, 25 xfailed`).

## Convenciones de las pruebas

- **Fuente de verdad = `.feature`**; `pytest-bdd` los enlaza con pasos Python. Etiquetas: `@HU-…` (historia), `@DEF-nn` (defecto conocido), `@concurrencia`.
- **Defectos conocidos**: los escenarios `@DEF-nn` son `xfail(strict)`. Si un defecto se corrige pasa a XPASS y pytest falla — es intencional.
- **Aislamiento**: cada escenario reinicia datos con `POST /api/pruebas/reiniciar` (propiedad *Independent* de FIRST). Por defecto la app corre in-process (TestClient) con BD temporal; con `QOLQE_URL` va contra un servidor real.
- **Contrato**: única ejecución con el CLI (`demo.py schemathesis`: uvicorn temporal, 30 ejemplos, `--seed 1`, deja HTML + VCR + HAR + `reporte-schemathesis/junit-contrato.xml`; sale con el rc del CLI). `test_contrato.py` se borró en `final` por duplicar la corrida.
- Todo nuevo defecto: reproducirlo primero contra la API, agregarlo a `docs/defectos.md` (formato DEF-nn) y a la tabla de la sección 5 de `docs/informe.md`.
- Documentación e idioma: **español** (código, escenarios, docs, commits).

## Análisis de equivalencia y valores límite

`docs/casos-equivalencia-limites.md` es la base de diseño de los casos: se construyó **solo desde `requisitos.md`** (RN/HU/CA), no desde los `.feature`, y luego se contrastó con ellos.

- **Una técnica por elemento** (EQ o VL; ambas solo en casos extremos). Formatos: A1 para equivalencia (`EQ-<HU>-nn`: partición, tipo V/I, representante, esperado) y B1 para límites (`VL-<HU>-nn`: variable, frontera, valor, lado, esperado). El cierre de cuenta (HU-N-06) es una tabla de decisión `DT-N06-R1…R8`.
- Decisiones tomadas: monto de transferencia y comisión = EQ; token a 30 min (a los 30:00 exactos ya vence), límite diario y saldo vs monto+comisión = VL; login sin `dispositivo_id` es válido (sin SMS); simulación con tipo inexistente se rechaza y sin tipo = QOLQE; categoría ajena como filtro = `FILTRO_INVALIDO`; página 0 = `FILTRO_INVALIDO`; 0 movimientos = 1 página; nombre de categoría solo con espacios = inválido; orden de validación del cierre: PIN → saldo → solicitudes; solicitud vence a las 48 h (R-G4-05); redondeo validado por el servidor.
- Monto no numérico o vacío responde 422 `SOLICITUD_INVALIDA` (validación de Pydantic), no `MONTO_INVALIDO`.
- Referencia externa: un análisis equivalente de otro grupo en `../proyecto2/features/g3/plantilla-analisis-ep-vl.md` (fuera de este repo, solo para contrastar).
- Al agregar un caso: primero la tabla del doc, luego el escenario/Example en `features/`, luego el paso en `tests/api/` si hace falta.

## Dominio (resumen)

- Módulos: **Núcleo** (registro, login/logout, perfil, saldo, cierre de cuenta, transferencias + comisión), G1 recargas, G2 servicios, **G3 historial/categorías/CSV**, G4 contactos/solicitudes, G5 límites/alertas, G6 seguridad/dispositivos/sesiones. Nuestro alcance: **Núcleo + G3**.
- Reglas clave: transferencia máx. S/ 500 por operación; comisión interbancaria 1.5 % (mín./máx.); 3 PIN fallidos → bloqueo 15 min (423); token JWT 30 min; historial máx. 90 días, páginas de 10; categorías máx. 10, nombre 3–20, paleta de 8 colores; nota 100 caracteres.
- Errores: JSON `{"codigo": "...", "detail": "..."}`; 404 también para recursos de otro usuario. Montos como texto con 2 decimales; fechas hora Lima.
- Datos semilla: Ana 987654321/4826 (principal, ~60 días de historial), Bruno 912345678/7391, Carla 956781234/5917, Diego 998877665/3604, Elena 923456789/8152 (bloqueada), Fabián 934567812/6029 (cerrada); usuarios de carga 900000001–900000200, PIN 2580, ~1 000 movimientos c/u (Parte 3).
- API de soporte (`QOLQE_MODO_PRUEBA=1`): `/api/pruebas/{reiniciar,reloj,notificaciones,saldo,procesar-diario}`. Reloj en memoria → un solo proceso.
- Env vars: `QOLQE_BD`, `QOLQE_MODO_PRUEBA`, `QOLQE_MINUTOS_TOKEN`, `QOLQE_CLAVE_SECRETA`.

## Defectos hallados (16 abiertos; detalle en `docs/defectos.md`)

DEF-01 redondeo comisión · 02 PIN descendente aceptado · 03 login exitoso no reinicia intentos · 04 interbancaria deja saldo negativo (Crítica) · 05 logout no invalida token (Crítica) · 06 transferencia a cuenta cerrada pierde dinero (Crítica) · 07 historial excluye el día `hasta` · 08 detalle de movimiento ajeno visible · 09 destinatario ve movimiento del emisor · 10 categoría editable con nombre duplicado · 11 (descartado: el token vence a los 30 min exactos, se acepta) · 12 dos operaciones del mismo segundo comparten código de operación · 13 el límite diario no cuenta las interbancarias · 14 (UI, Parte 2) historial vacío de noche si el celular no está en hora de Lima · 15 la respuesta sale antes del commit (500 al repetir el registro, 401 con token recién emitido; lo halló Schemathesis en CI, repro determinista `tests/api/reproducir_def15.py`) · 16 (rendimiento, Parte 3) más de 40 logins simultáneos → 500 «database is locked», misma raíz que 15 (`tests/performance/reproducir_def16.py`) · 17 (entrega final, Baja, lo halló Schemathesis) transferencia a Qolqe con `cci` inválido se ejecuta aunque el OpenAPI lo declara de 20 dígitos

## Presentación y demo

- **Estructura pedida por el docente**: 1) herramienta de automatización y justificación (1-2 slides), 2) módulo asignado, importancia y prioridad (1-2 slides), 3) diseño de casos funcionales y técnicos sobre una HU elegida, 4) demo en vivo (solo indicar que viene). El equipo eligió **HU-N-07** (núcleo, transferencias) y **HU-G3-01** (historial).
- **Artifacts** (privados; Maykol los comparte desde Share): presentación https://claude.ai/artifact/Y36yMfSCkNB16EiFANs8xK (13 slides: portada, herramienta, módulo, 4 de HU-N-07, 4 de HU-G3-01, técnicos, demo) y mapa visual https://claude.ai/artifact/KASkEjLiBq5AsLbhrKifQq. Se mantienen con las fuentes en el scratchpad de la sesión (no versionadas): hay que actualizar cifras en ambos cuando cambie el repo.
- **Deck final del proyecto (entrega final)**: https://claude.ai/artifact/J1zGptCteuY4Eg1UzNDDub (tipo Slides, v11 del 2026-11-20). 16 slides que cubren las 3 partes: cover, mapa, alcance, estrategia, p1-diseno, p1-resultados (371 casos, 24 xfail, 3 077 de contrato, 90 %), p2-web, p2-patron, pipeline, p3-modelo, p3-resultados, p3-estres (curva req/s de `estres-20261112-2024-docker/por-minuto.csv`), defectos, estado, lecciones, demo (4 pasos con tiempos reales del ensayo). Fuentes en el scratchpad de la sesión `e0458b44…/scratchpad/deck-final/project/` (deck.json, deck.css, slides/*.html), se publica con `root` = `…/deck-final`. Oradores [Maykol]/[Sebastian] en las notas (reparto supuesto). Mismo diseño bosque/crema/dorado.
- **Deck de la Parte 3**: https://claude.ai/artifact/NJZdBsUoPLMxe4PPvz2iUB (v20; 700 VUs en Docker, curva rehecha, oradores). Su slide de demo todavía dice EC2.
- Diseño de la presentación: fondo verde bosque / crema / dorado, Fraunces + DM Sans + JetBrains Mono; en el slide 2 se quitó Schemathesis a propósito (queda en el slide de técnicos como "Contrato OpenAPI").
- **demo.py** (solo stdlib; corre en Windows sin Bash ni curl; `demo.sh` prepara el entorno y lo invoca; `ci lanzar` dispara el pipeline y `ci` espera el run y abre Pages, Allure web y la matriz; documentado en README §7): `preparar` crea `.venv`; `ensayo` corre los 4 pasos (HU-G3-01, todo, DEF-07 con `MOSTRAR_DEFECTOS=1`, contrato) y mide tiempo; `demo` pausa con Enter; `schemathesis [g3] [todos]` levanta un servidor temporal, corre el CLI con `--seed 1` y abre el HTML en `reporte-schemathesis/` (ignorado por git); `plan-b` guarda la salida en `reportes/ensayo.txt`; `SIN_CONTRATO=1` omite el paso 4; `reporte` (y el final de `ensayo`/`demo`) genera el reporte **Allure 3** (`npx allure@3.21.0`, sin Java; config `allurerc.mjs`; hooks en `tests/api/conftest.py`: epic = módulo, story = HU, `@DEF` → issue + severidad leída de `docs/defectos.md`, petición/respuesta HTTP adjunta por paso) en `reportes/allure/index.html`. `schemathesis` guarda logs VCR+HAR y abre `reportes/dashboard-contrato.html`, generado por `tests/dashboard/dashboard.py` + `plantilla.html` (`demo.py dashboard` lo regenera). Su pestaña de comparativa valida contra el OpenAPI (`jsonschema_rs`) la petición del paso When de cada escenario BDD (sale de los adjuntos de Allure, que marcan "con/sin token") y lo clasifica como contrato (candidato a redundante), regla de negocio, éxito en valor elegido o contenido. Corrida del 2026-10-19: 3432 casos, 0 fallos; 274 escenarios = 44 contrato, 59 regla, 63 éxito, 108 contenido (2026-11-06, tras reforzar con el paso «no se persiste ningún cambio si la operación fue rechazada»: 12 contrato, 50 regla, 36 éxito, 176 contenido; los 12 que quedan son lecturas sin estado y los 5 de «requiere sesión»); `test_contrato.py` y el CLI usan los mismos checks y exclusiones. El paso 3 sale con rc=1 a propósito (los defectos fallan a la vista): avisarlo al presentar.
- **`demo.py final`** (demo de las 3 partes para el deck final; `final ensayo` sin pausas y con tiempos): k6 `correr.py carga` (USUARIOS=120, DURACION=1m, ETIQUETA=demo-final → `tests/performance/resultados/carga-*-docker-demo-final/`, log en `reportes/k6-final.log`) en segundo plano contra `qolqe-rend` (:8001; lo inicia si está detenido) → API HU-G3-01 + DEF-07 (rc=1 a propósito) → `schemathesis g3` (SIN_CONTRATO=1 lo omite) → wdio CP-W12 + HU-G3-01 (HEADED=1 por defecto; Qolqe en :8000 temporal si no hay uno) → espera k6 (umbrales + INTEGRIDAD OK) → Allure + Pages.
- **Corrida `schemathesis g3`** (2026-10-17): 9/69 operaciones (movimientos y categorías), 1212 casos, todos pasan; aviso de Schemathesis: `GET /api/movimientos` y `POST /api/categorias` validan más de lo que documenta el OpenAPI (mismo tipo que "contrato impreciso", no es defecto).
- **Comparativa Schemathesis vs features** (entrega final, pedida por la profesora): `docs/comparativa-schemathesis.md`, corrida del 2026-11-20 con `python demo.py schemathesis todos` (la misma del dashboard): 2 321 casos, 50 hallazgos (28 contrato impreciso, 4 datos inválidos aceptados, 17 `Allow`, 1 recurso tras crear), 0 5xx. En Núcleo + G3 los 8 de contrato impreciso ya los cubre un escenario nuestro. Decisión del equipo (opción B): el `cci` inválido es DEF-17 (Baja) y `hasta=0` queda como observación (§4.2 del doc). Aportes nuevos: `cci` basura con tipo `QOLQE` ejecuta la transferencia y `hasta=0` da 200 con 1970 (observaciones; si el equipo decide que son defectos serían DEF-17+).
- **Dashboard de contrato, pestañas** (`tests/dashboard/`): Schemathesis (agregados del VCR/HAR), Comparativa con pytest-bdd (Allure), **Hallazgos** (checks fallidos agrupados por operación y check, con petición/respuesta/curl y escenarios BDD que dan la misma respuesta) y **Todos los casos** (tabla paginada de 100 con filtros y CSV; cuerpo y respuesta recortados a 240 caracteres). Los datos son de Schemathesis (VCR/HAR); la clasificación y la columna «¿BDD lo prueba?» son heurísticas del script. Para llenar Hallazgos hay que correr `demo.py schemathesis todos`; con los 5 checks del gate sale vacía.
- **Corrida del CLI con todos los checks**: 44 hallazgos (23 contrato impreciso, 3 datos inválidos aceptados, 17 `Allow` ruido, 1 recurso tras crear), ninguno 5xx; clasificados en `docs/informe.md` §2. No se registran como defectos nuevos (solo es defecto lo que incumple la documentación o da 5xx).
- **Revisión completa con agentes (Opus)**: se corrigieron datos de los slides (prioridad del núcleo, escenario del DEF-07), verdes falsos (cierre de cuenta, HU-N-03 CA2, "eliminar dos veces", notas leídas de vuelta, códigos de error explícitos) y se registró **DEF-13**. Hallazgo descartado: la fila "Página" ya es valor límite en el análisis.

## CI

Sitio de Pages (generado por `.github/scripts/reportes.py sitio`, solo stdlib, CSS/JS en línea, claro/oscuro según el sistema; revisado con impeccable): `index.html` (portada + quality gate), `dashboard.html` (por criterio de la rúbrica: casos web × 3 corridas, tiempos por suite, casos por HU, defectos, tendencia entre runs y cobertura), `trazabilidad.html` (buscador + filtro por estado). La tendencia lee `historial.json` publicado en Pages y le suma el run; si no hay, parte de `.github/historial-inicial.json` (runs #1–#5 reconstruidos de sus artefactos).

`.github/workflows/pruebas.yml` (push a `main`/`parte-1`/`parte-2`/`final`, tags `parte-*`/`final`, PR, manual; solo ubuntu, cache pip/npm):
- `contrato` (primero; gate = rc del CLI): `demo.py schemathesis` → artefacto `contrato` (`reporte-schemathesis/`: `html/`, VCR, HAR, JUnit). Con `CI` puesto no arma el dashboard.
- `api` (needs contrato): `pytest -rx` (humo + BDD; `@DEF` = xfail strict) → `reportes/junit-api.xml`, Allure, cobertura; baja el artefacto `contrato` y corre `demo.py dashboard` → `reportes/dashboard-contrato.html`.
- `web` (needs contrato, en paralelo con api): Qolqe en :8000, `npm test` × 3 (cada JUnit se aparta a `tests/e2e/reportes/junit-corrida-N/`), `npm run test:ia` desde la caché sin clave (`ANTHROPIC_API_KEY=""`), DEF-14 invertido (falla esperada; si pasa, el job falla) con sus resultados Allure apartados.
- `reportes` (needs contrato+api+web): `.github/scripts/reportes.py sitio` → `docs/trazabilidad.md` + `sitio/` (portada, `trazabilidad.html`, `api/`, `web/`, `schemathesis/`, `contrato/`); al final `reportes.py gate` (2.3): G1 contrato 0 fallos (DEF-15 = defecto conocido) · G2 API sin fallas inesperadas ni XPASS (`@DEF-nn` = xfail estricto) · G3 cobertura ≥ 60 % (meta 75 %) · G4 web 3/3 corridas, `@ia` pasa y DEF-14 falla · G5 toda HU del alcance (Núcleo + G3) con caso ejecutado · G6 pruebas ≤ 10 min; umbrales en `UMBRAL`, un JUnit ausente = ❌. `publicar`: `deploy-pages` en push a `parte-2`/`main`/`final` o manual, también si el gate falló (reportes en failure) → https://maykol-morales.github.io/cs5383-qolqe-wallet/
- Mapeo: cada prueba BDD de la API lleva la propiedad JUnit `escenario` (hook en `tests/api/conftest.py`); los casos web por el `CP Wnn` del nombre (el reporter quita la puntuación). IDs API: `CP-A-<feature>-nn` por orden en el `.feature`. El script avisa (`::warning::`) de escenarios sin ejecución.
- Local: `pytest -rx --junitxml=reportes/junit-api.xml && python .github/scripts/reportes.py sitio` (regenera la matriz; `resumen TITULO xml...` = tabla del step summary).
- El `ci.yml` anterior (Windows + Linux, borrado el 2026-10-26 por lento) está en el commit `a9cd175`.

## Pendiente / notas

- Entorno local de pruebas: `python demo.py preparar` crea `.venv` e instala `requirements-dev.txt` (ya ignorado por git; ya creado en la máquina de Maykol).
- Herramienta de API (**provisional**: pytest+httpx+pytest-bdd; la asignada en el sorteo está vacía). Web: WebdriverIO 10 + Cucumber (§3); rendimiento: k6 (§4).
- Interpretaciones asumidas a confirmar con el docente están en `docs/informe.md` §1 (p. ej. "90 días" = `hasta − desde ≤ 90`). Además: el código de error de nombres inválidos difiere por endpoint (`SOLICITUD_INVALIDA` al registrarse, `PERFIL_INVALIDO` al editar el perfil) y el requisito no lo fija.
- Limitaciones conocidas de las pruebas: el escenario sin `@DEF` de HU-N-03 CA2 pasa sin probar nada mientras exista DEF-05 (logout no invalida nada); los `.feature` usan `# language: en` con texto en español; el escenario `@concurrencia` no tiene pasos (Parte 3).
- `IA.md`: el equipo lo editó a mano (quitó dos filas de la declaración); no reponer sin preguntar.
- Ramas: `parte-1` (rama por defecto en GitHub; `main` ya se borró) tiene la Parte 1 + reportes; `parte-2` sale de ella para las pruebas web E2E. `ejemplo-webdriverio` (Sebastián) fue el primer ejemplo; lo reemplaza `tests/e2e/`, migrado del repo `git@github.com:Maykol-Morales/cs5383-webdriverio.git` (historia independiente, remoto local `wdio`).
- Parte 2 · notas de WebdriverIO: `browser.act()` (`@ia`) tiene su caché commiteada en `tests/e2e/features/__act__/`, así que `npm run test:ia` la repite sin clave (0 tokens, ~12 s); grabar de nuevo (`npm run test:ia:regrabar`, ~140k tokens, ~45 s) usa la clave de `tests/e2e/.env` (ignorado; Maykol tiene una). Sonnet 5 exige `temperature: 1` (fijado en `wdio.conf.js`). `npm run demo` con clave graba en vivo, muestra la caché y repite; sin clave solo repite. DEF-14 (`features/historial-zona-horaria.feature`) va aparte: `npm run test:defectos` debe fallar mientras exista. El deck del laboratorio WebdriverIO (LSnrwob…) se borró el 2026-10-30; lo reemplaza el deck por rúbrica (abajo). La caché de `act` se indexa por el título del escenario: renombrarlo la invalida y obliga a regrabar. Comparativa act vs agente Claude en `docs/comparativa-ia.md` (2026-10-30). **Deck de la exposición de la Parte 2** (17 slides, ordenado por la rúbrica del slide 36: C1 web 5 · C2 patrón 2 · C3 pipeline 5 · C4 trazabilidad 4 · C5 demo 4; quipu = criterios, nudos = puntos): https://claude.ai/artifact/2XaeAeRaotLkVMBYRKECns. Las versiones de 5 y 15 min se borraron. Fuente y script de armado en el scratchpad de la sesión (no versionados); oradores en las notas: [Maykol] C1–C2, [Sebastian] C3–C4 (supuesto). las esperas sobre la UI se resolvieron recargando la página y esperando el PUT con `browser.mock` (condiciones de carrera vistas en la CI de Windows). `wdio.conf.js` fija la zona horaria del navegador en `America/Lima` (BiDi): la UI arma desde/hasta con la hora del navegador y el servidor rechaza `hasta` futuro en hora de Lima, así que en un runner UTC de noche el historial salía vacío.
- Stash pendiente `stash@{0}` (pytest-html + vcr/har en el viejo `demo.sh`): obsoleto, reemplazado por Allure y el dashboard; se puede descartar.
- Flujo de commits: se commitea y se hace push solo cuando el usuario lo pide; los mensajes terminan con `Co-Authored-By: Claude`.
- `docs/informe.md`: §1–§6 completos (§6 = estado de calidad, riesgos, lecciones y recomendaciones; cifras del 2026-11-20). §6.1: no apto para producción, 16 defectos abiertos (3 Crítica, 7 Alta, 4 Media, 2 Baja).
- **Cobertura con módulos ajenos** (2026-11-20): `features/otros_*.feature` (73 escenarios / 120 pruebas, epic Allure «Otros módulos (fuera de alcance)» vía `tests/api/conftest.py`). Para que no ensucien reportes: `qase.py` solo sube casos cuya HU calce `reportes.ALCANCE` (Núcleo + G3); `dashboard.py` mapea el epic a módulo «Otros»; `reportes.py` (comparativa) los agrupa como «Otros módulos (fuera de alcance)»; el gate G5 ya usaba `ALCANCE`. La matriz de trazabilidad **sí** muestra filas HU-G1/G2/G4–G6 (filtrar en `tablas()` si se quiere).
- **15 hallazgos en otros módulos** (`docs/hallazgos-otros-modulos.md`): bono con `>` en S/ 30, 6.ª recarga aceptada, reanudar programada sin límite, mora +1 día (3 filas), suministro de 13 dígitos, débito automático paga deudas en cobranza, alias con ñ rechazado, alias duplicado con espacios, aceptar solicitud vencida, reducción de límite no cancela aumento, alerta de recargas varias veces al día, PIN revisa 2 anteriores en vez de 3, cambio de PIN no cierra otras sesiones. Quitados de la suite y **no** registrados como DEF (fuera de alcance); registrarlos como DEF-17+ queda a decisión del equipo.
- CI: actions subidas a `upload-artifact@v7`, `download-artifact@v8`, `deploy-pages@v5`, `upload-pages-artifact@v5` (aviso de Node 20); primera corrida con ellas = run 44796177354 de `b74e6b0`.
- `demo.py final` ensayado el 2026-11-20: rc=0, 3 min 36 s (API HU-G3-01 29 s: 41 passed + 4 xfailed; DEF-07 5 s con rc=1 a propósito; schemathesis g3 58 s, 1216 casos; web CP-W12 + HU-G3-01 15 s; k6 103 s, 6/6 umbrales, INTEGRIDAD OK 104/104). Las carpetas de ensayo `tests/performance/resultados/carga-20261120-0{455,505}-docker-demo-final/` no se versionan (borrables).
- **Falta (al 2026-11-20)**:
  1. Confirmar CI verde del run 44796177354 (actions nuevas + 120 pruebas nuevas; Qase solo con el alcance).
  2. Re-correr la Parte 3 en EC2 con `correr.py` y confirmar DEF-16 allá (necesita la IP del Learner Lab).
  3. Rotar el token de Qase (acción de Maykol).
  4. Decidir si se mueve el tag `parte-3` (hoy no apunta al último commit de la rama; push de la rama con `refs/heads/parte-3` porque el tag tiene el mismo nombre).
  5. Compartir desde Share el deck final y el de la Parte 3.
  6. Ensayar `python demo.py final` con Chrome visible antes de exponer (Chrome y la imagen Docker en caché).
  7. Opcionales: filtrar HU ajenas de la matriz; DEF-17+ para los 15 hallazgos; corregir «EC2» en el slide de demo del deck de la Parte 3; borrar las carpetas de ensayo de k6.
- Commits por tarea repartidos entre Maykol (usuario git por defecto) y Sebastián (`GIT_AUTHOR_NAME/GIT_COMMITTER_NAME='Sebastián Urbina'`, email `129198429+Urbisin@users.noreply.github.com`); `gh` necesita `-R Maykol-Morales/cs5383-qolqe-wallet`.
