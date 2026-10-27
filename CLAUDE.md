# CLAUDE.md

## Qué es este repo

Proyecto 2 del curso **CS5383 Pruebas y Verificación de Software** (UTEC). Contiene **Qolqe Wallet**, una billetera digital ficticia (FastAPI + SQLite, UI en HTML estático) que es el **sistema bajo prueba (SUT)**, y el trabajo de pruebas del **Grupo 3 (G3 · Historial y categorías)** — integrantes Sebastian y Maykol.

**Regla principal: NO modificar `qolqe/`.** El trabajo es probarlo, no repararlo. Todo cambio va en `features/`, `tests/`, `docs/`, `.github/`, `IA.md`.

## Estado por partes

| Parte | Contenido | Estado |
|---|---|---|
| 1 | Pruebas de API (núcleo + G3), contrato con Schemathesis, 12 defectos, análisis EP/VL mapeado a escenarios | Hecha |
| CI | GitHub Actions: pytest + cobertura + junit + reporte Allure | Hecha |
| Reportes | Allure 3 (`demo.py reporte`) y dashboard de Schemathesis + comparativa con BDD (`demo.py schemathesis` / `dashboard`) | Hecha |
| Presentación | Deck final de 13 slides, mapa visual y guion `demo.py` | Hecha (ver "Presentación y demo") |
| 2 | Pruebas web E2E: WebdriverIO 10 + Cucumber + Page Objects + Allure en `tests/e2e/` (migrado del repo `cs5383-webdriverio`) | Happy path G3 hecho; falta ampliar escenarios e informe §3 |
| 3 | Rendimiento (`tests/performance/`) | Pendiente (solo `.gitkeep`) |

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
features/              escenarios Gherkin: nucleo_{registro,sesion,cuenta,transferencias}, historial, categorias
tests/
  api/conftest.py      fixtures (http, Contexto) y pasos comunes
  api/test_{nucleo,historial,contrato}.py   pasos pytest-bdd + contrato Schemathesis
  test_humo.py         prueba de humo
  e2e/                 Parte 2, proyecto Node propio: features/, steps/, pages/ (Page Objects), wdio.conf.js,
                       allurerc.mjs, demo.mjs; npm se corre dentro de tests/e2e/ (README propio)
docs/                  requisitos.md (HU, CA, RN), informe.md, defectos.md, plantilla-informe.md,
                       casos-equivalencia-limites.md (análisis EP/VL), formato-particiones.md (formatos A1/B1)
