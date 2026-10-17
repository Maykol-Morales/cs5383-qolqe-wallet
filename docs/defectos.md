# Reporte de defectos

Defectos encontrados al ejecutar las pruebas de la Parte 1 contra Qolqe Wallet 1.0.0 (`qolqe/` sin modificar). Cada defecto tiene una prueba en `tests/api/` marcada con su etiqueta `@DEF-nn` en los `.feature`; esas pruebas están como `xfail(strict)` para que el pipeline siga verde mientras el defecto exista. Con `MOSTRAR_DEFECTOS=1 pytest tests/api` fallan a la vista; cuando se corrija un defecto la prueba pasa a XPASS y el pipeline avisa para retirar la marca.

Resumen (ID, título, severidad y estado) en la sección 5 de [`informe.md`](informe.md).

## DEF-01: La comisión interbancaria no usa redondeo comercial (0.005 no sube)

| Campo | Valor |
|---|---|
| Módulo / regla | RN-09 / HU-N-08 CA2 · `qolqe/reglas/nucleo.py::calcular_comision` |
| Severidad | Media |
| Prioridad | Alta |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_nucleo.py::test_la_comisión_usa_redondeo_comercial_0005_sube` |

**Pasos para reproducir**
1. Iniciar sesión como Ana (987654321 / 4826).
2. `GET /api/transferencias/comision?monto=67.00&tipo=INTERBANCARIA`.
3. Repetir con `monto=71.00`.

**Resultado esperado:** 67.00 × 1.5 % = 1.005 → comisión `1.01`, total `68.01` (71.00 → `1.07`, total `72.07`).

**Resultado obtenido:** Comisión `1.00` / total `68.00` (71.00 → `1.06` / `72.06`). Se redondea a la mitad par (`ROUND_HALF_EVEN`) en lugar de hacia arriba. También afecta la transferencia real, que cobra el mismo valor.

**Evidencia:** `GET .../comision?monto=67.00&tipo=INTERBANCARIA` → `200 {"monto":"67.00","comision":"1.00","total":"68.00"}`

## DEF-02: El PIN con secuencia descendente (4321, 9876, 3210) se acepta al registrarse

| Campo | Valor |
|---|---|
| Módulo / regla | RN-03 / HU-N-01 CA4 · `qolqe/reglas/nucleo.py::validar_pin` |
| Severidad | Media |
| Prioridad | Alta |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_nucleo.py::test_un_pin_con_secuencia_descendente_es_rechazado` |

**Pasos para reproducir**
1. `POST /api/usuarios` con DNI `45678912`, nombres `Lucía Fernández`, celular `987000111` y PIN `4321`.

**Resultado esperado:** `422 PIN_INVALIDO`: RN-03 prohíbe secuencias ascendentes **y descendentes** (el ejemplo de la regla es `4321`).

**Resultado obtenido:** `201 Created`: la cuenta se crea con PIN `4321`. Solo se rechazan las secuencias ascendentes (`1234`, `0123`, `6789`).

**Evidencia:** `POST /api/usuarios {"pin":"4321",...}` → `201 {"id":207,"nombres":"Lucía Fernández Rojas","celular":"987000111",...}`

## DEF-03: Un inicio de sesión exitoso no reinicia el conteo de intentos fallidos

| Campo | Valor |
|---|---|
| Módulo / regla | RN-04 / HU-N-02 CA3 · `qolqe/api/autenticacion.py` |
| Severidad | Alta |
| Prioridad | Alta |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_nucleo.py::test_un_ingreso_exitoso_reinicia_el_conteo_de_intentos_fallidos` |

**Pasos para reproducir**
1. Fallar 2 veces el login de Bruno (912345678) con PIN `0000` (ambas `401`).
2. Iniciar sesión correctamente con PIN `7391` (`200`).
3. Fallar una vez más con PIN `0000`.

**Resultado esperado:** `401 CREDENCIALES_INVALIDAS`: el conteo se reinició con el ingreso exitoso, es solo el 1.er fallo.

**Resultado obtenido:** `423 CUENTA_BLOQUEADA`: los fallos previos al ingreso exitoso se siguen acumulando y la cuenta se bloquea 15 min.

**Evidencia:** `POST /api/auth/login {"celular":"912345678","pin":"0000"}` → `423 {"codigo":"CUENTA_BLOQUEADA","detail":"Superaste los intentos permitidos. Tu cuenta está bloqueada hasta las 07:18."}`

## DEF-04: Una transferencia interbancaria puede dejar el saldo negativo (la comisión no se valida contra el saldo)

| Campo | Valor |
|---|---|
| Módulo / regla | RN-08 / HU-N-08 CA2 · `qolqe/transacciones.py:62` |
| Severidad | Crítica |
| Prioridad | Alta |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_nucleo.py::test_la_comisión_también_debe_estar_cubierta_por_el_saldo_límite_exacto` |

