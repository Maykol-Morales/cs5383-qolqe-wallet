# Particiones de equivalencia y valores límite (Núcleo + G3)

Construido **solo** desde `docs/requisitos.md` (RN, HU, CA). Formatos: **A1** (equivalencia, una fila por partición) y **B1** (valores límite, una fila por frontera). Una técnica por variable; # = número de la lista acordada. Los resultados marcados *(a confirmar)* no los fija el requisito.

Tipo: V = válida · I = inválida. Lado: Dentro / Fuera del rango válido.

---

## Núcleo

### HU-N-01 · Registrarme

**#1 · RN-01 · CA2 · DNI** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N01-01 | 8 dígitos numéricos | V | `45678912` | Cuenta creada |
| EQ-N01-02 | Menos de 8 dígitos | I | `4567891` | `DNI_INVALIDO` |
| EQ-N01-03 | Más de 8 dígitos | I | `456789123` | `DNI_INVALIDO` |
| EQ-N01-04 | Contiene caracteres no numéricos | I | `4567891A` | `DNI_INVALIDO` |

**#2 · RN-02 · CA3 · Celular (formato)** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N01-05 | 9 dígitos y empieza con 9 | V | `987000111` | Cuenta creada |
| EQ-N01-06 | Menos de 9 dígitos | I | `98700011` | `CELULAR_INVALIDO` |
| EQ-N01-07 | Más de 9 dígitos | I | `9870001112` | `CELULAR_INVALIDO` |
| EQ-N01-08 | No empieza con 9 | I | `887000111` | `CELULAR_INVALIDO` |
| EQ-N01-09 | Contiene no numéricos | I | `98700011X` | `CELULAR_INVALIDO` |

**#3 · RN-02 · CA3 · Celular (unicidad)** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N01-10 | Celular no registrado | V | `987000111` | Cuenta creada |
| EQ-N01-11 | Registrado con cuenta activa | I | `987654321` | 409 `CELULAR_REGISTRADO` |
| EQ-N01-12 | Registrado con cuenta cerrada | I | `934567812` | 409 `CELULAR_REGISTRADO` |

**#4 · RN-03 · CA4 · PIN** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N01-13 | 4 dígitos, sin patrón | V | `4826` | Cuenta creada |
| EQ-N01-14 | Menos de 4 dígitos | I | `482` | `PIN_INVALIDO` |
| EQ-N01-15 | Más de 4 dígitos | I | `48261` | `PIN_INVALIDO` |
| EQ-N01-16 | No numérico | I | `48A6` | `PIN_INVALIDO` |
| EQ-N01-17 | Todos los dígitos iguales | I | `1111` | `PIN_INVALIDO` |
| EQ-N01-18 | Secuencia ascendente | I | `1234` | `PIN_INVALIDO` |
| EQ-N01-19 | Secuencia descendente | I | `4321` | `PIN_INVALIDO` |

**#6 · CA5 · Correo (opcional)** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N01-20 | Omitido | V | *(sin correo)* | Cuenta creada |
| EQ-N01-21 | Formato válido y no usado | V | `lucia@correo.pe` | Cuenta creada |
| EQ-N01-22 | Sin `@` | I | `lucia.correo.pe` | `CORREO_INVALIDO` |
| EQ-N01-23 | Sin dominio | I | `lucia@` | `CORREO_INVALIDO` |
| EQ-N01-24 | Usado por cuenta activa (igual) | I | correo existente | 409 `CORREO_REGISTRADO` |
| EQ-N01-25 | Usado por cuenta activa (otro uso de mayúsculas) | I | correo existente en MAYÚSCULAS | 409 `CORREO_REGISTRADO` |
| EQ-N01-26 | Usado solo por cuenta cerrada | V | correo de cuenta cerrada | Cuenta creada |

