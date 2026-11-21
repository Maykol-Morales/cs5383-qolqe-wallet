# Schemathesis vs. nuestros features: qué detecta cada uno y cómo se complementan

Pedido de la profesora para la entrega final: mostrar **en detalle qué casos reporta Schemathesis**, compararlos con los
casos que escribimos nosotros (`features/`), y decir **qué encuentra Schemathesis que nuestros features no** y en qué
nos ayuda.

Todas las cifras de este documento salen de **una sola corrida**, la misma que muestra el dashboard
`reportes/dashboard-contrato.html` (pestañas *Hallazgos* y *Todos los casos*). Si se vuelve a correr, las cifras
pueden variar un poco (semilla, orden, bloqueo de la cuenta de Ana durante el fuzzing de login).

## 1. Qué se ejecutó

| Dato | Valor |
|---|---|
| Herramienta | Schemathesis 4.31.1 (CLI) con `--checks all`, `--seed 1`, `--max-examples 30` |
| Comando | `python demo.py schemathesis todos` (servidor Qolqe temporal + CLI) |
| Objetivo | `GET /openapi.json` de Qolqe (OpenAPI 3.1): 69 operaciones, **60 probadas** (se excluyen logout, sesiones, reloj, reiniciar y cierre de cuenta, que invalidan la sesión compartida) |
| Autenticación | Token de Ana (987654321) en `Authorization` |
| Resultado | **2 321 casos, 50 hallazgos únicos (66 casos con algún check fallido), 0 respuestas 5xx** |
| Por fase (casos / con falla) | Examples 141 / 2 · Coverage 768 / 26 · Fuzzing 510 / 29 · Stateful 902 / 9 |

El gate del pipeline (`demo.py schemathesis` sin `todos`) valida solo 5 checks de conformidad. Aquí se activan además
`positive_data_acceptance`, `negative_data_rejection`, `allow_header_conformance` y `ensure_resource_availability`:
dan ruido y por eso no son gate, pero son los que más información dan para esta comparación.

Dónde ver cada cosa: *Schemathesis* (agregados por operación y fase), *Comparativa con pytest-bdd* (qué escenario nuestro
ataca lo mismo), *Hallazgos* (los 50, con petición, respuesta y `curl`) y *Todos los casos* (los 2 321, filtrables, con CSV).
Los datos son de Schemathesis (logs VCR y HAR); la clasificación y la columna «¿BDD lo prueba?» son del script del dashboard.

## 2. Los 50 hallazgos

Schemathesis informa 4 tipos de fallo. Ninguno es un 5xx; según nuestro criterio de defecto («incumple la documentación
o da 5xx», `CLAUDE.md`) ninguno lo es por sí solo, y cada uno se clasificó:

| Tipo (check de Schemathesis) | Hallazgos | Qué significa |
|---|---|---|
| `positive_data_acceptance` — «rechazó una solicitud válida según el OpenAPI» | **28** | El contrato es más laxo que la regla de negocio. Imprecisión del contrato, no defecto del código |
| `negative_data_rejection` — «aceptó una solicitud que viola el OpenAPI» | **4** | Se envió un dato que el esquema declara inválido y la API respondió éxito. Se explican abajo |
| `allow_header_conformance` — `Allow` inválido en 405 | **17** | Ruido de FastAPI |
| `ensure_resource_availability` — recurso no disponible tras crearlo | **1** | Ventana de DEF-15 |

### 2.1 Contrato impreciso (28): del alcance Núcleo + G3, los 8 están cubiertos por escenarios nuestros

Columna *Nuestros escenarios*: cuántos escenarios BDD provocan la misma respuesta (operación + estado + código), que es
lo que mide el dashboard. Es una aproximación: indica que ya probamos esa regla, no que el escenario sea idéntico.

**Alcance Núcleo + G3 (8 de 28): todos cubiertos**

| Operación | Petición de Schemathesis (resumen) | Respuesta | Casos | Nuestros escenarios (ejemplo) |
|---|---|---|---|---|
| `GET /api/transferencias/comision` | `?monto=0` | 422 `MONTO_INVALIDO` | 2 | 1 · «La simulación valida el monto» |
| `POST /api/transferencias` | `monto: 0.0` | 422 `MONTO_INVALIDO` | 2 | 1 · «Validación del monto por operación» |
| `POST /api/usuarios` | PIN de dígitos iguales | 422 `PIN_INVALIDO` | 1 | 1 · «Validación del PIN» |
| `PUT /api/cuentas/me` | `nombres: null` | 422 `PERFIL_INVALIDO` | 1 | 1 · «Longitud de los nombres (2 a 80)» |
| `POST /api/auth/login` | credenciales válidas con la cuenta ya bloqueada | 423 `CUENTA_BLOQUEADA` | 1 | 3 · «Bloqueo al tercer intento fallido» (efecto del fuzzing: ver 6) |
| `GET /api/movimientos` | `hasta` futura | 422 `FILTRO_INVALIDO` | 2 | 5 · filas «mañana» del Outline de fechas |
| `GET /api/movimientos/exportar` | `desde=2000-01-01` (más de 90 días) | 422 `FILTRO_INVALIDO` | 3 | 2 · «Exportar aplica las mismas reglas de rango» |
| `POST /api/categorias` | categoría número 11 | 422 `LIMITE_CATEGORIAS` | 1 | 1 · «Máximo 10 categorías» |

