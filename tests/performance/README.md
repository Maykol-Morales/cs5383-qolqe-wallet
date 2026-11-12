# Pruebas de rendimiento (Parte 3)

Requerimiento "Quincena Qolqe" (`pdfs/P2_Parte3_Enunciado.pdf`). Modelo, umbrales y supuestos: `docs/plan-rendimiento.md`.

| Archivo | Qué hace |
|---|---|
| `qolqe.js` | Script k6. `PRUEBA=humo\|carga\|pico\|estres` elige el escenario |
| `datos.py` | `preparar` (reinicia y deja un usuario por VU con deudas y contactos) y `verificar` (integridad) |
| `monitor.py` | CPU y memoria de un proceso → CSV (script del enunciado) |
| `graficos.py` | `por-minuto.csv`, `por-endpoint.csv`, `k6.png`, `recursos.png` |
| `correr.sh` | Todo lo anterior en orden, cuando Qolqe y k6 están en el mismo equipo |
| `reproducir_def16.py` | DEF-16: N logins simultáneos contra un Qolqe dedicado; sale con 1 si alguno da 5xx |

## Requisitos

- [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) ≥ 1.0
- `.venv/bin/pip install psutil matplotlib py-spy`
- Qolqe en un solo proceso: `uvicorn qolqe.main:app --host 0.0.0.0 --port 8000`
- Qolqe dedicado: si otras pruebas (E2E, pytest) usan el mismo servidor, sus `reiniciar` borran los usuarios de carga y salen 401. En ese caso, levantar otro puerto y otra BD (`QOLQE_BD=/tmp/rend.db uvicorn … --port 8001`) y correr con las mismas `QOLQE_URL` y `QOLQE_BD`

## Correr (mismo equipo)

```bash
tests/performance/correr.sh humo                      # 1 VU, 3 sesiones (~6 min): referencia y prueba del script
tests/performance/correr.sh carga                     # hora punta: 50 sesiones/min, 2 + 15 min
DURACION=60m ETIQUETA=resistencia tests/performance/correr.sh carga
tests/performance/correr.sh pico                      # 300 VUs, 15 min
PERFIL=1 tests/performance/correr.sh estres           # 300 → 1000 VUs (+100 cada 4 min) con flamegraph
PESOS=30,0,15,10,10,6,4,10 ETIQUETA=sin-historial tests/performance/correr.sh estres   # confirmación: el 15 % del historial se reparte en proporción
```

Cada corrida deja `resultados/<prueba>-<fecha>[-etiqueta]/`:
- de k6: `summary.json`, `dashboard.html` y `k6.json.gz`;
- de los otros scripts: `recursos-*.csv`, `integridad.txt`, las tablas, los PNG y `horario.txt`.

k6 sale con error si se incumple un umbral. `integridad.txt` termina en `INTEGRIDAD OK` o lista los fallos. Durante la corrida, el dashboard en vivo de k6 está en http://localhost:5665.

## Dos equipos (EC2)

En el servidor, desde la raíz del repo:

```bash
.venv/bin/python tests/performance/datos.py preparar resultados/X
.venv/bin/python tests/performance/monitor.py <PID uvicorn> resultados/X/recursos-qolqe.csv
```

En el generador:

```bash
QOLQE_URL=http://<ip>:8000 k6 run -e PRUEBA=carga --out json=k6.json.gz --summary-export=summary.json tests/performance/qolqe.js
```

Al terminar:
1. Copiar `k6.json.gz` al directorio del servidor.
2. En el servidor, `datos.py verificar resultados/X` y `graficos.py resultados/X`.
3. Medir también el CPU de k6 con `monitor.py` en el generador: si pasa de 80 %, la corrida no vale.