**#5 · CA1 · Nombres (2 a 80 caracteres)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N01-01 | largo de nombres | mín − 1 | 1 | Fuera | Error de validación |
| VL-N01-02 | largo de nombres | mín | 2 | Dentro | Cuenta creada |
| VL-N01-03 | largo de nombres | máx | 80 | Dentro | Cuenta creada |
| VL-N01-04 | largo de nombres | máx + 1 | 81 | Fuera | Error de validación |

### HU-N-02 · Iniciar sesión

**#10 · CA1, CA2, CA5 · Credenciales y estado de la cuenta** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N02-01 | Celular y PIN correctos, cuenta activa | V | credenciales válidas | 200 con token y sesión activa |
| EQ-N02-02 | Celular inexistente | I | `999999999` | 401 `CREDENCIALES_INVALIDAS` |
| EQ-N02-03 | PIN incorrecto | I | PIN erróneo | 401 `CREDENCIALES_INVALIDAS` (mismo mensaje que EQ-N02-02) |
| EQ-N02-04 | Cuenta cerrada | I | celular de cuenta cerrada | 401 `CUENTA_CERRADA` |
| EQ-N02-08 | Cuenta bloqueada con PIN correcto | I | celular bloqueado | 423 `CUENTA_BLOQUEADA` |

**#11 · CA6 · Dispositivo** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N02-05 | Dispositivo de confianza | V | id registrado | Ingresa, sin SMS de alerta |
| EQ-N02-06 | Dispositivo no registrado | V | id desconocido | Ingresa y recibe SMS de "nuevo dispositivo" |
| EQ-N02-07 | Dispositivo no enviado | V | *(sin id)* | Ingresa, sin SMS de alerta |

**#7 · RN-04 · CA3 · Intentos fallidos consecutivos (bloqueo al 3.º)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N02-01 | fallos consecutivos | máx − 1 | 2 | Dentro | 401 `CREDENCIALES_INVALIDAS`, sin bloqueo |
| VL-N02-02 | fallos consecutivos | máx | 3 | Fuera | 423 `CUENTA_BLOQUEADA` + SMS de aviso |
| VL-N02-08 | fallos consecutivos | mín | 1 | Dentro | 401 `CREDENCIALES_INVALIDAS`, sin bloqueo |

**#8 · RN-04 · CA4 · Minutos de bloqueo (15)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N02-03 | minutos desde el bloqueo | límite − 1 | 14 | Bloqueada | 423, ni con PIN correcto |
| VL-N02-04 | minutos desde el bloqueo | límite | 15 | Liberada | Ingresa con PIN correcto |

**#9 · CA1 · Vigencia del token (30 minutos)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N02-05 | minutos desde el login | límite − 1 | 29 | Dentro | Token válido |
| VL-N02-06 | minutos desde el login | límite | 30 | Fuera | 401 `NO_AUTENTICADO` (a los 30:00 exactos ya venció) |
| VL-N02-07 | minutos desde el login | límite + 1 | 31 | Fuera | 401 `NO_AUTENTICADO` |

### HU-N-04 · Consultar saldo y perfil

**#12 · CA3 · Token** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N04-01 | Token válido | V | token de sesión activa | 200 |
| EQ-N04-02 | Sin token | I | *(sin cabecera)* | 401 `NO_AUTENTICADO` |
| EQ-N04-03 | Token inválido | I | texto aleatorio | 401 `NO_AUTENTICADO` |
| EQ-N04-04 | Token vencido | I | token pasados 30 min | 401 `NO_AUTENTICADO` |
| EQ-N04-05 | Token firmado con otra clave | I | JWT con firma ajena | 401 `NO_AUTENTICADO` |
| EQ-N04-06 | Token alterado | I | payload modificado | 401 `NO_AUTENTICADO` |

### HU-N-05 · Editar mi perfil