**Pasos para reproducir**
1. Iniciar sesión como Carla (956781234 / 5917) y fijar su saldo en S/ 50.00 (`PUT /api/pruebas/saldo`).
2. `POST /api/transferencias` con `tipo=INTERBANCARIA`, `cci=00219300123456789012`, `monto=49.01` (comisión 1.00, total 50.01).

**Resultado esperado:** `422 SALDO_INSUFICIENTE`: el saldo debe cubrir monto **más** comisión (50.01 > 50.00) y el saldo sigue en S/ 50.00.

**Resultado obtenido:** `201 Created` y el saldo queda en **S/ -0.01**. `transacciones.py:62` compara `saldo < monto_cent` y no `monto + comisión`. Con monto 49.00 (total 50.00) y 60.00 sí se comporta bien.

**Evidencia:** `POST /api/transferencias` → `201 {"monto":"49.01","comision":"1.00","total":"50.01",...,"saldo":"-0.01"}`

## DEF-05: Cerrar sesión responde 204 pero el token sigue siendo válido

| Campo | Valor |
|---|---|
| Módulo / regla | HU-N-03 CA1 y CA2 · `qolqe/api/autenticacion.py::cerrar_sesion`, `qolqe/dependencias.py` |
| Severidad | Crítica |
| Prioridad | Alta |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_nucleo.py::test_al_cerrar_sesión_el_token_deja_de_ser_válido y ::test_cerrar_una_sesión_no_afecta_mis_otras_sesiones` |

**Pasos para reproducir**
1. `POST /api/auth/login` como Ana y guardar el `access_token`.
2. `POST /api/auth/logout` con ese token (`204`).
3. `GET /api/cuentas/me/saldo` con el mismo token.

**Resultado esperado:** `401 NO_AUTENTICADO`: el token ya no es válido.

**Resultado obtenido:** `200 OK` con el saldo: el token cerrado sigue funcionando hasta que vence (30 min). Un token robado no se puede invalidar cerrando la sesión. Causa probable: se revoca insertando el `jti` en `tokens_revocados`, pero la validación busca el **token completo** en esa tabla, y la sesión no se marca como cerrada.

**Evidencia:** `POST /api/auth/logout` → `204`; luego `GET /api/cuentas/me/saldo` → `200 {"saldo":"1500.00","moneda":"PEN",...}`

## DEF-06: Se puede transferir a una cuenta cerrada y el dinero se pierde

| Campo | Valor |
|---|---|
| Módulo / regla | RN-07 / HU-N-07 CA2 / HU-N-06 CA4 · `qolqe/api/transferencias.py::_resolver_destino_qolqe` |
| Severidad | Crítica |
| Prioridad | Alta |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_nucleo.py::test_no_se_puede_transferir_a_una_cuenta_cerrada y ::test_cierre_exitoso_nadie_puede_transferirme` |

**Pasos para reproducir**
1. Iniciar sesión como Ana.
2. `POST /api/transferencias` al celular `934567812` (Fabián, cuenta cerrada en la semilla) por S/ 10.00.
3. Alternativa: cerrar la cuenta de Diego (saldo 0.00) y transferirle.

**Resultado esperado:** `422 DESTINO_INACTIVO` y el saldo de Ana no cambia.

