# Matriz de trazabilidad · HU → caso → nivel → resultado

Generada por `.github/scripts/reportes.py` desde los JUnit del run local (commit `4960809`, 2026-10-30 18:44 UTC).
No se edita a mano: el pipeline la regenera y la publica en https://maykol-morales.github.io/cs5383-qolqe-wallet/trazabilidad.html.

- **Caso**: `CP-Wnn` (web, etiqueta del `.feature`) o `CP-A-<feature>-nn` (API, n.º de escenario en su `.feature`).
- **Resultado**: `pasa k/n` (n ejecuciones: ejemplos de un Outline o las 3 corridas web); `defecto conocido` = falla
  esperada (`xfail` estricto en pytest, paso invertido en web) enlazada a [docs/defectos.md](defectos.md).
- Un caso con varias HU aparece una vez por HU.

## Resumen por historia

| HU | Nivel | Casos | Pasan | Defecto conocido | Otros |
|---|---|---|---|---|---|
| HU-N-01 | API | 10 | 9 | 1 | 0 |
| HU-N-02 | API | 11 | 10 | 1 | 0 |
| HU-N-03 | API | 3 | 1 | 2 | 0 |
| HU-N-04 | API | 3 | 3 | 0 | 0 |
| HU-N-05 | API | 4 | 4 | 0 | 0 |
| HU-N-06 | API | 7 | 6 | 1 | 0 |
| HU-N-07 | API | 17 | 14 | 2 | 1 |
| HU-N-08 | API | 12 | 7 | 5 | 0 |
| HU-N-09 | API | 4 | 4 | 0 | 0 |
| HU-G3-01 | API + Web E2E | 26 | 21 | 5 | 0 |
| HU-G3-02 | API | 4 | 2 | 2 | 0 |
| HU-G3-03 | API + Web E2E | 12 | 12 | 0 | 0 |
| HU-G3-04 | API | 3 | 3 | 0 | 0 |
| HU-G3-05 | API | 8 | 7 | 1 | 0 |
| HU-G3-06 | API | 5 | 5 | 0 | 0 |
| HU-G3-07 | API + Web E2E | 12 | 12 | 0 | 0 |
| HU-G3-08 | API + Web E2E | 9 | 9 | 0 | 0 |
| — | API | 2 | 2 | 0 | 0 |

## Detalle

