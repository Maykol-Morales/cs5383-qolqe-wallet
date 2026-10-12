# language: en
@g3
Feature: Historial de movimientos
  Como cliente
  Quiero consultar, clasificar y exportar mis movimientos
  Para controlar mis gastos

  # Datos: en los últimos 90 días Ana tiene 21 movimientos: 5 transferencias enviadas, 5 recibidas, 5 pagos de servicios
  # y 6 recargas (una es de hoy). 5 movimientos están en "Servicios" y 5 en "Familia".

  @HU-G3-01 @api
  Scenario: Por defecto se consultan los últimos 30 días hasta hoy
    Given que inicié sesión como Ana
    When consulto mi historial
    Then el rango del historial es de hace 30 días hasta hoy

  @HU-G3-01 @api @DEF-07
  Scenario: El historial por defecto incluye los movimientos de hoy
    Given que inicié sesión como Ana
    And que hice una transferencia de S/ 10.00 a Bruno
    When consulto mi historial
    Then el movimiento más reciente es esa transferencia

  @HU-G3-01 @api @DEF-07
  Scenario: El rango incluye completo el día "hasta"
    Given que tengo 3 movimientos de hace un día
    When consulto mi historial desde "ayer" hasta "ayer"
    Then el historial indica 3 movimientos y 1 páginas

  @HU-G3-01 @api
  Scenario: El rango incluye completo el día "desde"
    Given que tengo 3 movimientos de hace un día
    When consulto mi historial desde "ayer" hasta "hoy"
    Then el historial indica 3 movimientos y 1 páginas

  @HU-G3-01 @api
  Scenario: Un rango sin movimientos devuelve una lista vacía
    Given que tengo 3 movimientos de hace un día
    When consulto mi historial desde "hace 10 días" hasta "hace 2 días"
    Then el historial indica 0 movimientos y 1 páginas

  @HU-G3-01 @api
  Scenario Outline: Validación del rango de consulta (R-G3-01)
    Given que inicié sesión como Ana
    When consulto mi historial desde "<desde>" hasta "<hasta>"
    Then la operación es "<resultado>"

    Examples:
      | desde       | hasta       | resultado      |
      | hace 90 días | hoy        | exitosa        |
      | hace 91 días | hoy        | FILTRO_INVALIDO |
      | hace 10 días | hace 11 días | FILTRO_INVALIDO |
      | hace 5 días  | hace 5 días | exitosa        |
      | hace 5 días  | mañana      | FILTRO_INVALIDO |
      | hoy          | hoy         | exitosa        |
      | hace 101 días | hace 10 días | FILTRO_INVALIDO |
      | hace 100 días | hace 10 días | exitosa        |
      | hace 95 días | hace 5 días | exitosa        |

  @HU-G3-01 @api
  Scenario Outline: Filtro por tipo de movimiento
    Given que inicié sesión como Ana
    When consulto mi historial de los últimos 90 días de tipo "<tipo>"
    Then el historial indica 5 movimientos y 1 páginas
    And todos los movimientos son de tipo "<tipo>"

    Examples:
      | tipo                   |
      | TRANSFERENCIA_ENVIADA  |
      | TRANSFERENCIA_RECIBIDA |
      | PAGO_SERVICIO          |

  @HU-G3-01 @api @DEF-07
  Scenario: El filtro por tipo incluye la recarga de hoy
    Given que inicié sesión como Ana
    When consulto mi historial de los últimos 90 días de tipo "RECARGA"
    Then el historial indica 6 movimientos y 1 páginas

  @HU-G3-01 @api
  Scenario: Un tipo inexistente es rechazado
    Given que inicié sesión como Ana
    When consulto mi historial de los últimos 90 días de tipo "DEPOSITO"
    Then la respuesta es 422 con el código "FILTRO_INVALIDO"

  @HU-G3-01 @api
  Scenario Outline: Filtro por categoría
    Given que inicié sesión como Ana
    When consulto mi historial de los últimos 90 días de la categoría "<categoria>"
    Then el historial indica 5 movimientos y 1 páginas
    And todos los movimientos tienen la categoría "<categoria>"

    Examples:
      | categoria |
      | Servicios |
      | Familia   |

  @HU-G3-01 @api
  Scenario: Una categoría inexistente o de otro usuario es rechazada
    Given que inicié sesión como Ana
    When consulto mi historial de la categoría "NoExiste"
    Then la respuesta es 422 con el código "FILTRO_INVALIDO"

  @HU-G3-01 @api
  Scenario Outline: Paginación de 10 movimientos (R-G3-02)
    Given que tengo <n> movimientos de hace un día
    When consulto mi historial
    Then el historial indica <n> movimientos y <paginas> páginas

    Examples:
      | n  | paginas |
      | 0  | 1       |
      | 1  | 1       |
      | 9  | 1       |
      | 10 | 1       |
      | 11 | 2       |
      | 20 | 2       |
      | 21 | 3       |

  @HU-G3-01 @api
  Scenario Outline: Cada página trae como máximo 10 movimientos
    Given que tengo 11 movimientos de hace un día
    When consulto la página <pagina> de mi historial
    Then la página trae <cantidad> movimientos

    Examples:
      | pagina | cantidad |
      | 1      | 10       |
      | 2      | 1        |
      | 3      | 0        |

  @HU-G3-01 @api
  Scenario Outline: La página debe ser mayor o igual a 1
    Given que inicié sesión como Ana
    When consulto la página <pagina> de mi historial
    Then la operación es "<resultado>"

    Examples:
      | pagina | resultado       |
      | 0      | FILTRO_INVALIDO |
      | -1     | FILTRO_INVALIDO |
      | 1      | exitosa         |

  @HU-G3-01 @api
  Scenario: Los movimientos van del más reciente al más antiguo
    Given que inicié sesión como Ana
    When consulto mi historial de los últimos 90 días
    Then los movimientos están ordenados del más reciente al más antiguo

  @HU-G3-01 @api
  Scenario: Cada movimiento muestra importe negativo, comisión y saldo posterior
    Given que tengo 3 movimientos de hace un día
    When consulto mi historial
    Then el movimiento más reciente muestra importe "-0.01", comisión "0.00", saldo posterior "99.97" y tipo "TRANSFERENCIA_ENVIADA"

  @HU-G3-01 @api
  Scenario: El historial requiere sesión
    When consulto mi historial sin token
    Then la respuesta es 401 con el código "NO_AUTENTICADO"

  @HU-G3-02 @api
  Scenario: Detalle de mi propio movimiento
    Given que inicié sesión como Ana
    And que hice una transferencia de S/ 25.00 a Bruno
    When consulto el detalle de ese movimiento
    Then el detalle muestra tipo "TRANSFERENCIA_ENVIADA" y monto "25.00"

  @HU-G3-02 @api @DEF-09
  Scenario: El destinatario ve su lado de la transferencia en el detalle
    Given que Ana transfirió S/ 25.00 a Bruno
    And que inicié sesión como Bruno
    When consulto el detalle de ese movimiento
    Then el detalle muestra tipo "TRANSFERENCIA_RECIBIDA" y monto "25.00"

  @HU-G3-02 @api
  Scenario: Un código inexistente
    Given que inicié sesión como Ana
    When consulto el detalle del movimiento "NO000000000000000000"
    Then la respuesta es 404 con el código "MOVIMIENTO_NO_ENCONTRADO"

  @HU-G3-02 @api @DEF-08
  Scenario: El movimiento de otro usuario responde 404
    Given que Ana transfirió S/ 25.00 a Bruno
    And que inicié sesión como Carla
    When consulto el detalle de ese movimiento
    Then la respuesta es 404 con el código "MOVIMIENTO_NO_ENCONTRADO"

  @HU-G3-07 @api
  Scenario: Asignar una de mis categorías a un movimiento
    Given que inicié sesión como Ana
    And que hice una transferencia de S/ 25.00 a Bruno
    When clasifico ese movimiento con la categoría "Comida"
    Then el movimiento queda con la categoría "Comida"
    And el movimiento conserva su monto, fecha y tipo

  @HU-G3-07 @api
  Scenario: Quitar la categoría de un movimiento
    Given que inicié sesión como Ana
    And que hice una transferencia de S/ 25.00 a Bruno
    And que clasifiqué ese movimiento con la categoría "Comida"
    When le quito la categoría a ese movimiento
    Then el movimiento queda sin categoría

  @HU-G3-07 @api
  Scenario Outline: Longitud de la nota (R-G3-04)
    Given que inicié sesión como Ana
    And que hice una transferencia de S/ 25.00 a Bruno
    When agrego a ese movimiento una nota de <n> caracteres
    Then la operación es "<resultado>"

    Examples:
      | n   | resultado     |
      | 1   | exitosa       |
      | 100 | exitosa       |
      | 101 | NOTA_INVALIDA |

  @HU-G3-07 @api
  Scenario: Editar y quitar la nota
    Given que inicié sesión como Ana
    And que hice una transferencia de S/ 25.00 a Bruno
    And que agregué a ese movimiento la nota "Almuerzo"
    When le quito la nota a ese movimiento
    Then el movimiento queda sin nota
    And el movimiento conserva su monto, fecha y tipo

  @HU-G3-07 @api
  Scenario: Clasificar solo cambia lo enviado
    Given que inicié sesión como Ana
    And que hice una transferencia de S/ 25.00 a Bruno
    And que clasifiqué ese movimiento con la categoría "Comida"
    When agrego a ese movimiento una nota de 10 caracteres
    Then el movimiento queda con la categoría "Comida"

  @HU-G3-07 @api
  Scenario: No puedo usar la categoría de otro usuario
    Given que Carla tiene la categoría "Ajena"
    And que inicié sesión como Ana
    And que hice una transferencia de S/ 25.00 a Bruno
    When clasifico ese movimiento con la categoría de Carla
    Then la respuesta es 404 con el código "CATEGORIA_NO_ENCONTRADA"

  @HU-G3-07 @api
  Scenario: No puedo clasificar el movimiento de otro usuario
    Given que Ana transfirió S/ 25.00 a Bruno
    And que inicié sesión como Carla
    When clasifico ese movimiento con una nota de 10 caracteres
    Then la respuesta es 404 con el código "MOVIMIENTO_NO_ENCONTRADO"

  @HU-G3-08 @api
  Scenario: Exportar con el encabezado y formato esperados
    Given que tengo 3 movimientos de hace un día
    When exporto mis movimientos
    Then recibo un archivo CSV en UTF-8 con el encabezado "fecha;codigo_operacion;tipo;descripcion;monto;comision;importe;categoria;nota"
    And el CSV tiene 3 filas de datos con 9 columnas, punto decimal y separador punto y coma

  @HU-G3-08 @api
  Scenario: Exportar no pagina
    Given que tengo 21 movimientos de hace un día
    When exporto mis movimientos
    Then el CSV tiene 21 filas de datos con 9 columnas, punto decimal y separador punto y coma

  @HU-G3-08 @api
  Scenario: Sin movimientos el archivo contiene solo el encabezado
    Given que tengo 0 movimientos de hace un día
    When exporto mis movimientos
    Then el CSV tiene 0 filas de datos con 9 columnas, punto decimal y separador punto y coma

  @HU-G3-08 @api
  Scenario Outline: Exportar con los mismos filtros que el historial
    Given que inicié sesión como Ana
    When exporto mis movimientos de los últimos 90 días de tipo "<tipo>"
    Then el CSV tiene 5 filas de datos con 9 columnas, punto decimal y separador punto y coma
    And todas las filas del CSV son de tipo "<tipo>"

    Examples:
      | tipo                   |
      | TRANSFERENCIA_RECIBIDA |
      | PAGO_SERVICIO          |

  @HU-G3-08 @api
  Scenario Outline: Exportar aplica las mismas reglas de rango
    Given que inicié sesión como Ana
    When exporto mis movimientos desde "<desde>" hasta "<hasta>"
    Then la operación es "<resultado>"

    Examples:
      | desde        | hasta  | resultado       |
      | hace 90 días | hoy    | exitosa         |
      | hace 91 días | hoy    | FILTRO_INVALIDO |
      | hace 5 días  | mañana | FILTRO_INVALIDO |

  @HU-G3-08 @api
  Scenario: El CSV incluye la categoría y la nota
    Given que inicié sesión como Ana
    When exporto mis movimientos de los últimos 90 días de la categoría "Servicios"
    Then todas las filas del CSV tienen la categoría "Servicios"