**Otros módulos (20 de 28):** 12 los provoca algún escenario de `features/otros_*.feature` (que escribimos solo para
cobertura): `POST /api/recargas` y `/programadas` (monto 0), `POST /api/limites/alertas` y `PUT /api/limites` (umbral y
límite 0), `POST`/`PUT /api/contactos`, `POST /api/solicitudes` y `/rechazar`, `POST /api/servicios/pagos` (deuda en
cobranza), `POST /api/seguridad/dispositivos` y `/desbloqueo/confirmar`, `PUT /api/seguridad/pin`. Los **8 restantes
no los provoca ningún escenario** y son entradas extremas: ids de 20 a 32 dígitos o `2^63` en la ruta
(`DELETE /api/servicios/afiliaciones/{id}`, `GET /api/servicios/pagos`, `POST /api/recargas/programadas/{id}/pausar`,
`POST /api/solicitudes/{id}/aceptar`), cuerpos con claves aleatorias en `PUT` (`/api/limites/alertas/{id}`,
`/api/recargas/programadas/{id}`, `/api/servicios/afiliaciones/{id}`) y `PUT /api/pruebas/saldo` (API de soporte). Qolqe los
maneja bien (422 sin 500); solo que el OpenAPI no documenta ese 422.

### 2.2 «Aceptó datos que violan el OpenAPI» (4)

| # | Operación | Petición | Respuesta | Análisis |
|---|---|---|---|---|
| 1 | `POST /api/transferencias` | `{"tipo":"QOLQE","celular_destino":"912345678","monto":"10.00","cci":"AAA"}` | **201**, transfirió | **Nuevo, requiere decisión (ver 4.1)** |
| 2 | `GET /api/movimientos` | `?hasta=0` | **200**, rango 1969-12-02 a 1970-01-01, 0 movimientos | **Nuevo, requiere decisión (ver 4.2)** |
| 3 | `POST /api/seguridad/desbloqueo/solicitar` | `{"celular":"aaaaaaaaaa"}` | 202 «Si el celular corresponde a una cuenta bloqueada…» | Intencional: responde igual para no revelar qué celulares existen. Decisión de seguridad |
| 4 | `POST /api/auth/login` | `{"pin":"aaaaa"}` | 423 | La cuenta de Ana ya estaba bloqueada por el propio fuzzing; el 423 va antes que la validación de formato. Orden de validación, no defecto |

### 2.3 `Allow` inválido en 405 (17)

Al probar métodos no soportados, FastAPI devuelve 405 con un `Allow` que no lista todos los métodos del recurso (p. ej.
`Allow: GET` en `/api/categorias`, que también admite `POST`). Es comportamiento del framework. **Ruido, no se registra.**

### 2.4 Recurso no disponible tras crearlo (1)

`POST /api/solicitudes/11/aceptar` responde 404 justo después de crear la solicitud 11. Es **DEF-15** (la respuesta sale
antes del commit). Ya está registrado (`docs/defectos.md`) y se reproduce de forma determinista con
`tests/api/reproducir_def15.py`.

### 2.5 Advertencias de Schemathesis (no son fallos)

- **«Schema validation mismatch» en 10 operaciones** (`POST /api/categorias`, `/contactos`, `/limites/alertas`,
  `/recargas/programadas`, `/servicios/afiliaciones`, `/usuarios`…): la validación real es más estricta que lo documentado.
  Es la conclusión de 2.1 vista por operación.
- **«Missing test data»: operaciones que devolvieron siempre 404** (`GET /api/servicios/pagos/{codigo}`,
  `PUT`/`DELETE /api/seguridad/dispositivos/{id}`, `POST /api/solicitudes/{id}/aceptar` y `/rechazar`). El OpenAPI no declara
  los enlaces entre operaciones, así que Schemathesis no halla los ids. Nuestros features sí las ejercitan con datos
  semilla: aquí **los features llegan más lejos que Schemathesis**.
- **«Authentication failed» en `POST /api/auth/login`**: esperado; el login solo devuelve 401 a un token ajeno.

## 3. Qué detecta cada uno

**Schemathesis y no nuestros features**

