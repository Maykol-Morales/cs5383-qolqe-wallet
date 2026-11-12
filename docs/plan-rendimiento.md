# Plan · Parte 3: pruebas de rendimiento

Rama `parte-3` (sale de `parte-2`). Herramienta **k6**. Entregables: `tests/performance/`, `tests/performance/resultados/`, `docs/informe.md` §4 (estructura de `pdfs/Template_Informe_Rendimiento.docx`), tag `parte-3` antes del viernes de la semana 14.

## 0. Entorno

El enunciado pide elegir una de cuatro opciones; EC2 no figura tal cual.
- **Plan A, AWS EC2 como "dos equipos"**: una instancia corre Qolqe (`--host 0.0.0.0`) y otra corre k6, en la misma VPC (pendiente de aprobación de cuentas). Usar instancias de CPU fija (c/m), no t2/t3/t4g: las de créditos se estrangulan en 1 h de resistencia y mediríamos a AWS, no a Qolqe.
- **Plan B, Docker en la laptop** (`--cpus=1 --memory=1g`), por si las cuentas no llegan antes del tag. Requiere agregar el usuario al grupo `docker`.
- En cualquier caso: humo de 1 VU como referencia de latencia de red. Los scripts reciben la URL por `QOLQE_URL`.

## 1. Flujos críticos

| Flujo | % | Criterio |
|---|---|---|
| Inicio de sesión | 1 por sesión (3 000/h) | Frecuencia: toda sesión pasa por aquí; riesgo: PBKDF2 de 200 000 iteraciones (CPU) |
| Transferir a otro usuario Qolqe | 15 % | Impacto en el dinero (débito + crédito); riesgo de quedar a medias o duplicarse |
| Consultar movimientos | 15 % | Riesgo: el saldo posterior se calcula con una subconsulta por fila (`api/movimientos.py:117-123`) |
| Consultar saldo y perfil | 30 % | La operación más frecuente |
| Recargar / pagar servicio | 10 % / 4 % | Dinero; pasan por el antifraude simulado (sleep de 40–120 ms) |

## 2. Umbrales

| Criterio | Umbral (k6) | Fuente |
|---|---|---|
| Tiempo, consultas + login | `http_req_duration{tipo:consulta}` p(95) < 800 ms | "Consultas e inicio de sesión: el 95 % … 800 ms" |
| Tiempo, dinero | `http_req_duration{tipo:dinero}` p(95) < 1 500 ms | "Operaciones de dinero … 1.5 s" |
| Errores (hora punta) | fallas técnicas (5xx, timeout, red) < 1 % | "no más del 1 % de las operaciones puede fallar" |
| Errores de datos | `errores_negocio` (4xx por regla, contados por `codigo`) = 0 | Enunciado §5: se separan del rendimiento (`responseCallback` para que no cuenten en `http_req_failed`) |
| Throughput | ≥ 50 sesiones/min, ≥ 5 operaciones/s (≈ 7.5 req/s) | 3 000 sesiones/h × 6 operaciones = 18 000/h; ~9 peticiones por sesión |
| Sin acumular retrasos | `dropped_iterations` = 0 con `maxVUs` = 120; `iteration_duration` ≈ 2 min estable | "sostener el volumen … sin acumular retrasos" |
| Integridad (todas) | 0 operaciones a medias o duplicadas | "ninguna operación de dinero puede quedar a medias ni aplicarse dos veces" |

**Lo que no se convierte tal cual → supuesto:**
- "Degradación razonable" en el pico: p95 ≤ 2× el umbral (1.6 s / 3 s) y fallas técnicas < 5 %; integridad sigue en 0.
- "Operación" = operación de negocio para el throughput; el tiempo se mide por petición HTTP (saldo + perfil y consultar + pagar son 2 peticiones).
- Pausa de "10 a 25 s, 18 s en promedio" → triangular(10, 19, 25), cuya media es 18 s. Son 6 pausas por sesión (tras el login y entre operaciones): 6 × 18 = 108 s + respuestas ≈ 2 min. La alternativa de 5 pausas daría 1.5 min y no cuadra.
- Historial sin `desde`/`hasta` (30 días por defecto, como la pantalla de inicio).
- Sin logout al final (el requerimiento no lo menciona).