**#5 · CA1 · Nombres (2 a 80 caracteres)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N05-01 | largo de nombres | mín − 1 | 1 | Fuera | 422 `PERFIL_INVALIDO` |
| VL-N05-02 | largo de nombres | mín | 2 | Dentro | 200 |
| VL-N05-03 | largo de nombres | mín + 1 | 3 | Dentro | 200 |
| VL-N05-04 | largo de nombres | máx − 1 | 79 | Dentro | 200 |
| VL-N05-05 | largo de nombres | máx | 80 | Dentro | 200 |
| VL-N05-06 | largo de nombres | máx + 1 | 81 | Fuera | 422 `PERFIL_INVALIDO` |

**#6 · CA1 · Correo** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N05-01 | Formato válido y no usado por otra cuenta activa | V | `ana.nueva@correo.pe` | 200 |
| EQ-N05-02 | El propio correo con otras mayúsculas | V | propio en MAYÚSCULAS | 200 |
| EQ-N05-03 | Formato inválido | I | `sin-arroba.pe` | `CORREO_INVALIDO` |
| EQ-N05-04 | Usado por otra cuenta (sin distinguir mayúsculas) | I | correo ajeno en MAYÚSCULAS | 409 `CORREO_REGISTRADO` |

### HU-N-06 · Cerrar mi cuenta

**#13 · HU-N-06 · CA1–CA4 · Cierre de cuenta** · Tabla de decisión

*Pendiente* = solicitud de dinero no vencida, enviada o recibida (CA3). S = se cumple, N = no se cumple. `X` = la acción ocurre.

**Condiciones**

| ID | Condición | Origen |
|---|---|---|
| C1 | El PIN ingresado coincide con el del titular | CA1 |
| C2 | El saldo es exactamente S/ 0.00 | CA2 |
| C3 | El titular no tiene solicitudes de dinero pendientes | CA3 |

**Acciones**

| ID | Acción |
|---|---|
| A1 | Cerrar la cuenta (204), cerrar todas sus sesiones, impedir nuevo login y rechazar transferencias entrantes (CA4) |
| A2 | Responder `PIN_INCORRECTO` |
| A3 | Responder `SALDO_PENDIENTE` |
| A4 | Responder 409 `SOLICITUDES_PENDIENTES` |
| A5 | La cuenta permanece activa y sin cambios |

**Orden de validación asumido** (el requisito no lo fija): C1 (PIN) → C2 (saldo) → C3 (solicitudes); responde el primer error que falle.

**Reglas**

| Regla | C1 | C2 | C3 | A1 | A2 | A3 | A4 | A5 | Estado |
|---|---|---|---|---|---|---|---|---|---|
| DT-N06-R1 | S | S | S | X | | | | | Definida |
| DT-N06-R2 | N | S | S | | X | | | X | Definida |
| DT-N06-R3 | S | N | S | | | X | | X | Definida |
| DT-N06-R4 | S | S | N | | | | X | X | Definida |
| DT-N06-R5 | N | N | S | | X | | | X | Definida (orden asumido) |
| DT-N06-R6 | N | S | N | | X | | | X | Definida (orden asumido) |
| DT-N06-R7 | S | N | N | | | X | | X | Definida (orden asumido) |
| DT-N06-R8 | N | N | N | | X | | | X | Definida (orden asumido) |

**#14 · CA2 · Saldo para cerrar (exactamente 0.00)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N06-01 | saldo (S/) | límite | 0.00 | Dentro | Cierre permitido |
| VL-N06-02 | saldo (S/) | límite + 0.01 | 0.01 | Fuera | `SALDO_PENDIENTE` |

### HU-N-07 · Transferir a otro usuario Qolqe

**#15 · RN-05 · CA2 · Monto** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N07-01 | Mayor que 0, hasta 500.00, ≤ 2 decimales | V | `100.50` | 201 |
| EQ-N07-02 | Cero | I | `0.00` | `MONTO_INVALIDO` |
| EQ-N07-03 | Negativo | I | `-10.00` | `MONTO_INVALIDO` |
| EQ-N07-04 | Mayor que 500.00 | I | `600.00` | `MONTO_INVALIDO` |
| EQ-N07-05 | Más de 2 decimales | I | `10.005` | `MONTO_INVALIDO` |
| EQ-N07-06 | No numérico | I | `abc` | 422 `SOLICITUD_INVALIDA` |
| EQ-N07-11 | Vacío | I | *(sin monto)* | 422 `SOLICITUD_INVALIDA` |

