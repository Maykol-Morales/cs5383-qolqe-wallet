# Sesión 2026-11-10 · Parte 3 (rendimiento): planificación e inicio de la implementación

Trabajo hecho con Claude Code (Opus 5.5) para Maykol. Nada commiteado todavía.

## 1. Lectura del enunciado y del SUT

- Se leyeron `pdfs/P2_Parte3_Enunciado.pdf` (requerimiento "Quincena Qolqe", recomendaciones, entregables, rúbrica de 20 pts) y `pdfs/Template_Informe_Rendimiento.docx` (8 secciones del informe).
- Se revisó en `qolqe/` (sin modificarlo):
  - los endpoints de cada operación del requerimiento;
  - la semilla: usuarios de carga 900000001–900000200, PIN 2580, S/ 10 000 y unos 1 000 movimientos cada uno;
  - las reglas que pueden dar 422 bajo carga: límite diario, máx. 5 recargas al día por número, 15 contactos, bloqueo tras 3 PIN fallidos;
  - el hash del PIN (PBKDF2 de 200 000 iteraciones), SQLite en WAL y el sleep antifraude de 40–120 ms.

## 2. Decisiones del equipo

| Tema | Decisión |
|---|---|
| Herramienta | **k6** (umbrales nativos, poco CPU en el generador, dashboard HTML) |
| Entorno | **AWS EC2**, en espera de que aprueben las cuentas. Se presenta como "dos equipos"; plan B: Docker `--cpus=1 --memory=1g` |
| Rama | **`parte-3`**, creada desde `origin/parte-2` (las correcciones de `final` todavía no se revisan) |
| Revisión | Un agente revisor del plan y un code-reviewer con la skill ponytail-review contra la sobreingeniería |

## 3. Plan (`docs/plan-rendimiento.md`)

**Modelo**
- Ley de Little: 3 000 sesiones/h × 2 min = **100 usuarios simultáneos**; campaña = triple = **300**.
- Cinco pruebas, todas con pausas triangular(10, 19, 25) de media 18 s y la mezcla 30/15/15/10/10/6/4/10 del requerimiento:

| Prueba | Configuración |
|---|---|
| Humo | 1 VU |
| Carga | 50 sesiones/min, modelo abierto, `maxVUs` 120 |
| Pico | 300 VUs, rampa de 5 min, 15 min en total |
| Estrés | 300 → 1 000 VUs, +100 por escalón |
| Resistencia | La carga durante 60 min; el requerimiento pide 18 h y se justifica el recorte |

**Umbrales**
- p95 < 800 ms en consultas y login; p95 < 1.5 s en operaciones de dinero.
- Fallas técnicas (5xx o red) < 1 %. Los errores de negocio (4xx) se cuentan aparte y deben ser 0.
- `dropped_iterations` = 0, que es como se mide "sin acumular retrasos".
- Integridad: ninguna operación de dinero a medias ni duplicada.

**Supuestos declarados**
- "Degradación razonable" en el pico = hasta 2× el umbral y menos de 5 % de fallas.
- Hay 6 pausas por sesión.
- Se usa el historial por defecto (30 días).
- La sesión termina sin logout.

**Revisión del agente** (21 hallazgos; se verificaron en el código antes de aplicarlos)
- Hipótesis principal nueva de cuello de botella: `GET /api/movimientos` hace una subconsulta SUM por cada fila (`qolqe/api/movimientos.py:117`), unas 250 por petición.
- Integridad por id propio de cada petición de dinero (`descripcion`, celular de la recarga, `deuda_id`) en vez de contar 201 o buscar códigos duplicados. Las transferencias comparten código entre envío y recepción, y existe DEF-12.
- EC2 no es una de las cuatro opciones del enunciado, de ahí el plan B con Docker; usar instancias de CPU fija, no t2/t3/t4g.
- Se corrigieron las hipótesis: PBKDF2 libera el GIL y SQLite está en WAL.
- Los usuarios extra se copian con `limites` (sin esa fila las operaciones dan 500) y con su historial.
- Los 4xx se separan de `http_req_failed`. El estrés tiene tope y regla de parada.

**Cuatro mejoras aprobadas**
1. Evidencia obligatoria del cuello de botella: flamegraph con `py-spy` y un estrés de confirmación sin historial (`PESOS=30,0,15,10,10,6,4,10`).
2. Predicción de la capacidad con la ley de utilización (U = X · S), partiendo de los tiempos del humo.
3. Demo en vivo en la laptop. Los resultados de EC2 van en el informe y sirven de plan B grabado.
4. Capacidad informada también en sesiones/h y como múltiplo de la hora punta.

## 4. Implementación (`tests/performance/`)

| Archivo | Qué hace |
|---|---|
| `qolqe.js` | Script k6 único: `PRUEBA=humo\|carga\|pico\|estres`; variables `DURACION`, `PESOS`, `TOPE`, `PASO`, `USUARIOS`; umbrales según la prueba; `responseCallback` para separar los 4xx; contador `errores_negocio` por `codigo`; tag `ref` en cada operación de dinero |
| `datos.py` | `preparar`: `reiniciar`, más usuarios 201–1 000 copiados por SQL, 5 contactos y 30 deudas ELECTRO por usuario, y una foto de saldos y `MAX(id)`. `verificar`: saldo vs movimientos, operaciones vs movimientos, deudas pagadas una vez, cruce 1:1 con las refs de k6 |
| `monitor.py` | El script psutil del enunciado, con PID y salida como argumentos |
| `graficos.py` | `por-minuto.csv` (sirve para los escalones del estrés), `por-endpoint.csv`, `k6.png` y `recursos.png` |
| `correr.sh` | Orquesta una corrida local: preparar → monitores de Qolqe y de k6 → k6 (json, summary, dashboard) → verificar → gráficos. Detecta el PID de Qolqe por el puerto; `PERFIL=1` agrega py-spy |
| `README.md` | Cómo correr cada prueba, en un equipo o en dos (EC2) |

Herramientas instaladas: k6 1.3.0 en `~/.local/bin`; psutil, matplotlib y py-spy en `.venv`.

## 5. Ejecuciones en local

- **Preparar** 1 000 usuarios tarda unos 30 s.
- **Humo** (1 VU, 3 sesiones, 5 min 18 s):
  - todos los umbrales en verde: p95 de consultas 238 ms (el login es lo más lento, 259 ms), p95 de dinero 9 ms;
  - 0 errores de negocio;
  - **integridad OK**: 4 operaciones de dinero cruzadas una a una;
  - se descartó: el monitor había tomado un proceso shell en vez de uvicorn (corregido con `lsof` sobre el puerto).
- **Carga de calibración** (`DURACION=3m`): en curso al cerrar este resumen; queda en `tests/performance/resultados/carga-20261110-2011-calibracion/`.

## 6. Pendiente

1. Revisar la calibración y ajustar si hace falta.
2. Code-reviewer con ponytail-review sobre `tests/performance/`.
3. F2: corridas en EC2 (o Docker): humo, carga, pico, estrés con flamegraph, estrés sin historial y resistencia.
4. F3: análisis y `docs/informe.md` §4 con la estructura de la plantilla; defectos nuevos si aparecen (DEF-15…).
5. F4: comparación k6 vs JMeter, Locust, Gatling y Artillery; deck de 15 min; guion de la demo.
6. Decidir si `pdfs/` y `resultados/` se versionan, commitear cuando se pida y poner el tag `parte-3` antes del viernes de la semana 14.

Notas: en el puerto 8010 hay un uvicorn que no es de esta sesión (no se tocó). El contexto quedó también en la memoria del proyecto (`parte-3-rendimiento.md`).