## 3. Modelo de carga

Ley de Little: usuarios simultáneos = 3 000 sesiones/h × 2 min / 60 min = **100**. Campaña = triple = **300**.

| Parámetro | Carga (hora punta) | Pico (campaña) | Estrés (capacidad) | Resistencia |
|---|---|---|---|---|
| Executor k6 | `ramping-arrival-rate` | `ramping-vus` | `ramping-vus` en escalones | igual a carga, más larga |
| Carga | 50 sesiones/min (≈ 100 VUs, `maxVUs` 120) | 300 VUs | 300 → 400 → … → tope 1 000 (+50 cerca del quiebre) | 50 sesiones/min |
| Ramp-up | 2 min (una sesión) | 5 min: la rampa lineal hace entrar a todos en los primeros 5 min | 1 min por escalón | 2 min |
| Duración | 15 min estables | 15 min en total (12:00–12:15, rampa incluida) | 3 min por escalón; se miden los últimos 2 | 60 min (supuesto) |
| Think time | triangular 10–25 s | igual | igual | igual |
| Distribución | 30/15/15/10/10/6/4/10 | igual | igual | igual |

- La carga usa modelo **abierto** porque el dato es "sesiones por hora", y "sin acumular retrasos" solo se nota si las sesiones siguen llegando aunque el sistema se atrase. Pico y estrés usan **VUs** porque el dato es "usuarios simultáneos".
- El estrés empieza en el pico (300). La capacidad es el último escalón que cumple los umbrales de hora punta. Corta solo con `abortOnFail` si las fallas pasan de 10 %.
- La resistencia es la carga con `DURACION=60m`. El requerimiento pide 18 h (6:00–24:00); se comprime a 1 h por costo y se justifica en el informe. Vigilar la RSS, el p95 del historial (crece `movimientos`) y `notificaciones`.
- El humo es la carga con 1 VU y 3 sesiones: referencia de latencia y prueba del script. Va en la demo en vivo.
- Las 6 operaciones se sortean con pesos: saldo+perfil 30, movimientos 15, transferencia 15, contactos 10, recarga 10, consultar deuda 6, pagar deuda 4, otras (límites, alertas, solicitudes, dispositivos, sesiones) 10.

## 4. Datos de prueba (un usuario por VU)

`tests/performance/datos.py`. Corre en la máquina del servidor (lee y escribe `QOLQE_BD`) **antes de cada corrida**, porque el límite diario es acumulado y `reiniciar` restaura la plantilla.
1. `POST /api/pruebas/reiniciar`, antes de abrir la ventana de medición (la primera del día puede tardar). Semilla: usuarios de carga 900000001–900000200, PIN 2580, S/ 10 000, unos 1 000 movimientos cada uno.
2. Hasta N = 1 000 usuarios (el tope del estrés): copiar por SQL las filas de `usuarios`, `cuentas`, `limites`, `historial_pin` y `movimientos` del usuario de carga `n − 200`. Así todos tienen el mismo volumen de historial. Sin `limites` las operaciones de dinero dan 500.
3. Por usuario: 5 contactos y un suministro propio (`ELECTRO`, 8–12 dígitos) con 30 deudas de S/ 10 que vencen en el futuro. No hay API para crear deudas: van por SQL y se documenta.
4. Cada petición de dinero lleva un id propio: `descripcion` única en la transferencia (por ejemplo `k6-<vu>-<iter>-<n>`), celular destino único en la recarga y `deuda_id` en el pago. El pago primero consulta y toma el `id` de la respuesta.
5. Riesgo de 422 revisado con el código: límite diario lejos (unas 20 transferencias de S/ 1–20 por usuario), recargas a números distintos, PIN siempre correcto, token de 30 min mayor que una sesión de 2 min.