**#17 · RN-07 · CA2 · Destino** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N07-07 | Otro usuario con cuenta activa | V | celular de otro usuario | 201 |
| EQ-N07-08 | Uno mismo | I | mi propio celular | 422 `TRANSFERENCIA_A_SI_MISMO` |
| EQ-N07-09 | Celular no registrado | I | `999999999` | 404 `DESTINO_NO_REGISTRADO` |
| EQ-N07-10 | Cuenta cerrada | I | celular de cuenta cerrada | `DESTINO_INACTIVO` |

**#16 · CA1 · Descripción (hasta 60 caracteres)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N07-01 | largo de descripción | mín | 0 (omitida) | Dentro | 201 |
| VL-N07-02 | largo de descripción | máx | 60 | Dentro | 201 |
| VL-N07-03 | largo de descripción | máx + 1 | 61 | Fuera | Error de validación |

**#19 · RN-08 · Saldo vs monto + comisión** · VL *(saldo S/ 50.00, entre cuentas Qolqe, comisión 0.00)*

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N07-04 | monto + comisión vs saldo | saldo − 0.01 | 49.99 | Dentro | 201, saldo 0.01 |
| VL-N07-05 | monto + comisión vs saldo | saldo | 50.00 | Dentro | 201, saldo 0.00 |
| VL-N07-06 | monto + comisión vs saldo | saldo + 0.01 | 50.01 | Fuera | `SALDO_INSUFICIENTE`, saldo intacto |

**#18 · RN-06 · Límite diario acumulado** · VL *(límite vigente L; transferencias del día + monto)*

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N07-07 | acumulado del día + monto | L − 0.01 | L − 0.01 | Dentro | 201 |
| VL-N07-08 | acumulado del día + monto | L | L | Dentro | 201 |
| VL-N07-09 | acumulado del día + monto | L + 0.01 | L + 0.01 | Fuera | `LIMITE_DIARIO_EXCEDIDO` |

**#18 · RN-06 · Reinicio del límite diario a medianoche de Lima** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N07-10 | hora de Lima (límite agotado) | 00:00:00 − 1 s | 23:59:59 | Mismo día | `LIMITE_DIARIO_EXCEDIDO` |
| VL-N07-11 | hora de Lima (límite agotado) | 00:00:00 | 00:00:00 | Día nuevo | 201 |

### HU-N-08 · Transferir a otro banco

**#22 · CA1 · CCI** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N08-01 | 20 dígitos | V | `00219300123456789012` | 201 |
| EQ-N08-02 | Menos de 20 dígitos | I | 19 dígitos | `CCI_INVALIDO` |
| EQ-N08-03 | Más de 20 dígitos | I | 21 dígitos | `CCI_INVALIDO` |
| EQ-N08-04 | Contiene no numéricos | I | 19 dígitos + `X` | `CCI_INVALIDO` |

**#20 · RN-09 · CA2 · Comisión** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N08-05 | Entre cuentas Qolqe | V | S/ 100.00 a celular | Comisión 0.00 |
| EQ-N08-06 | Interbancaria, 1.5 % menor al mínimo | V | S/ 10.00 | Comisión 1.00 (mínimo) |
| EQ-N08-07 | Interbancaria, 1.5 % dentro del rango | V | S/ 100.00 | Comisión 1.50 |
| EQ-N08-08 | Interbancaria, 1.5 % mayor al máximo | V | S/ 400.00 | Comisión 5.00 (máximo) |
| EQ-N08-09 | Interbancaria, 1.5 % apenas mayor al máximo | V | S/ 333.34 (1.5 % = 5.0001) | Comisión 5.00 (máximo) |

