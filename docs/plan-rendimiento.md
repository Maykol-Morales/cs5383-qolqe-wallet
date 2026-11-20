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

| Parámetro | Carga (hora punta) | Pico (campaña) | Estrés (capacidad) |
|---|---|---|---|
| Executor k6 | `ramping-arrival-rate` | `ramping-vus` | `ramping-vus` en escalones |
| Carga | 50 sesiones/min (≈ 100 VUs, `maxVUs` 120) | 300 VUs | 300 → 400 → … → tope 1 000 (+50 cerca del quiebre) |
| Ramp-up | 2 min (una sesión) | 5 min: la rampa lineal hace entrar a todos en los primeros 5 min | 1 min por escalón |
| Duración | 15 min estables | 15 min en total (12:00–12:15, rampa incluida) | 3 min por escalón; se miden los últimos 2 |
| Think time | triangular 10–25 s | igual | igual |
| Distribución | 4 flujos: 20 / 40 / 25 / 15 % de las sesiones (ver abajo) | igual | igual |

- La carga usa modelo **abierto** porque el dato es "sesiones por hora", y "sin acumular retrasos" solo se nota si las sesiones siguen llegando aunque el sistema se atrase. Pico y estrés usan **VUs** porque el dato es "usuarios simultáneos".
- El estrés empieza en el pico (300). La capacidad es el último escalón que cumple los umbrales de hora punta. Corta solo con `abortOnFail` si las fallas pasan de 10 %.
- El humo es la carga con 1 VU y 3 sesiones: referencia de latencia y prueba del script. Va en la demo en vivo.
- Cada sesión sigue **uno de 4 flujos completos**, historias de lo que un usuario hace al abrir la app, de 6 operaciones cada una y sorteados con 20 / 40 / 25 / 15 % (variable `FLUJOS`):

| Flujo | % sesiones | Operaciones (después del login) | Por qué es crítico |
|---|---|---|---|
| 1. Chequear mi plata | 20 | saldo+perfil, movimientos, límites o alertas, otra consulta de cuenta, saldo+perfil, movimientos | Frecuencia (consultas) y riesgo: el historial calcula el saldo posterior con una subconsulta por fila |
| 2. Es quincena, pago a los míos | 40 | saldo+perfil, contactos, transferencia, saldo+perfil, transferencia, movimientos | Impacto en el dinero (débito y crédito en dos cuentas); verifica el resultado al terminar |
| 3. Recargo celulares | 25 | saldo+perfil, contactos, recarga, recarga (a un familiar), saldo+perfil, límites o alertas | Dinero y riesgo: la recarga pasa por el antifraude simulado (40–120 ms por hilo) |
| 4. Pago mis servicios | 15 | saldo+perfil, consultar deuda, pagar, consultar deuda, pagar, movimientos | Dinero: se paga siempre la deuda consultada antes; revisa el historial al final |

  Las "otras" (límites, alertas, solicitudes, dispositivos, sesiones) se reparten al azar entre esos 5 endpoints. Los datos de cada operación siguen siendo al azar (monto, contacto, número recargado).
- **Los pesos 20/40/25/15 salen de la tabla del requerimiento.** Una sesión tiene 6 operaciones, así que 100 sesiones son 600 operaciones. Se probaron las combinaciones de porcentajes (en pasos de 5) y de variantes de los flujos, y se eligió la de menor desviación que deja el flujo de consulta con un peso creíble (20 %). La mezcla resultante frente al requerimiento:

| Operación | Requerimiento | Con los 4 flujos | Diferencia |
|---|---|---|---|
| Saldo y perfil | 30 % | 30,8 % | +0,8 |
| Movimientos | 15 % | 15,8 % | +0,8 |
| Transferencia | 15 % | 13,3 % | −1,7 |
| Contactos | 10 % | 10,8 % | +0,8 |
| Recarga | 10 % | 8,3 % | −1,7 |
| Consultar deuda | 6 % | 5,0 % | −1,0 |
| Pagar deuda | 4 % | 5,0 % | +1,0 |
| Otras | 10 % | 10,8 % | +0,8 |

  Con sesiones de longitud fija (6 operaciones, dato del requerimiento) y flujos enteros, la mezcla no puede ser exacta: la mayor desviación es de 1,7 puntos. Las operaciones de dinero suman 26,7 % (requerimiento: 29 %): transferencias, recargas y pagos quedan algo por debajo, en las tres un poco menos de lo pedido.

### 3.1 Tipos de prueba: cuáles se ejecutan y cuál se descarta

