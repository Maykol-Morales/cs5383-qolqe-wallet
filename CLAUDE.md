# CLAUDE.md

## Qué es este repo

Proyecto 2 del curso **CS5383 Pruebas y Verificación de Software** (UTEC). Contiene **Qolqe Wallet**, una billetera digital ficticia (FastAPI + SQLite, UI en HTML estático) que es el **sistema bajo prueba (SUT)**, y el trabajo de pruebas del **Grupo 3 (G3 · Historial y categorías)** — integrantes Sebastian y Maykol.

**Regla principal: NO modificar `qolqe/`.** El trabajo es probarlo, no repararlo. Todo cambio va en `features/`, `tests/`, `docs/`, `.github/`, `IA.md`.

## Estado por partes

| Parte | Contenido | Estado |
|---|---|---|
| 1 | Pruebas de API (núcleo + G3), contrato con Schemathesis, 12 defectos, análisis EP/VL mapeado a escenarios | Hecha |
| CI | GitHub Actions: pytest + cobertura + junit | Hecha |
| 2 | Pruebas web E2E con Page Objects (`tests/e2e/pages/`) | Pendiente (solo `.gitkeep`) |
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
docs/                  requisitos.md (HU, CA, RN), informe.md, defectos.md, plantilla-informe.md,
                       casos-equivalencia-limites.md (análisis EP/VL), formato-particiones.md (formatos A1/B1)
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
pytest --cov=qolqe                     # cobertura
```

Resultado de referencia (Parte 1): `238 passed, 1 skipped, 23 xfailed` + 60 subpruebas de contrato. El skip es el escenario `@concurrencia` (pertenece a la Parte 3).

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
- Decisiones tomadas: monto de transferencia y comisión = EQ; token a 30 min, límite diario y saldo vs monto+comisión = VL; login sin `dispositivo_id` es válido (sin SMS); simulación con tipo inexistente se rechaza y sin tipo = QOLQE; categoría ajena como filtro = `FILTRO_INVALIDO`; página 0 = `FILTRO_INVALIDO`; 0 movimientos = 1 página; nombre de categoría solo con espacios = inválido; orden de validación del cierre: PIN → saldo → solicitudes; solicitud vence a las 48 h (R-G4-05); redondeo validado por el servidor.
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

## Defectos hallados (todos abiertos; detalle en `docs/defectos.md`)

DEF-01 redondeo comisión · 02 PIN descendente aceptado · 03 login exitoso no reinicia intentos · 04 interbancaria deja saldo negativo (Crítica) · 05 logout no invalida token (Crítica) · 06 transferencia a cuenta cerrada pierde dinero (Crítica) · 07 historial excluye el día `hasta` · 08 detalle de movimiento ajeno visible · 09 destinatario ve movimiento del emisor · 10 categoría editable con nombre duplicado · 11 token inválido a los 30 min exactos (por confirmar).

## CI

`.github/workflows/ci.yml`: en push a `main`, tags `parte-*`/`final`, PRs y manual → Python 3.12, `pytest -rx` con junit y cobertura, resumen en el step summary, artefacto `reportes/`.

## Pendiente / notas

- Entorno local de pruebas: no hay `.venv` en el repo; crear uno e instalar `requirements-dev.txt` (usar el del scratchpad de la sesión o `python -m venv .venv`, ya ignorado por git).
- Herramienta de API (**provisional**: pytest+httpx+pytest-bdd; la asignada en el sorteo está vacía). Herramientas web y de rendimiento aún sin definir en `docs/informe.md`.
- Interpretaciones asumidas a confirmar con el docente están en `docs/informe.md` §1 (p. ej. "90 días" = `hasta − desde ≤ 90`).
- Secciones 3, 4 y 6 de `docs/informe.md` están vacías hasta las Partes 2/3 y la entrega final.