**#21 · RN-09 · Redondeo a 2 decimales (0.005 sube), validado por el servidor** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N08-01 | comisión bruta (1.5 % del monto) | justo bajo 0.005 | monto 66.99 → 1.00485 | Debajo | Comisión 1.00 |
| VL-N08-02 | comisión bruta (1.5 % del monto) | exactamente 0.005 | monto 67.00 → 1.005 | En el límite | Comisión 1.01 |

**#19 · RN-08 · HU-N-08 CA2 · Saldo vs monto + comisión (interbancaria, monto 100.00, total 101.50)** · VL

| ID | Variable | Frontera | Valor (saldo) | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N08-03 | saldo vs total | total − 0.01 | 101.49 | Fuera | `SALDO_INSUFICIENTE` |
| VL-N08-04 | saldo vs total | total | 101.50 | Dentro | 201, saldo 0.00 |
| VL-N08-05 | saldo vs total | solo el monto (sin comisión) | 100.00 | Fuera | `SALDO_INSUFICIENTE` |

### HU-N-09 · Simular la comisión

**#23 · CA1 · Tipo de transferencia** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N09-01 | QOLQE | V | S/ 100.00 | Comisión 0.00, total 100.00, sin operación |
| EQ-N09-02 | INTERBANCARIA | V | S/ 100.00 | Comisión 1.50, total 101.50, sin operación |
| EQ-N09-03 | Tipo inexistente | I | `OTRO` | Rechazado (error de validación) |
| EQ-N09-04 | Tipo no indicado | V | *(sin campo)* | Se trata como QOLQE: comisión 0.00 |

---

## G3 · Historial y categorías

### HU-G3-01 · Consultar mis movimientos

**#24 · R-G3-01 · Rango de fechas** · VL *(días = hasta − desde; hoy = H)*

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-G301-01 | días del rango | máx | 90 | Dentro | 200 |
| VL-G301-02 | días del rango | máx + 1 | 91 | Fuera | `FILTRO_INVALIDO` |
| VL-G301-03 | días del rango | mín | 0 (`desde` = `hasta`) | Dentro | 200 |
| VL-G301-04 | días del rango | mín − 1 | −1 (`desde` > `hasta`) | Fuera | `FILTRO_INVALIDO` |
| VL-G301-05 | `hasta` | límite | H (hoy) | Dentro | 200, incluye movimientos de hoy |
| VL-G301-06 | `hasta` | límite + 1 día | H + 1 | Fuera | `FILTRO_INVALIDO` |

**#24 · CA1 · Formato de fecha** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G301-11 | Formato AAAA-MM-DD de una fecha real | V | `2026-11-10` | 200 |
| EQ-G301-12 | Otro formato | I | `15-11-2026` | 422 |
| EQ-G301-13 | Mes o día fuera de calendario | I | `2026-02-30` | 422 |
| EQ-G301-14 | Texto que no es fecha | I | `ayer` | 422 |

**#24 · CA2 · Días completos de `desde` y `hasta`** · VL *(consulta del 10 al 12; hora de Lima)*

| ID | Variable | Frontera | Valor (fecha del movimiento) | Lado | Esperado |
|---|---|---|---|---|---|
| VL-G301-14 | fecha del movimiento | inicio − 1 s | día 9 a las 23:59:59 | Fuera | No aparece |
| VL-G301-15 | fecha del movimiento | inicio | día 10 a las 00:00:00 | Dentro | Aparece |
| VL-G301-16 | fecha del movimiento | fin | día 12 a las 23:59:59 | Dentro | Aparece |
| VL-G301-17 | fecha del movimiento | fin + 1 s | día 13 a las 00:00:00 | Fuera | No aparece |