El requerimiento pregunta dos cosas: si se cumple en **hora punta y en el pico de la campaña**, y **hasta cuántos usuarios simultáneos** puede crecer la plataforma. Cada tipo de prueba se elige según la pregunta que contesta:

| Tipo | Decisión | Pregunta del requerimiento que contesta |
|---|---|---|
| Carga | **Se ejecuta** | "En hora punta … sostener el volumen de la hora punta sin acumular retrasos" |
| Pico | **Se ejecuta** | "El triple de usuarios simultáneos, la mayoría en los primeros 5 minutos … ninguna operación de dinero a medias ni dos veces" |
| Estrés | **Se ejecuta** | "Hasta cuántos usuarios simultáneos podemos crecer antes de dejar de cumplir" |
| Resistencia (soak) | **Se descarta** | Ninguna (ver abajo) |
| Humo | Se ejecuta (validación) | No es del requerimiento: valida el script y da la latencia sin contención |

**Por qué se descarta la resistencia:**

1. **El requerimiento no la pide.** Lo que "necesitamos saber" es si se cumple en hora punta y en el pico, y el límite de crecimiento. Nada pregunta por la estabilidad durante muchas horas. El dato de que Qolqe "opera de 6:00 a 24:00 sin reinicios" describe el contexto, no un criterio de aceptación: no trae ningún umbral (memoria máxima, degradación permitida) que convertir en prueba.
2. **La prueba real no es ejecutable.** La resistencia que corresponde al dato son 18 h (6:00–24:00). No cabe en el plazo ni en una laptop que además genera la carga. Una versión de 1 h no demuestra nada sobre 18 h: las 18 h acumulan 18 veces más movimientos, sesiones y notificaciones, y una hora no permite extrapolar con confianza.
3. **Lo que vigila una resistencia ya se observa en las otras pruebas.** Su objetivo es ver si crece la memoria o el tiempo de respuesta con el uso. En la carga, el pico y el estrés se registran el CPU y la memoria de Qolqe cada segundo y el p95 por minuto, así que una fuga o una degradación progresiva importante aparecería en esas curvas.
4. **Sería la misma prueba que la carga, más larga.** La hora punta dura 1 h, y la carga ya mide el ritmo de 3 000 sesiones/h con 0 sesiones descartadas; alargarla a 60 min repite la misma carga sin hacer una pregunta nueva.

**Riesgo que queda sin cubrir (se declara en el informe, §6):** la acumulación de datos durante 18 h (crecimiento del historial, de las sesiones y de las notificaciones en SQLite) no se mide. Si el negocio necesita esa garantía, la recomendación es una prueba de resistencia de 18 h en un entorno dedicado, con memoria y tamaño de la base como criterios, que hoy no existen en el requerimiento.

**Referencia previa, no comparable:** en la rama `parte-3` hay una corrida de 60 min a la tasa de hora punta (memoria 122 → 124 MB, sin degradación del p95), hecha con el modelo de carga anterior y otro hardware. No se usa como resultado de esta entrega.

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
  qolqe.js         script k6 único; PRUEBA=humo|carga|pico|estres
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
- el estrés sin historial no se ejecutó: la evidencia apuntó al candado de SQLite y no al historial.

**Capacidad** se informa en usuarios simultáneos y en sesiones/h (= usuarios × 30) frente a la hora punta: "N usuarios ≈ M sesiones/h = K veces la hora punta".

## 8. Fases

| Fase | Contenido | Revisión |
|---|---|---|
| F0 | Este plan | Agente revisor (hecho; correcciones incorporadas) |
| F1 | `qolqe.js`, `datos.py`, `monitor.py`, `graficos.py`; humo y carga corta en local para calibrar | Agente code-reviewer con ponytail-review |
| F2 | Ejecución en EC2 (o Docker): humo, carga, pico, estrés (la resistencia se descarta, §3.1) | – |
| F3 | Análisis + `docs/informe.md` §4 + defectos nuevos si aparecen (DEF-15…) | Agente revisor |
| F4 | Comparación de herramientas (k6 vs JMeter, Locust, Gatling, Artillery), deck de 15 min y guion de demo | – |

**Demo en vivo en la laptop, no en EC2** (5–10 min de transición, red de la universidad): Qolqe local + carga de ~2 min con el dashboard de k6 abierto. Los resultados de EC2 van en el informe y sirven de plan B grabado.

Fuera de alcance: rendimiento en la CI (el enunciado no lo pide) y la capa web (la carga es de API).
