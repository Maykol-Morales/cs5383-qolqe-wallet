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

## Demo en vivo (exposición, ~5 min)

Hora punta acortada: 2 min de rampa + 1 min estable, solo los 120 usuarios que necesita (`maxVUs`), así `preparar` tarda segundos. Ensayo del 2026-11-11: **3 min 32 s** de principio a fin, todos los umbrales en verde, integridad 122 / 122 (`resultados/carga-20261111-2242-demo/`).

**Antes de la exposición** (en la transición entre grupos):
1. Cerrar el resto de aplicaciones; abrir dos terminales en la raíz del repo y, en el navegador, `resultados/pico-20261111-2032-docker/dashboard.html` (plan B).
2. Levantar Qolqe y comprobar que responde:
   ```bash
   docker start qolqe-rend && curl -s -o /dev/null -w "%{http_code}\n" localhost:8001/docs   # 200
   ```
3. Dejar las variables cargadas en la terminal 1:
   ```bash
   export QOLQE_PID=$(docker inspect -f '{{.State.Pid}}' qolqe-rend) QOLQE_URL=http://localhost:8001 \
          QOLQE_BD=$PWD/datos/rendimiento/qolqe.db PATH=$HOME/.local/bin:$PATH
   ```

**Guion:**

| Min | Pantalla | Qué se hace | Qué se dice |
|---|---|---|---|
| 0:00 | Terminal 2 | `docker stats qolqe-rend` | "Qolqe en un contenedor de 1 núcleo y 1 GB: es nuestro servidor" |
| 0:15 | Terminal 1 | `USUARIOS=120 DURACION=1m ETIQUETA=demo K6_WEB_DASHBOARD_OPEN=true tests/performance/correr.sh carga` | "Prepara 120 usuarios, uno por VU, y arranca la hora punta: 50 sesiones por minuto" |
| 0:30 | Dashboard de k6 (se abre solo en :5665) | Mostrar VUs subiendo, req/s y p95 | "Modelo abierto: llegan 50 sesiones por minuto pase lo que pase; si Qolqe se atrasa, se ve aquí" |
| 1:30 | Terminal 2 | CPU del contenedor | "El CPU que ven es el de Qolqe; k6 casi no consume" |
| 2:00 | `qolqe.js` en el editor | Umbrales y pesos | "Cada umbral es una frase del requerimiento" |
| 3:00 | Terminal 1 | Esperar el cierre (hasta 30 s de `gracefulStop` para las sesiones en curso) | "Las sesiones que quedan a medias por el corte de k6 no cuentan; las operaciones de dinero sí se verifican" |
| 3:50 | Terminal 1 | Al terminar, la terminal muestra el resumen de k6 (subir hasta `THRESHOLDS`) y al final `INTEGRIDAD OK` | "Todos los umbrales en verde y cada operación de dinero confirmada está una sola vez en la BD" |
| 4:10 | `recursos.png` y `k6.png` de la carpeta que imprime al final | Gráficos | "Esto mismo, en 15 minutos y con 300 usuarios, son los resultados que vienen" |

**Plan B** (si el contenedor o k6 fallan): el `dashboard.html` exportado del pico, que ya está abierto, y `resultados/carga-20261111-0422-docker/`.

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