**#25 · CA1 · Tipo de movimiento** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G301-01 | Sin filtro de tipo | V | *(omitido)* | Todos los tipos |
| EQ-G301-02 | Transferencia enviada | V | `TRANSFERENCIA_ENVIADA` | Solo de ese tipo |
| EQ-G301-03 | Transferencia recibida | V | `TRANSFERENCIA_RECIBIDA` | Solo de ese tipo |
| EQ-G301-04 | Recarga | V | `RECARGA` | Solo de ese tipo |
| EQ-G301-05 | Pago de servicio | V | `PAGO_SERVICIO` | Solo de ese tipo |
| EQ-G301-06 | Tipo inexistente | I | `DEPOSITO` | `FILTRO_INVALIDO` |

**#26 · CA1 · Categoría (filtro)** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G301-07 | Sin filtro de categoría | V | *(omitida)* | Todas |
| EQ-G301-08 | Categoría propia | V | una de mis categorías | Solo sus movimientos |
| EQ-G301-09 | Categoría de otro usuario | I | categoría ajena | `FILTRO_INVALIDO` |
| EQ-G301-10 | Categoría inexistente | I | `NoExiste` | `FILTRO_INVALIDO` |

**#27 · R-G3-02 · CA3 · Movimientos por página (10)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-G301-07 | total de movimientos | máx de la pág. 1 | 10 | Dentro | 1 página |
| VL-G301-08 | total de movimientos | máx + 1 | 11 | Fuera | 2 páginas |
| VL-G301-09 | total de movimientos | máx de la pág. 2 | 20 | Dentro | 2 páginas |
| VL-G301-10 | total de movimientos | máx de la pág. 2 + 1 | 21 | Fuera | 3 páginas |
| VL-G301-13 | total de movimientos | mín | 0 | Dentro | 1 página, lista vacía |

**#28 · R-G3-02 · Número de página (≥ 1)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-G301-11 | página | mín − 1 | 0 | Fuera | `FILTRO_INVALIDO` |
| VL-G301-12 | página | mín | 1 | Dentro | 200, hasta 10 movimientos |
| VL-G301-18 | página | última | 3 (de 21 movimientos) | Dentro | 200, 1 movimiento |
| VL-G301-19 | página | última + 1 | 4 (de 21 movimientos) | Dentro | 200, 0 movimientos |
| VL-G301-20 | tipo de dato | no numérica | `abc` | Fuera | 422 |

### HU-G3-02 · Detalle de un movimiento

**#29 · CA1, CA2 · Código de operación** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G302-01 | Código de un movimiento propio | V | código propio | 200 con el detalle |
| EQ-G302-02 | Código de un movimiento de otro usuario | I | código ajeno | 404 `MOVIMIENTO_NO_ENCONTRADO` |
| EQ-G302-03 | Código inexistente | I | código no emitido | 404 `MOVIMIENTO_NO_ENCONTRADO` |

### HU-G3-03 · Crear categoría · HU-G3-05 · Editar categoría

**#30 · R-G3-03 · Largo del nombre (3 a 20)** · VL *(aplica también a HU-G3-05)*

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-G303-01 | largo del nombre | mín − 1 | 2 | Fuera | `CATEGORIA_INVALIDA` |
| VL-G303-02 | largo del nombre | mín | 3 | Dentro | 201 |
| VL-G303-03 | largo del nombre | máx | 20 | Dentro | 201 |
| VL-G303-04 | largo del nombre | máx + 1 | 21 | Fuera | `CATEGORIA_INVALIDA` |
| VL-G303-07 | largo del nombre | vacío | 0 | Fuera | `CATEGORIA_INVALIDA` |
| VL-G303-08 | largo del nombre (tras recortar espacios) | solo espacios | `"   "` | Fuera | `CATEGORIA_INVALIDA` (los espacios alrededor no cuentan) |

**#31 · R-G3-03 · Color** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G303-01 | Color de la paleta de 8 | V | un color de la paleta | 201 |
| EQ-G303-02 | Hexadecimal fuera de la paleta | I | `#000000` | `CATEGORIA_INVALIDA` |
| EQ-G303-03 | No es un color | I | `rojo` | `CATEGORIA_INVALIDA` |
| EQ-G303-09 | Color de la paleta en minúsculas | V | `#e53935` | 201, se guarda como `#E53935` |
| EQ-G303-10 | Color vacío o no enviado | I | *(sin campo)* | `CATEGORIA_INVALIDA` |