**Resultado obtenido:** `201 Created`: se debita a Ana (saldo 1490.00) y se acredita a una cuenta que ya no puede iniciar sesión. El código `DESTINO_INACTIVO` está en el contrato pero esta ruta nunca lo devuelve (sí lo hace `solicitudes.py:127`).

**Evidencia:** `POST /api/transferencias {"celular_destino":"934567812","monto":"10.00"}` → `201 {...,"destinatario":{"nombre":"Fabián R.","celular":"934567812"},"saldo":"1490.00"}`

## DEF-07: El historial excluye el día completo del límite superior (`hasta`), incluidos los movimientos de hoy

| Campo | Valor |
|---|---|
| Módulo / regla | R-G3-01 / HU-G3-01 CA2 · `qolqe/api/movimientos.py::_filtrar` |
| Severidad | Alta |
| Prioridad | Alta |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_historial.py::test_el_historial_por_defecto_incluye_los_movimientos_de_hoy, ::test_el_rango_incluye_completo_el_día_hasta y ::test_el_filtro_por_tipo_incluye_la_recarga_de_hoy` |

**Pasos para reproducir**
1. Iniciar sesión como Ana y transferir S/ 10.00 a Bruno.
2. `GET /api/movimientos` (por defecto, últimos 30 días hasta hoy).
3. Otra vía: con un movimiento de ayer, `GET /api/movimientos?desde=<ayer>&hasta=<ayer>`.

**Resultado esperado:** El historial por defecto **incluye los movimientos de hoy** (R-G3-01) y el rango incluye completos los días `desde` y `hasta` (CA2): la transferencia aparece primera.

**Resultado obtenido:** La transferencia de hoy no aparece (el primer movimiento es el de ayer) y `desde=hasta=<ayer>` devuelve 0 movimientos. La consulta compara `fecha BETWEEN 'AAAA-MM-DD' AND 'AAAA-MM-DD'` contra fechas con hora (`2026-10-12T07:00:00` > `2026-10-12`), así que el último día queda fuera. Afecta también la exportación CSV, que reutiliza el filtro. El seed de Ana tiene una recarga de hoy que no se ve en `tipo=RECARGA` (5 en vez de 6).

**Evidencia:** Tras `POST /api/transferencias` (código `TRF26101206582300001`): `GET /api/movimientos` → `movimientos[0].codigo_operacion = "PAG26101114032300001"` (de ayer); `total` sigue en 10.

## DEF-08: El detalle de un movimiento de otro usuario es visible (200 en lugar de 404)

| Campo | Valor |
|---|---|
| Módulo / regla | HU-G3-02 CA2 / propiedad de los datos · `qolqe/api/movimientos.py::detalle` |
| Severidad | Alta |
| Prioridad | Alta |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_historial.py::test_el_movimiento_de_otro_usuario_responde_404` |

**Pasos para reproducir**
1. Ana transfiere S/ 25.00 a Bruno y se anota el `codigo_operacion`.
2. Iniciar sesión como Carla (sin relación con esa operación).
3. `GET /api/movimientos/{codigo_operacion}`.

**Resultado esperado:** `404 MOVIMIENTO_NO_ENCONTRADO`: el código de un movimiento ajeno responde como si no existiera.

**Resultado obtenido:** `200 OK` con el movimiento completo de Ana (tipo, monto, descripción, contraparte `912345678`, categoría y nota). Cualquier usuario autenticado puede consultar movimientos ajenos si conoce o adivina el código. La consulta no filtra por `usuario_id`.

**Evidencia:** `GET /api/movimientos/TRF26101207074600001` como Carla → `200 {"tipo":"TRANSFERENCIA_ENVIADA","descripcion":"Transferencia a Bruno D.","contraparte":"912345678","monto":"25.00",...}`

## DEF-09: El destinatario de una transferencia ve el movimiento del emisor en el detalle