| HU | Caso | Nivel | Escenario | Resultado | Defecto |
|---|---|---|---|---|---|
| HU-N-01 | CP-A-nucleo_registro-01 | API | Registro exitoso con saldo y límite diario iniciales | pasa | — |
| HU-N-01 | CP-A-nucleo_registro-02 | API | Se envía un SMS de bienvenida | pasa | — |
| HU-N-01 | CP-A-nucleo_registro-03 | API | Validación del DNI (8 dígitos numéricos) | pasa 5/5 | — |
| HU-N-01 | CP-A-nucleo_registro-04 | API | Validación del celular (9 dígitos y empieza con 9) | pasa 5/5 | — |
| HU-N-01 | CP-A-nucleo_registro-05 | API | Un celular ya registrado, incluso con cuenta cerrada, no se puede reutilizar | pasa 2/2 | — |
| HU-N-01 | CP-A-nucleo_registro-06 | API | Validación del PIN (4 dígitos, sin repetidos ni secuencias) | pasa 9/9 | — |
| HU-N-01 | CP-A-nucleo_registro-07 | API | Un PIN con secuencia descendente es rechazado | defecto conocido (3 ejec.) | [DEF-02](defectos.md#def-02-el-pin-con-secuencia-descendente-4321-9876-3210-se-acepta-al-registrarse) |
| HU-N-01 | CP-A-nucleo_registro-08 | API | Validación del correo | pasa 6/6 | — |
| HU-N-01 | CP-A-nucleo_registro-09 | API | El correo es opcional | pasa | — |
| HU-N-01 | CP-A-nucleo_registro-10 | API | Longitud de los nombres al registrarme (2 a 80 caracteres) | pasa 4/4 | — |
| HU-N-02 | CP-A-nucleo_sesion-01 | API | Ingreso con credenciales correctas | pasa | — |
| HU-N-02 | CP-A-nucleo_sesion-02 | API | Credenciales inválidas con mensaje genérico | pasa | — |
| HU-N-02 | CP-A-nucleo_sesion-03 | API | Bloqueo al tercer intento fallido consecutivo | pasa | — |
| HU-N-02 | CP-A-nucleo_sesion-04 | API | Dos intentos fallidos no bloquean la cuenta | pasa | — |
| HU-N-02 | CP-A-nucleo_sesion-05 | API | Un ingreso exitoso reinicia el conteo de intentos fallidos | defecto conocido (1 ejec.) | [DEF-03](defectos.md#def-03-un-inicio-de-sesión-exitoso-no-reinicia-el-conteo-de-intentos-fallidos) |
| HU-N-02 | CP-A-nucleo_sesion-06 | API | Durante el bloqueo ni el PIN correcto permite ingresar; pasados 15 minutos sí | pasa 4/4 | — |
| HU-N-02 | CP-A-nucleo_sesion-07 | API | Una cuenta cerrada no puede iniciar sesión | pasa | — |
| HU-N-02 | CP-A-nucleo_sesion-08 | API | Aviso de nuevo dispositivo | pasa 2/2 | — |
| HU-N-02 | CP-A-nucleo_sesion-12 | API | Un solo intento fallido no bloquea la cuenta | pasa | — |
| HU-N-02 | CP-A-nucleo_sesion-13 | API | Sin identificador de dispositivo no se envía la alerta | pasa | — |
| HU-N-02 | CP-A-nucleo_sesion-14 | API | El token vale 30 minutos | pasa 3/3 | — |
| HU-N-03 | CP-A-nucleo_sesion-09 | API | Al cerrar sesión el token deja de ser válido | defecto conocido (1 ejec.) | [DEF-05](defectos.md#def-05-cerrar-sesión-responde-204-pero-el-token-sigue-siendo-válido) |
| HU-N-03 | CP-A-nucleo_sesion-10 | API | Cerrar una sesión no afecta mis otras sesiones | pasa | — |
| HU-N-03 | CP-A-nucleo_sesion-11 | API | Al cerrar una de mis sesiones esa sesión deja de ser válida | defecto conocido (1 ejec.) | [DEF-05](defectos.md#def-05-cerrar-sesión-responde-204-pero-el-token-sigue-siendo-válido) |
| HU-N-04 | CP-A-nucleo_cuenta-01 | API | Consulta de saldo | pasa | — |
| HU-N-04 | CP-A-nucleo_cuenta-02 | API | Consulta de perfil con DNI enmascarado | pasa | — |
| HU-N-04 | CP-A-nucleo_cuenta-03 | API | Consulta sin una sesión válida | pasa 5/5 | — |
| HU-N-05 | CP-A-nucleo_cuenta-04 | API | Longitud de los nombres al editar mi perfil (2 a 80 caracteres) | pasa 6/6 | — |
| HU-N-05 | CP-A-nucleo_cuenta-05 | API | Cambio de correo | pasa 5/5 | — |
| HU-N-05 | CP-A-nucleo_cuenta-06 | API | El DNI y el celular no se pueden modificar | pasa | — |
| HU-N-05 | CP-A-nucleo_cuenta-07 | API | Al cambiar el correo se envía un SMS de aviso | pasa | — |
| HU-N-06 | CP-A-nucleo_cuenta-08 | API | Cierre con PIN incorrecto | pasa | — |
| HU-N-06 | CP-A-nucleo_cuenta-09 | API | Solo se cierra con saldo exactamente S/ 0.00 | pasa 2/2 | — |
| HU-N-06 | CP-A-nucleo_cuenta-10 | API | No se puede cerrar con solicitudes de dinero pendientes | pasa | — |
| HU-N-06 | CP-A-nucleo_cuenta-11 | API | Cierre exitoso: no puedo volver a ingresar | pasa | — |
| HU-N-06 | CP-A-nucleo_cuenta-12 | API | Cierre exitoso: todas mis sesiones se cierran | pasa | — |
| HU-N-06 | CP-A-nucleo_cuenta-13 | API | Cierre exitoso: nadie puede transferirme | defecto conocido (1 ejec.) | [DEF-06](defectos.md#def-06-se-puede-transferir-a-una-cuenta-cerrada-y-el-dinero-se-pierde) |
| HU-N-06 | CP-A-nucleo_cuenta-14 | API | Orden de validación del cierre: PIN, luego saldo, luego solicitudes | pasa 4/4 | — |
| HU-N-07 | CP-A-nucleo_transferencias-01 | API | Transferencia exitosa a un usuario registrado | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-02 | API | El saldo del destinatario aumenta | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-03 | API | Validación del monto por operación | pasa 10/10 | — |
| HU-N-07 | CP-A-nucleo_transferencias-04 | API | Descripción de hasta 60 caracteres | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-05 | API | Descripción de exactamente 60 caracteres | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-06 | API | No se puede transferir a uno mismo | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-07 | API | No se puede transferir a un celular no registrado | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-08 | API | No se puede transferir a una cuenta cerrada | defecto conocido (1 ejec.) | [DEF-06](defectos.md#def-06-se-puede-transferir-a-una-cuenta-cerrada-y-el-dinero-se-pierde) |
| HU-N-07 | CP-A-nucleo_transferencias-11 | API | El saldo nunca queda negativo en transferencias entre cuentas Qolqe | pasa 3/3 | — |
| HU-N-07 | CP-A-nucleo_transferencias-12 | API | El límite diario de S/ 1000.00 de Diego se respeta | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-13 | API | Una transferencia que alcanza exactamente el límite diario es válida | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-14 | API | Transferencias simultáneas no superan el límite diario ni dejan el saldo negativo | omitido | — |
| HU-N-07 | CP-A-nucleo_transferencias-21 | API | El monto debe ser numérico | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-22 | API | El monto es obligatorio | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-23 | API | Un acumulado un centavo bajo el límite diario es válido | pasa | — |
| HU-N-07 | CP-A-nucleo_transferencias-24 | API | El límite diario se reinicia a medianoche de Lima | pasa 2/2 | — |
| HU-N-07 | CP-A-nucleo_transferencias-33 | API | Dos transferencias en el mismo segundo tienen códigos de operación distintos | defecto conocido (1 ejec.) | [DEF-12](defectos.md#def-12-dos-operaciones-del-mismo-usuario-en-el-mismo-segundo-comparten-el-código-de-operación) |
| HU-N-08 | CP-A-nucleo_transferencias-09 | API | El saldo debe cubrir el monto más la comisión interbancaria | pasa 2/2 | — |
| HU-N-08 | CP-A-nucleo_transferencias-10 | API | La comisión también debe estar cubierta por el saldo (límite exacto) | defecto conocido (1 ejec.) | [DEF-04](defectos.md#def-04-una-transferencia-interbancaria-puede-dejar-el-saldo-negativo-la-comisión-no-se-valida-contra-el-saldo) |
| HU-N-08 | CP-A-nucleo_transferencias-15 | API | Comisión interbancaria de 1.5 % con mínimo S/ 1.00 y máximo S/ 5.00 | pasa 11/11 | — |
| HU-N-08 | CP-A-nucleo_transferencias-16 | API | La comisión usa redondeo comercial (0.005 sube) | defecto conocido (2 ejec.) | [DEF-01](defectos.md#def-01-la-comisión-interbancaria-no-usa-redondeo-comercial-0005-no-sube) |
| HU-N-08 | CP-A-nucleo_transferencias-17 | API | Validación del CCI (20 dígitos) | pasa 4/4 | — |
| HU-N-08 | CP-A-nucleo_transferencias-18 | API | El movimiento interbancario muestra solo los últimos 4 dígitos del CCI | pasa | — |
| HU-N-08 | CP-A-nucleo_transferencias-25 | API | Con saldo igual al total de una interbancaria de S/ 100.00 la operación es válida | pasa | — |
| HU-N-08 | CP-A-nucleo_transferencias-26 | API | Con saldo menor al total de una interbancaria de S/ 100.00 se rechaza | defecto conocido (2 ejec.) | [DEF-04](defectos.md#def-04-una-transferencia-interbancaria-puede-dejar-el-saldo-negativo-la-comisión-no-se-valida-contra-el-saldo) |
| HU-N-08 | CP-A-nucleo_transferencias-29 | API | El límite diario cuenta las transferencias interbancarias hasta el límite | pasa 2/2 | — |
| HU-N-08 | CP-A-nucleo_transferencias-30 | API | Una interbancaria que supera el límite diario acumulado se rechaza | defecto conocido (1 ejec.) | [DEF-13](defectos.md#def-13-el-límite-diario-no-cuenta-las-transferencias-interbancarias) |
| HU-N-08 | CP-A-nucleo_transferencias-31 | API | Las interbancarias del día cuentan para el límite de una transferencia a Qolqe | defecto conocido (1 ejec.) | [DEF-13](defectos.md#def-13-el-límite-diario-no-cuenta-las-transferencias-interbancarias) |
| HU-N-08 | CP-A-nucleo_transferencias-32 | API | Las transferencias a Qolqe del día cuentan para el límite de una interbancaria | pasa | — |
| HU-N-09 | CP-A-nucleo_transferencias-19 | API | Simulación de la comisión sin realizar ninguna operación | pasa 2/2 | — |
| HU-N-09 | CP-A-nucleo_transferencias-20 | API | La simulación valida el monto | pasa | — |
| HU-N-09 | CP-A-nucleo_transferencias-27 | API | Un tipo de transferencia inexistente es rechazado | pasa | — |
| HU-N-09 | CP-A-nucleo_transferencias-28 | API | Sin tipo la simulación se trata como transferencia entre cuentas Qolqe | pasa | — |
| HU-G3-01 | CP-A-historial-01 | API | Por defecto se consultan los últimos 30 días hasta hoy | pasa | — |
| HU-G3-01 | CP-A-historial-02 | API | El historial por defecto incluye los movimientos de hoy | defecto conocido (1 ejec.) | [DEF-07](defectos.md#def-07-el-historial-excluye-el-día-completo-del-límite-superior-hasta-incluidos-los-movimientos-de-hoy) |
| HU-G3-01 | CP-A-historial-03 | API | El rango incluye completo el día "hasta" | defecto conocido (1 ejec.) | [DEF-07](defectos.md#def-07-el-historial-excluye-el-día-completo-del-límite-superior-hasta-incluidos-los-movimientos-de-hoy) |
| HU-G3-01 | CP-A-historial-04 | API | El rango incluye completo el día "desde" | pasa | — |
| HU-G3-01 | CP-A-historial-05 | API | Un rango sin movimientos devuelve una lista vacía | pasa | — |
| HU-G3-01 | CP-A-historial-06 | API | Validación del rango de consulta (R-G3-01) | pasa 9/9 | — |
| HU-G3-01 | CP-A-historial-07 | API | Filtro por tipo de movimiento | pasa 3/3 | — |
| HU-G3-01 | CP-A-historial-08 | API | El filtro por tipo incluye la recarga de hoy | defecto conocido (1 ejec.) | [DEF-07](defectos.md#def-07-el-historial-excluye-el-día-completo-del-límite-superior-hasta-incluidos-los-movimientos-de-hoy) |
| HU-G3-01 | CP-A-historial-09 | API | Un tipo inexistente es rechazado | pasa | — |
| HU-G3-01 | CP-A-historial-10 | API | Filtro por categoría | pasa 2/2 | — |
| HU-G3-01 | CP-A-historial-11 | API | Una categoría inexistente como filtro es rechazada | pasa | — |
| HU-G3-01 | CP-A-historial-12 | API | Paginación de 10 movimientos (R-G3-02) | pasa 7/7 | — |
| HU-G3-01 | CP-A-historial-13 | API | Cada página trae como máximo 10 movimientos | pasa 3/3 | — |
| HU-G3-01 | CP-A-historial-14 | API | La página debe ser mayor o igual a 1 | pasa 3/3 | — |
| HU-G3-01 | CP-A-historial-15 | API | Los movimientos van del más reciente al más antiguo | pasa | — |
| HU-G3-01 | CP-A-historial-16 | API | Cada movimiento muestra importe negativo, comisión y saldo posterior | pasa | — |
| HU-G3-01 | CP-A-historial-17 | API | El historial requiere sesión | pasa | — |
| HU-G3-01 | CP-A-historial-38 | API | Una fecha mal formada es rechazada | pasa 3/3 | — |
| HU-G3-01 | CP-A-historial-39 | API | Una categoría de otro usuario como filtro es rechazada | pasa | — |
| HU-G3-01 | CP-A-historial-40 | API | La página debe ser numérica | pasa | — |
| HU-G3-01 | CP-A-historial-41 | API | El rango incluye desde las 00:00:00 del día "desde" y excluye el día anterior | pasa | — |
| HU-G3-01 | CP-A-historial-42 | API | El rango incluye hasta las 23:59:59 del día "hasta" y excluye el día siguiente | defecto conocido (1 ejec.) | [DEF-07](defectos.md#def-07-el-historial-excluye-el-día-completo-del-límite-superior-hasta-incluidos-los-movimientos-de-hoy) |
| HU-G3-01 | — | Web E2E | De noche en Lima, con el celular en hora UTC, el historial muestra los últimos 30 días | defecto conocido (1 ejec.) | [DEF-14](defectos.md#def-14-de-noche-en-lima-con-el-celular-en-otra-zona-horaria-el-historial-sale-vacío) |
| HU-G3-01 | CP-W02 | Web E2E | CP-W02 · Filtrar el historial por tipo "Recargas" | pasa | — |
| HU-G3-01 | CP-W03 | Web E2E | CP-W03 · Filtrar el historial por tipo "Pagos de servicios" | pasa | — |
| HU-G3-01 | CP-W04 | Web E2E | CP-W04 · Paginar el historial de 10 en 10 con Siguiente y Anterior | pasa | — |
| HU-G3-02 | CP-A-historial-18 | API | Detalle de mi propio movimiento | pasa | — |
| HU-G3-02 | CP-A-historial-19 | API | El destinatario ve su lado de la transferencia en el detalle | defecto conocido (1 ejec.) | [DEF-09](defectos.md#def-09-el-destinatario-de-una-transferencia-ve-el-movimiento-del-emisor-en-el-detalle) |
| HU-G3-02 | CP-A-historial-20 | API | Un código inexistente | pasa | — |
| HU-G3-02 | CP-A-historial-21 | API | El movimiento de otro usuario responde 404 | defecto conocido (1 ejec.) | [DEF-08](defectos.md#def-08-el-detalle-de-un-movimiento-de-otro-usuario-es-visible-200-en-lugar-de-404) |
| HU-G3-03 | CP-A-categorias-01 | API | Crear una categoría con nombre y color de la paleta | pasa | — |
| HU-G3-03 | CP-A-categorias-02 | API | Longitud del nombre (3 a 20 caracteres) | pasa 5/5 | — |
| HU-G3-03 | CP-A-categorias-03 | API | El color debe ser de la paleta de 8 colores | pasa 10/10 | — |
| HU-G3-03 | CP-A-categorias-04 | API | El nombre es único sin distinguir mayúsculas | pasa 4/4 | — |
| HU-G3-03 | CP-A-categorias-05 | API | Máximo 10 categorías por usuario (R-G3-03) | pasa 3/3 | — |
| HU-G3-03 | CP-A-categorias-18 | API | Un nombre de solo espacios es rechazado | pasa | — |
| HU-G3-03 | CP-A-categorias-19 | API | Un color en minúsculas se acepta y se guarda en mayúsculas | pasa | — |
| HU-G3-03 | CP-A-categorias-20 | API | El color es obligatorio | pasa | — |
| HU-G3-03 | CP-A-categorias-21 | API | Un color vacío es rechazado | pasa | — |
| HU-G3-03 | CP-A-categorias-22 | API | Otro usuario puede tener una categoría con el mismo nombre | pasa | — |
| HU-G3-03 | CP-W90 | Web E2E (IA) | CP-W90 · La IA crea "Viajes" y clasifica el último movimiento | pasa | — |
| HU-G3-03 | CP-W01 | Web E2E | CP-W01 · Clasificar el último movimiento en una categoría nueva | pasa 2/2 | — |
| HU-G3-04 | CP-A-categorias-06 | API | Mis categorías en orden alfabético con su cantidad de movimientos | pasa | — |
| HU-G3-04 | CP-A-categorias-07 | API | Solo veo mis categorías | pasa | — |
| HU-G3-04 | CP-A-categorias-17 | API | Las categorías requieren sesión | pasa | — |
| HU-G3-05 | CP-A-categorias-08 | API | Cambiar el nombre y el color de una categoría | pasa | — |
| HU-G3-05 | CP-A-categorias-09 | API | Cambiar solo el color conserva el nombre | pasa | — |
| HU-G3-05 | CP-A-categorias-10 | API | Editar no compara la categoría consigo misma | pasa 2/2 | — |
| HU-G3-05 | CP-A-categorias-11 | API | Editar valida los nombres duplicados de otras categorías | defecto conocido (2 ejec.) | [DEF-10](defectos.md#def-10-editar-una-categoría-permite-repetir-el-nombre-de-otra-categoría) |
| HU-G3-05 | CP-A-categorias-12 | API | Editar aplica la regla de color de la paleta | pasa | — |
| HU-G3-05 | CP-A-categorias-13 | API | No puedo editar la categoría de otro usuario | pasa | — |
| HU-G3-05 | CP-A-categorias-23 | API | Longitud del nombre al editar (3 a 20 caracteres) | pasa 4/4 | — |
| HU-G3-05 | CP-A-categorias-24 | API | Editar una categoría que no existe responde 404 | pasa | — |
| HU-G3-06 | CP-A-categorias-14 | API | Eliminar una categoría deja sus movimientos sin categoría | pasa | — |
| HU-G3-06 | CP-A-categorias-15 | API | Eliminar una categoría ajena responde 404 y no la borra | pasa | — |
| HU-G3-06 | CP-A-categorias-16 | API | Eliminar una categoría no afecta los movimientos de otras categorías | pasa | — |
| HU-G3-06 | CP-A-categorias-25 | API | Eliminar una categoría que no existe responde 404 | pasa | — |
| HU-G3-06 | CP-A-categorias-26 | API | Eliminar dos veces la misma categoría responde 404 la segunda vez | pasa | — |
| HU-G3-07 | CP-A-historial-22 | API | Asignar una de mis categorías a un movimiento | pasa | — |
| HU-G3-07 | CP-A-historial-23 | API | Quitar la categoría de un movimiento | pasa | — |
| HU-G3-07 | CP-A-historial-24 | API | Longitud de la nota (R-G3-04) | pasa 5/5 | — |
| HU-G3-07 | CP-A-historial-25 | API | Editar la nota | pasa | — |
| HU-G3-07 | CP-A-historial-26 | API | Quitar la nota | pasa | — |
| HU-G3-07 | CP-A-historial-27 | API | Clasificar solo cambia lo enviado | pasa | — |
| HU-G3-07 | CP-A-historial-28 | API | No puedo usar la categoría de otro usuario | pasa | — |
| HU-G3-07 | CP-A-historial-29 | API | No puedo clasificar el movimiento de otro usuario | pasa | — |
| HU-G3-07 | CP-A-historial-43 | API | Una categoría inexistente al clasificar responde 404 | pasa | — |
| HU-G3-07 | CP-A-historial-44 | API | Un movimiento inexistente al clasificar responde 404 | pasa | — |
| HU-G3-07 | CP-W90 | Web E2E (IA) | CP-W90 · La IA crea "Viajes" y clasifica el último movimiento | pasa | — |
| HU-G3-07 | CP-W01 | Web E2E | CP-W01 · Clasificar el último movimiento en una categoría nueva | pasa 2/2 | — |
| HU-G3-08 | CP-A-historial-30 | API | Exportar con el encabezado y formato esperados | pasa | — |
| HU-G3-08 | CP-A-historial-31 | API | Exportar no pagina | pasa | — |
| HU-G3-08 | CP-A-historial-32 | API | Sin movimientos el archivo contiene solo el encabezado | pasa | — |
| HU-G3-08 | CP-A-historial-33 | API | Exportar con los mismos filtros que el historial | pasa 2/2 | — |
| HU-G3-08 | CP-A-historial-34 | API | Exportar aplica las mismas reglas de rango | pasa 4/4 | — |
| HU-G3-08 | CP-A-historial-35 | API | Exportar con la categoría de otro usuario es rechazado | pasa | — |
| HU-G3-08 | CP-A-historial-36 | API | Exportar requiere sesión | pasa | — |
| HU-G3-08 | CP-A-historial-37 | API | El CSV incluye la categoría y la nota | pasa | — |
| HU-G3-08 | CP-W05 | Web E2E | CP-W05 · Exportar a CSV el historial filtrado por recargas | pasa | — |
| — | test_contrato_openapi | API | Contrato OpenAPI (Schemathesis, 1 prueba + subpruebas) | pasa 61/61 | — |
| — | test_la_app_responde | API | test_la_app_responde | pasa | — |