| Hallazgo | Por qué no lo veíamos |
|---|---|
| `cci` incoherente con el tipo, y la transferencia se ejecuta (2.2 #1) | Nuestros escenarios siempre arman cuerpos coherentes (o `QOLQE` con celular, o interbancaria con CCI) |
| Fechas numéricas aceptadas (2.2 #2) | Usamos fechas `AAAA-MM-DD`, `hoy`, `mañana`, `hace N días` |
| Ids fuera de rango (2.1, los 8 sin cobertura) | Probamos «id que no existe» (404), no «id de 30 dígitos» |
| **DEF-15**: 500 al repetir el registro (CI) y 404 tras crear (2.4) | Nuestros pasos van en serie; Schemathesis encadena llamadas muy rápidas |
| Las reglas que el OpenAPI no declara (28) | Es una auditoría del contrato, no de la lógica |
| Operaciones de módulos ajenos, sin escribir un caso | Cobertura barata de 60 operaciones |

**Nuestros features y no Schemathesis.** Schemathesis valida la **forma** (tipos, códigos, esquema, cabeceras); no conoce
las reglas de negocio. De los 16 defectos abiertos (DEF-11 está descartado), los features encontraron **13** (DEF-01 a 10, 12,
13 y 14), Schemathesis **2** (DEF-15 y DEF-17) y k6 **1** (DEF-16):

| Defecto | Lo que viola | ¿Lo vio Schemathesis? | Por qué no |
|---|---|---|---|
| DEF-01 redondeo de la comisión | RN-09 | No | Responde 200 con un `string` válido; solo un cálculo exacto lo ve |
| DEF-02 PIN descendente aceptado | RN-03 | No | Un string de 4 dígitos cumple el esquema |
| DEF-03 login exitoso no reinicia intentos | RN-04 | No | Requiere una secuencia con significado |
| DEF-04 interbancaria deja saldo negativo | RN-08 | No | Invariante entre dos respuestas (saldo antes y después) |
| DEF-05 logout no invalida el token | HU-N-03 | No | Exige reutilizar el token tras el logout |
| DEF-06 transferencia a cuenta cerrada pierde dinero | RN-07 | No | Estado de otra cuenta |
| DEF-07 historial excluye el día `hasta` | R-G3-01 | No | El esquema no dice qué movimientos debe traer |
| DEF-08 / DEF-09 detalle ajeno visible | autorización | No | Requiere dos usuarios |
| DEF-10 categoría editable con nombre duplicado | R-G3-03 | No | Unicidad sin reflejo en el esquema |
| DEF-12 / DEF-13 código repetido; límite diario sin interbancarias | RN-06 | No | Invariantes de negocio |
| DEF-14 historial vacío de noche (UI) | R-G3-01 | No | Es de la interfaz web |
| DEF-15 respuesta antes del commit | consistencia | **Sí** | Concurrencia: el modo stateful lo expone |
| DEF-16 `database is locked` con 40+ logins | capacidad | No (lo halló k6) | Requiere carga concurrente |

## 4. Hallazgos que requirieron decisión del equipo

**Decisión tomada: opción B.** 4.1 se registró como **DEF-17** (Baja, contrato; `docs/defectos.md`, escenario `@DEF-17` en
`features/nucleo_transferencias.feature`, xfail estricto) y 4.2 queda como **observación**. Los defectos abiertos pasan de 15 a 16.

Ambos aceptan una entrada que **el propio OpenAPI declara inválida**, pero **ningún requisito dice lo que debería pasar**.
Se reprodujeron a mano contra un servidor limpio (2026-11-20).

### 4.1 `POST /api/transferencias`: `cci` basura con `tipo: QOLQE`

- **Qué pasa.** `{"tipo":"QOLQE","celular_destino":"912345678","monto":"10.00","cci":"AAA"}` → **201**; el saldo de Ana baja de
  S/ 1 500.00 a S/ 1 490.00 y Bruno recibe S/ 10.00. El control sin `cci` responde igual.
- **Lo que declara el OpenAPI.** `SolicitudTransferencia.cci`: `pattern ^\d{20}$`, `minLength 20`, `maxLength 20`, «CCI de 20
  dígitos (tipo INTERBANCARIA)». Con `tipo: INTERBANCARIA`, un CCI inválido sí da `CCI_INVALIDO` (HU-N-08 CA1).
- **Lo que pasa en el sentido contrario.** `tipo: INTERBANCARIA` con `celular_destino: "basura"` y un CCI válido → 201 (comisión
  S/ 1.00): el servidor ignora los campos que no corresponden al tipo, en ambos sentidos.
- **Qué dicen los requisitos.** HU-N-07 CA1 pide celular o contacto, monto y descripción opcional; no menciona campos
  sobrantes. No hay incumplimiento de un requisito.
- **Impacto real.** Ninguno para el usuario: el destino correcto recibe el monto correcto. El riesgo es que un cliente con un
  error (manda el CCI de otro campo) no se entera. Es un endpoint que mueve dinero.
- **Por qué no lo vimos.** Todos nuestros cuerpos son coherentes con el tipo.

### 4.2 `GET /api/movimientos` (y `/exportar`): `hasta=0`

- **Qué pasa.** `?hasta=0` → **200**, `desde 1969-12-02`, `hasta 1970-01-01`, 0 movimientos. `?desde=0&hasta=0` y
  `/exportar?hasta=0` también responden 200 (CSV solo con el encabezado). `?hasta=abc` sí da 422.
- **Lo que declara el OpenAPI.** `desde` y `hasta`: `format: date`, «AAAA-MM-DD». Pydantic acepta un entero como marca de tiempo
  Unix; es un comportamiento por defecto del framework.
- **Qué dicen los requisitos.** R-G3-01 (desde ≤ hasta, máx. 90 días, hasta no futura) se cumple: 1970 no es futura y el
  rango es de 30 días.
- **Impacto real.** Ninguno: lista vacía. La UI manda siempre `AAAA-MM-DD`.
- **Por qué no lo vimos.** Nuestras fechas son siempre `AAAA-MM-DD`, `hoy`, `mañana` o `hace N días`.

### Opciones

| Opción | Qué implica |
|---|---|
| A. Ambos como observaciones (precedente del informe §2: «datos inválidos aceptados» de bajo impacto) | Quedan en este documento; no cambian los 15 defectos; se proponen escenarios pero no se agregan |
| **B. 4.1 como DEF-17 (Baja, contrato) y 4.2 como observación (elegida)** | Mueve dinero y rompe una validación que el contrato promete, pero 4.2 es solo lectura y viene del framework. Defectos 15 → 16; hay que actualizar informe §5/§6, `defectos.md`, `CLAUDE.md` y los decks |
| **C. Ambos como DEF-17 y DEF-18 (Baja)** | Es lo que dice la regla literal («incumple la documentación»). Defectos 15 → 17; mismo trabajo de actualización |

Con la opción elegida se agregó el escenario `@DEF-17` (xfail estricto) y su paso en `tests/api/test_nucleo.py`.

## 5. En qué nos ayuda Schemathesis (conclusión)

1. **Verificación cruzada del contrato.** En Núcleo + G3, los 8 hallazgos de «contrato impreciso» ya los provoca algún escenario
   nuestro (8 de 8): no se nos pasó ninguna validación de entrada. Fuera del alcance, 12 de 20 también.
2. **Entradas que no se nos ocurrieron.** Dos comportamientos nuevos (4.1 y 4.2) y los ids extremos.
3. **Concurrencia.** Es la única herramienta que nos descubrió un defecto de consistencia (DEF-15).
4. **Auditoría del OpenAPI.** Las reglas de negocio existen en `requisitos.md` pero no en `/openapi.json`; se recomienda
   endurecerlo (`minimum`, `enum`, `pattern`, `maxLength`) en el informe §6.4. No modificamos `qolqe/`.
5. **Costo.** Unos 40 s y ningún caso escrito, frente a 371 pruebas BDD de ~1 min. Es complemento, no reemplazo: sin los
   features no habríamos encontrado ninguno de los 13 defectos de lógica de negocio e interfaz.

Para no duplicar trabajo, la pestaña de comparativa del dashboard valida contra el OpenAPI la petición de cada escenario BDD y
marca como *candidato a redundante* los que solo repiten lo que el contrato ya cubre. Eran 44; se reforzaron con el paso
«no se persiste ningún cambio si la operación fue rechazada» y quedan 12 (lecturas sin estado y «requiere sesión»).

## 6. Limitaciones

- Una sola semilla (`--seed 1`) y 30 ejemplos por operación: otra semilla puede descubrir otros valores. El número de
  hallazgos ha variado entre corridas (40, 44, 47 y 50).
- El fuzzing de `login` bloquea a Ana (RN-04); las peticiones siguientes salen 423 y Schemathesis las reporta como «rechazó una
  solicitud válida» aunque es la regla funcionando. Un token de otro usuario evitaría ese ruido.
- La columna «¿BDD lo prueba?» compara (operación, estado, código), no el motivo. Un escenario puede dar la misma respuesta
  por otra causa.

## 7. Cómo reproducir

```bash
python demo.py schemathesis todos          # servidor temporal + todos los checks; abre el HTML y el dashboard
python demo.py schemathesis g3 todos       # solo movimientos y categorías
python demo.py dashboard                   # regenera el dashboard con los últimos logs (requiere pytest --alluredir para la comparativa)
```

Artefactos de la corrida (no versionados): `reporte-schemathesis/` (HTML nativo, VCR, HAR, JUnit) y
`reportes/dashboard-contrato.html`. Cada hallazgo trae su comando `st replay <id>`.