| Campo | Valor |
|---|---|
| Módulo / regla | HU-G3-02 CA1 / RN-10 · `qolqe/api/movimientos.py::detalle` |
| Severidad | Media |
| Prioridad | Media |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_historial.py::test_el_destinatario_ve_su_lado_de_la_transferencia_en_el_detalle` |

**Pasos para reproducir**
1. Ana transfiere S/ 25.00 a Bruno.
2. Iniciar sesión como Bruno.
3. `GET /api/movimientos/{codigo_operacion}` con el código del comprobante.

**Resultado esperado:** Bruno ve **su** movimiento: `TRANSFERENCIA_RECIBIDA`, monto `25.00` (ambos comparten el código, RN-10).

**Resultado obtenido:** Bruno recibe el movimiento de Ana: `TRANSFERENCIA_ENVIADA`. La consulta devuelve la primera fila con ese código (`ORDER BY m.id LIMIT 1`) sin filtrar por usuario. Misma causa raíz que DEF-08, pero con un síntoma distinto para el usuario legítimo.

**Evidencia:** `GET /api/movimientos/<codigo>` como Bruno → `200 {"tipo":"TRANSFERENCIA_ENVIADA",...}`

## DEF-10: Editar una categoría permite repetir el nombre de otra categoría

| Campo | Valor |
|---|---|
| Módulo / regla | R-G3-03 / HU-G3-05 CA1 · `qolqe/api/categorias.py::editar` |
| Severidad | Baja |
| Prioridad | Media |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, uvicorn/TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_historial.py::test_editar_valida_los_nombres_duplicados_de_otras_categorías` |

**Pasos para reproducir**
1. Iniciar sesión como Ana (categorías Comida, Familia, Servicios).
2. `PUT /api/categorias/{id de Comida}` con `{"nombre":"Familia"}` (o `"SERVICIOS"`).

**Resultado esperado:** `409 CATEGORIA_DUPLICADA`: el nombre es único sin distinguir mayúsculas (se compara con las demás categorías, no consigo misma).

**Resultado obtenido:** `200 OK`: quedan dos categorías con el mismo nombre. Al crear sí se valida; al editar no se llama a la verificación de duplicados.

**Evidencia:** `PUT /api/categorias/3 {"nombre":"Familia"}` → `200 {"id":3,"nombre":"Familia",...}`

## DEF-11: El token deja de ser válido a los 30 minutos exactos (descartado)

**Descartado: no es un defecto.** El requisito dice que el token es "válido por 30 minutos" y no precisa el minuto 30 exacto. No hay forma de confirmarlo con el docente, así que se acepta el comportamiento del sistema: a los 29 minutos el token vale y a los 30 ya no (`401 NO_AUTENTICADO`). La prueba quedó como escenario normal (`El token vale 30 minutos`, filas 29, 30 y 31). Se conserva el número para no renumerar los demás defectos.

## DEF-12: Dos operaciones del mismo usuario en el mismo segundo comparten el código de operación

| Campo | Valor |
|---|---|
| Módulo / regla | RN-10 / HU-N-07 · `qolqe/operaciones.py::generar_codigo_operacion` |
| Severidad | Alta |
| Prioridad | Media |
| Entorno | Qolqe Wallet 1.0.0, Python 3.14, TestClient, Linux; reproducible por API (sin navegador) |
| Prueba que lo detecta | `tests/api/test_nucleo.py::test_dos_transferencias_en_el_mismo_segundo_tienen_códigos_de_operación_distintos` |

**Pasos para reproducir**
1. Fijar el reloj: `PUT /api/pruebas/reloj {"ahora": "2026-10-17T10:00:00"}`.
2. Iniciar sesión como Ana y hacer dos transferencias seguidas a Bruno (S/ 1.00 y S/ 2.00).

**Resultado esperado:** dos códigos de operación distintos: RN-10 exige un código **único** por operación.

**Resultado obtenido:** ambas responden `201` con el mismo `TRF26101710000000001`. El código se arma como prefijo + fecha y hora hasta el segundo + id del usuario, sin secuencia. Consecuencia: `GET /api/movimientos/{codigo}` devuelve el primer movimiento (S/ 1.00) para las dos operaciones.

**Evidencia:** `POST /api/transferencias` ×2 → `201 {"codigo_operacion":"TRF26101710000000001",...}` en ambas.
