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

## Demo en vivo en EC2 (exposición, ~5 min)

Qolqe y k6 corren en la EC2 (AWS Academy Learner Lab, `c7i.large`, Ubuntu 22.04, 2 vCPU): Qolqe en Docker con `--cpus=1 --memory=1g` fijado al núcleo 1, k6 con `taskset -c 0` en el núcleo 0. Así no compiten por el CPU ni se suma la latencia de red Perú → us-east-1 (~120 ms) al p95. Desde la laptop solo se manejan dos SSH y el navegador. Hora punta acortada: 2 min de rampa + 1 min estable, solo los 120 usuarios que necesita (`maxVUs`). Prueba en la EC2 del 2026-11-12: unos 4 min de principio a fin, p95 consulta 32 ms / dinero 117 ms, 0 fallas, integridad 126 / 126. Ensayo en Docker local del 2026-11-11: 3 min 32 s.

**Antes de la exposición** (10 min antes, fuera del tiempo de la demo):
1. Iniciar el Learner Lab (*Start Lab*, esperar el círculo verde) y anotar la **IP pública** de la instancia, que cambia en cada sesión. La sesión dura unas 4 h.
2. En la laptop, abrir en el navegador el plan B: `resultados/pico-20261112-*-ec2/dashboard.html` (o el de Docker, `resultados/pico-20261111-2032-docker/dashboard.html`).
3. **Terminal 1**, con túnel al dashboard de k6:
   ```bash
   export IP=<IP pública>
   ssh -i ~/.ssh/labsuser.pem -L 5665:localhost:5665 ubuntu@$IP
   ```
   Ya en la EC2:
   ```bash
   cd ~/qolqe && docker start qolqe-rend && sleep 3 && curl -s -o /dev/null -w "%{http_code}\n" localhost:8001/docs   # 200
   export QOLQE_PID=$(docker inspect -f '{{.State.Pid}}' qolqe-rend) QOLQE_URL=http://localhost:8001 \
          QOLQE_BD=$PWD/datos/rendimiento/qolqe.db PATH=$HOME/.local/bin:$PATH
   ```
4. **Terminal 2**: `ssh -i ~/.ssh/labsuser.pem ubuntu@$IP` (para `docker stats`).
5. Si pasaron más de 7 días desde la última corrida, la plantilla de datos venció (`DIAS_VIGENCIA_PLANTILLA`) y el primer `preparar` la reconstruye (tarda más). Para evitarlo, correr el comando del minuto 0:15 una vez antes de entrar, o al menos `.venv/bin/python tests/performance/datos.py preparar /tmp/x 120`.

**Guion:**

| Min | Pantalla | Qué se hace | Qué se dice |
|---|---|---|---|
| 0:00 | Terminal 2 | `docker stats qolqe-rend` | "Esto corre en una EC2 de AWS: Qolqe en un contenedor de 1 núcleo y 1 GB es nuestro servidor; k6 usa el otro núcleo" |
| 0:15 | Terminal 1 | `USUARIOS=120 DURACION=1m ETIQUETA=demo taskset -c 0 tests/performance/correr.sh carga` | "Prepara 120 usuarios, uno por VU, y arranca la hora punta: 50 sesiones por minuto" |
| 0:30 | Navegador, http://localhost:5665 (por el túnel) | Mostrar VUs subiendo, req/s y p95 | "Modelo abierto: llegan 50 sesiones por minuto pase lo que pase; si Qolqe se atrasa, se ve aquí" |
| 1:30 | Terminal 2 | CPU del contenedor | "El CPU que ven es el de Qolqe; k6 está en otro núcleo y casi no consume" |
| 2:00 | `qolqe.js` en el editor de la laptop | Umbrales y pesos | "Cada umbral es una frase del requerimiento" |
| 3:00 | Terminal 1 | Esperar el cierre (hasta 30 s de `gracefulStop` para las sesiones en curso) | "Las sesiones que quedan a medias por el corte de k6 no cuentan; las operaciones de dinero sí se verifican" |
| 3:50 | Terminal 1 | Al terminar, la terminal muestra el resumen de k6 (subir hasta `THRESHOLDS`) y al final `INTEGRIDAD OK` | "Todos los umbrales en verde y cada operación de dinero confirmada está una sola vez en la BD" |
| 4:10 | Terminal 2 (Ctrl+C a `docker stats`) y luego la laptop | `exit`, y en la laptop `scp -r -i ~/.ssh/labsuser.pem ubuntu@$IP:qolqe/<carpeta que imprimió> /tmp/demo && xdg-open /tmp/demo/recursos.png` | "Esto mismo, en 15 minutos y con 300 usuarios, son los resultados que vienen" |

**Plan B:**
- Si falla la red o el lab, mostrar el `dashboard.html` exportado que ya está abierto, y `resultados/carga-20261112-0747-ec2/`.
- Si hay tiempo, la misma demo en Docker local de la laptop: `docker start qolqe-rend` y las variables con `$PWD`, sin `taskset` ni túnel.

## Montaje de la EC2 (una vez)

Desde la laptop, en la raíz del repo (`git archive` sube solo lo versionado):

```bash
S="ssh -i ~/.ssh/labsuser.pem ubuntu@$IP"
git archive --format=tar --prefix=qolqe/ HEAD | $S 'rm -rf qolqe && tar x'
$S 'mkdir -p .local/bin' && scp -i ~/.ssh/labsuser.pem ~/.local/bin/k6 ubuntu@$IP:.local/bin/k6
$S 'cd qolqe && docker build -f tests/performance/Dockerfile -t qolqe-rendimiento . \
    && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt psutil matplotlib && mkdir -p datos/rendimiento \
    && docker run -d --name qolqe-rend --cpus=1 --cpuset-cpus=1 --memory=1g --user $(id -u):$(id -g) -p 8001:8000 \
         -v $PWD/datos/rendimiento:/bd -e QOLQE_BD=/bd/qolqe.db -e QOLQE_BD_PLANTILLA=/bd/plantilla_carga.db qolqe-rendimiento'
```

Las pruebas largas se corren con `nohup` para que no se corten si se cae el SSH (`ETIQUETA=ec2 taskset -c 0 tests/performance/correr.sh <prueba>`), y los resultados se traen con `scp -r ubuntu@$IP:qolqe/tests/performance/resultados/<carpeta> tests/performance/resultados/`.