**#32 · R-G3-03 · HU-G3-05 CA1 · Unicidad del nombre** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G303-04 | Nombre nuevo | V | nombre no usado | 201 |
| EQ-G303-05 | Igual a una categoría existente | I | mismo nombre | 409 `CATEGORIA_DUPLICADA` |
| EQ-G303-06 | Igual con otro uso de mayúsculas | I | mismo nombre en MAYÚSCULAS | 409 `CATEGORIA_DUPLICADA` |
| EQ-G303-07 | Al editar: conserva su propio nombre | V | su nombre actual | 200 (no se compara consigo misma) |
| EQ-G303-08 | Al editar: nombre de otra categoría | I | nombre de otra categoría propia | 409 `CATEGORIA_DUPLICADA` |
| EQ-G303-11 | Mismo nombre que una categoría de otro usuario | V | nombre de una categoría ajena | 201 |

**#33 · R-G3-03 · Cantidad de categorías (máx. 10)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-G303-05 | categorías existentes al crear | máx − 1 | 9 | Dentro | 201 (queda en 10) |
| VL-G303-06 | categorías existentes al crear | máx | 10 | Fuera | `LIMITE_CATEGORIAS` |

**HU-G3-05 · CA1 · Id de la categoría a editar** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G305-01 | Id de una categoría propia | V | id propio | 200 |
| EQ-G305-02 | Id de otro usuario | I | id ajeno | 404 |
| EQ-G305-03 | Id inexistente | I | `999999` | 404 |

### HU-G3-06 · Eliminar una categoría

**CA1 · Id de la categoría a eliminar** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G306-01 | Id de una categoría propia | V | id propio | 204, sus movimientos quedan sin categoría |
| EQ-G306-02 | Id de otro usuario | I | id ajeno | 404, la categoría ajena sigue |
| EQ-G306-03 | Id inexistente | I | `999999` | 404 |
| EQ-G306-04 | Id ya eliminado | I | id de una categoría eliminada | 404 |

### HU-G3-07 · Clasificar un movimiento

**#34 · R-G3-04 · CA2 · Largo de la nota (hasta 100)** · VL

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-G307-01 | largo de la nota | mín | 1 | Dentro | 200 |
| VL-G307-04 | largo de la nota | mín − 1 (quitar la nota) | 0 | Dentro | 200, sin nota |
| VL-G307-05 | largo de la nota | máx − 1 | 99 | Dentro | 200 |
| VL-G307-02 | largo de la nota | máx | 100 | Dentro | 200 |
| VL-G307-03 | largo de la nota | máx + 1 | 101 | Fuera | `NOTA_INVALIDA` |

**#35 · CA1, CA3, CA4 · Categoría y movimiento a clasificar** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G307-01 | Mi categoría en mi movimiento | V | ambos propios | 200; monto, fecha y tipo no cambian |
| EQ-G307-02 | Quitar la categoría | V | categoría nula | 200, sin categoría |
| EQ-G307-03 | Categoría de otro usuario | I | categoría ajena | 404 |
| EQ-G307-04 | Movimiento de otro usuario | I | movimiento ajeno | 404 |
| EQ-G307-05 | Categoría inexistente | I | `999999` | 404 |
| EQ-G307-06 | Movimiento inexistente | I | código no emitido | 404 |

### HU-G3-08 · Exportar mis movimientos

**#36 · CA1–CA3 · Contenido del CSV** · EQ

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-G308-01 | Hay movimientos en el filtro | V | filtro con datos | CSV con encabezado y una fila por movimiento, sin paginar |
| EQ-G308-02 | No hay movimientos en el filtro | V | filtro sin datos | CSV solo con el encabezado |
| EQ-G308-03 | Filtro fuera de las reglas de rango | I | rango de 91 días | `FILTRO_INVALIDO` (mismas reglas que #24) |