**Integridad** (`datos.py verificar`): antes de la corrida se guardan el `MAX(id)` de cada tabla y los saldos; después, con la BD (no la API, por DEF-07):
- por usuario, `saldo_final − saldo_inicial = Σ importe_cent` de los movimientos nuevos; ningún saldo queda negativo;
- cada transferencia tiene 2 movimientos, y cada recarga y cada pago, 1; una deuda PAGADA tiene exactamente 1 pago;
- cruce 1:1 de los ids que k6 registró con respuesta 2xx contra las filas nuevas; las operaciones que se aplicaron pese a un timeout del cliente se cuentan aparte;
- no se buscan duplicados por `codigo_operacion`: una transferencia comparte código entre envío y recepción, y existe DEF-12.

## 5. Recursos

`tests/performance/monitor.py <PID> <salida.csv>` (el script psutil del enunciado, con argumentos) sobre uvicorn y sobre k6. Si k6 pasa de 80 % de CPU, la corrida no vale. Se anota la hora de inicio y fin de cada prueba. El CPU de Qolqe puede pasar de 100 % porque PBKDF2 libera el GIL.

## 6. Estructura

```
tests/performance/
  README.md        cómo correr cada prueba
  qolqe.js         script k6 único; PRUEBA=humo|carga|pico|estres (+ DURACION para resistencia)
  datos.py         preparar | verificar
  monitor.py       CPU y memoria de un proceso → CSV
  graficos.py      CPU/memoria → PNG y p95/errores por escalón del estrés (lo demás lo da el dashboard HTML de k6)
  resultados/<prueba>-<fecha>/   summary.json, dashboard.html, CSV de k6 y de recursos, PNG, integridad.txt
```

## 7. Cuello de botella: hipótesis a confirmar con evidencia

1. **Historial**: `GET /api/movimientos` ejecuta una subconsulta por fila de la ventana (unas 250 por usuario de carga) más un bucle en Python con el GIL tomado. Es la sospecha principal.
2. **Pool de hilos de AnyIO (40)**: todos los endpoints son síncronos. El sleep antifraude (40–120 ms) y PBKDF2 (~0.15 s) ocupan hilos y forman cola.
3. **Login**: PBKDF2 libera el GIL y escala entre núcleos hasta agotar el pool o los núcleos.
4. **SQLite**: está en WAL y la escritura dura milisegundos; "database is locked" es poco probable (`busy_timeout` 10 s).

**Predicción antes de medir (ley de utilización, U = X · S):** el humo da el tiempo de servicio S de cada endpoint con 1 VU. Con la mezcla del modelo (≈ 9 peticiones por sesión) se estima la demanda por sesión y, con los núcleos disponibles, la tasa de sesiones a la que el servidor se satura. El estrés confirma o desmiente esa cifra y el informe explica la diferencia.

**Evidencia (obligatoria):**
- p95 por endpoint (etiqueta `name` de k6) y CPU del proceso;
- `py-spy record --pid <uvicorn> -o flamegraph.svg` durante el estrés: en qué funciones se va el CPU;
- experimento de confirmación: estrés repetido con `PESOS` sin historial (su 15 % repartido entre las demás operaciones). Si la capacidad sube mucho, el historial es la causa.

**Capacidad** se informa en usuarios simultáneos y en sesiones/h (= usuarios × 30) frente a la hora punta: "N usuarios ≈ M sesiones/h = K veces la hora punta".

## 8. Fases

| Fase | Contenido | Revisión |
|---|---|---|
| F0 | Este plan | Agente revisor (hecho; correcciones incorporadas) |
| F1 | `qolqe.js`, `datos.py`, `monitor.py`, `graficos.py`; humo y carga corta en local para calibrar | Agente code-reviewer con ponytail-review |
| F2 | Ejecución en EC2 (o Docker): humo, carga, pico, estrés, resistencia | – |
| F3 | Análisis + `docs/informe.md` §4 + defectos nuevos si aparecen (DEF-15…) | Agente revisor |
| F4 | Comparación de herramientas (k6 vs JMeter, Locust, Gatling, Artillery), deck de 15 min y guion de demo | – |

**Demo en vivo en la laptop, no en EC2** (5–10 min de transición, red de la universidad): Qolqe local + carga de ~2 min con el dashboard de k6 abierto. Los resultados de EC2 van en el informe y sirven de plan B grabado.

Fuera de alcance: rendimiento en la CI (el enunciado no lo pide) y la capa web (la carga es de API).