demo.py                guion de la demo, multiplataforma (preparar, ensayo, demo, schemathesis, plan-b)
demo.sh                atajo Linux/macOS → demo.py
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
QOLQE_URL=http://localhost:8000 pytest tests/api/test_nucleo.py   # contra servidor real
pytest --cov=qolqe                     # cobertura (64 %)
python demo.py preparar | ensayo | demo | schemathesis [g3] [todos] | plan-b   # Windows: py demo.py …; ver "Presentación y demo"
cd tests/e2e && npm install && npm run demo   # Parte 2: levanta Qolqe desde la raíz, flujo, mutación, Allure
npm test                               # (en tests/e2e, con Qolqe en :8000) escenarios web; HEADED=1 muestra Chrome
```

Resultado de referencia (Parte 1, 2026-10-17): `252 passed, 1 skipped, 24 xfailed` + 60 subpruebas de contrato, 141 escenarios Gherkin (G3 70, núcleo 71), 12 defectos abiertos, unos 70 s. El skip es el escenario `@concurrencia` (pertenece a la Parte 3).

## Convenciones de las pruebas

- **Fuente de verdad = `.feature`**; `pytest-bdd` los enlaza con pasos Python. Etiquetas: `@HU-…` (historia), `@DEF-nn` (defecto conocido), `@concurrencia`.
- **Defectos conocidos**: los escenarios `@DEF-nn` son `xfail(strict)`. Si un defecto se corrige pasa a XPASS y el CI falla — es intencional.
- **Aislamiento**: cada escenario reinicia datos con `POST /api/pruebas/reiniciar` (propiedad *Independent* de FIRST). Por defecto la app corre in-process (TestClient) con BD temporal; con `QOLQE_URL` va contra un servidor real.
- **Contrato**: `test_contrato.py` levanta uvicorn en subproceso y corre Schemathesis (15 ejemplos/operación; `CONTRATO_EJEMPLOS` lo cambia; CI usa modo determinista `derandomize`).
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

## Defectos hallados (12 abiertos; detalle en `docs/defectos.md`)

DEF-01 redondeo comisión · 02 PIN descendente aceptado · 03 login exitoso no reinicia intentos · 04 interbancaria deja saldo negativo (Crítica) · 05 logout no invalida token (Crítica) · 06 transferencia a cuenta cerrada pierde dinero (Crítica) · 07 historial excluye el día `hasta` · 08 detalle de movimiento ajeno visible · 09 destinatario ve movimiento del emisor · 10 categoría editable con nombre duplicado · 11 (descartado: el token vence a los 30 min exactos, se acepta) · 12 dos operaciones del mismo segundo comparten código de operación · 13 el límite diario no cuenta las interbancarias

## Presentación y demo

- **Estructura pedida por el docente**: 1) herramienta de automatización y justificación (1-2 slides), 2) módulo asignado, importancia y prioridad (1-2 slides), 3) diseño de casos funcionales y técnicos sobre una HU elegida, 4) demo en vivo (solo indicar que viene). El equipo eligió **HU-N-07** (núcleo, transferencias) y **HU-G3-01** (historial).
- **Artifacts** (privados; Maykol los comparte desde Share): presentación https://claude.ai/artifact/Y36yMfSCkNB16EiFANs8xK (13 slides: portada, herramienta, módulo, 4 de HU-N-07, 4 de HU-G3-01, técnicos, demo) y mapa visual https://claude.ai/artifact/KASkEjLiBq5AsLbhrKifQq. Se mantienen con las fuentes en el scratchpad de la sesión (no versionadas): hay que actualizar cifras en ambos cuando cambie el repo.
- Diseño de la presentación: fondo verde bosque / crema / dorado, Fraunces + DM Sans + JetBrains Mono; en el slide 2 se quitó Schemathesis a propósito (queda en el slide de técnicos como "Contrato OpenAPI").
- **demo.py** (solo stdlib; corre en Windows sin Bash ni curl; `demo.sh` solo lo invoca; documentado en README §7): `preparar` crea `.venv`; `ensayo` corre los 4 pasos (HU-G3-01, todo, DEF-07 con `MOSTRAR_DEFECTOS=1`, contrato) y mide tiempo; `demo` pausa con Enter; `schemathesis [g3] [todos]` levanta un servidor temporal, corre el CLI con `--seed 1` y abre el HTML en `reporte-schemathesis/` (ignorado por git); `plan-b` guarda la salida en `reportes/ensayo.txt`; `SIN_CONTRATO=1` omite el paso 4; `reporte` (y el final de `ensayo`/`demo`) genera el reporte **Allure 3** (`npx allure@3.21.0`, sin Java; config `allurerc.mjs`; hooks en `tests/api/conftest.py`: epic = módulo, story = HU, `@DEF` → issue + severidad leída de `docs/defectos.md`, petición/respuesta HTTP adjunta por paso) en `reportes/allure/index.html`. `schemathesis` guarda logs VCR+HAR y abre `reportes/dashboard-contrato.html`, generado por `tests/dashboard/dashboard.py` + `plantilla.html` (`demo.py dashboard` lo regenera). Su pestaña de comparativa valida contra el OpenAPI (`jsonschema_rs`) la petición del paso When de cada escenario BDD (sale de los adjuntos de Allure, que marcan "con/sin token") y lo clasifica como contrato (candidato a redundante), regla de negocio, éxito en valor elegido o contenido. Corrida del 2026-10-19: 3432 casos, 0 fallos; 274 escenarios = 44 contrato, 59 regla, 63 éxito, 108 contenido; `test_contrato.py` y el CLI usan los mismos checks y exclusiones. El paso 3 sale con rc=1 a propósito (los defectos fallan a la vista): avisarlo al presentar.
- **Corrida `schemathesis g3`** (2026-10-17): 9/69 operaciones (movimientos y categorías), 1212 casos, todos pasan; aviso de Schemathesis: `GET /api/movimientos` y `POST /api/categorias` validan más de lo que documenta el OpenAPI (mismo tipo que "contrato impreciso", no es defecto).
- **Corrida del CLI con todos los checks**: 44 hallazgos (23 contrato impreciso, 3 datos inválidos aceptados, 17 `Allow` ruido, 1 recurso tras crear), ninguno 5xx; clasificados en `docs/informe.md` §2. No se registran como defectos nuevos (solo es defecto lo que incumple la documentación o da 5xx).
- **Revisión completa con agentes (Opus)**: se corrigieron datos de los slides (prioridad del núcleo, escenario del DEF-07), verdes falsos (cierre de cuenta, HU-N-03 CA2, "eliminar dos veces", notas leídas de vuelta, códigos de error explícitos) y se registró **DEF-13**. Hallazgo descartado: la fila "Página" ya es valor límite en el análisis.

## CI

`.github/workflows/ci.yml` tiene dos jobs: `pruebas-api` y `pruebas-web` (Parte 2, matriz Windows + Linux; en Windows también ensaya `npm run demo`). En push a `main`/`parte-*`, tags `parte-*`/`final`, PRs y manual → Python 3.12, `pytest -rx` con junit y cobertura, resumen en el step summary, artefacto `reportes/`.

## Pendiente / notas

- Entorno local de pruebas: `python demo.py preparar` crea `.venv` e instala `requirements-dev.txt` (ya ignorado por git; ya creado en la máquina de Maykol).
- Herramienta de API (**provisional**: pytest+httpx+pytest-bdd; la asignada en el sorteo está vacía). Herramientas web y de rendimiento aún sin definir en `docs/informe.md`.
- Interpretaciones asumidas a confirmar con el docente están en `docs/informe.md` §1 (p. ej. "90 días" = `hasta − desde ≤ 90`). Además: el código de error de nombres inválidos difiere por endpoint (`SOLICITUD_INVALIDA` al registrarse, `PERFIL_INVALIDO` al editar el perfil) y el requisito no lo fija.
- Limitaciones conocidas de las pruebas: el escenario sin `@DEF` de HU-N-03 CA2 pasa sin probar nada mientras exista DEF-05 (logout no invalida nada); los `.feature` usan `# language: en` con texto en español; el escenario `@concurrencia` no tiene pasos (Parte 3).
- `IA.md`: el equipo lo editó a mano (quitó dos filas de la declaración); no reponer sin preguntar.
- Ramas: `parte-1` (rama por defecto en GitHub; `main` ya se borró) tiene la Parte 1 + reportes; `parte-2` sale de ella para las pruebas web E2E. `ejemplo-webdriverio` (Sebastián) fue el primer ejemplo; lo reemplaza `tests/e2e/`, migrado del repo `git@github.com:Maykol-Morales/cs5383-webdriverio.git` (historia independiente, remoto local `wdio`).
- Parte 2 · notas de WebdriverIO: el escenario `@ia` (`browser.act()`) se salta sin `ANTHROPIC_API_KEY` ni caché en `features/__act__/`; las esperas sobre la UI se resolvieron recargando la página y esperando el PUT con `browser.mock` (condiciones de carrera vistas en la CI de Windows).
- Stash pendiente `stash@{0}` (pytest-html + vcr/har en el viejo `demo.sh`): obsoleto, reemplazado por Allure y el dashboard; se puede descartar.
- Flujo de commits: se commitea y se hace push solo cuando el usuario lo pide; los mensajes terminan con `Co-Authored-By: Claude`.
- Secciones 3, 4 y 6 de `docs/informe.md` están vacías hasta las Partes 2/3 y la entrega final.
