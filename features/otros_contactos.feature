# language: en
@fuera-de-alcance
Feature: Contactos y solicitudes de dinero (G4, fuera de alcance)
  Como cliente
  Quiero guardar a mis contactos frecuentes y pedirles dinero
  Para transferir y cobrar sin recordar celulares

  # Escenarios para la cobertura del SUT: camino feliz y errores principales, no un análisis EP/VL.
  # Datos: Ana tiene los contactos "Bruno" (favorito) y "Prima Carla". Solicitudes: Bruno le pidió
  # S/ 45.00 por "Almuerzo del viernes" (pendiente), Carla le pidió S/ 30.00 por "Entradas al cine"
  # (creada hace 50 h: vencida) y Ana le pidió S/ 20.00 a Bruno por "Taxi al aeropuerto" (pendiente).

  Background:
    Given que inicié sesión como Ana

  @HU-G4-01 @HU-G4-02 @api
  Scenario: Agregar un contacto
    When agrego el contacto 998877665 con alias "Diego"
    Then la respuesta es 201
    And la respuesta tiene "nombre" igual a "Diego S."
    And la respuesta tiene "favorito" igual a "false"
    And mis contactos son "Bruno, Diego, Prima Carla"

  @HU-G4-01 @api
  Scenario Outline: Contacto rechazado
    When agrego el contacto <celular> con alias "<alias>"
    Then la respuesta es <estado> con el código "<codigo>"
    And mis contactos son "Bruno, Prima Carla"

    Examples:
      | celular   | alias   | estado | codigo                |
      | 812345678 | Diego   | 422    | CELULAR_INVALIDO      |
      | 987654321 | Yo      | 422    | CONTACTO_PROPIO       |
      | 911111111 | Nadie   | 404    | CELULAR_NO_REGISTRADO |
      | 934567812 | Fabián  | 404    | CELULAR_NO_REGISTRADO |
      | 912345678 | Bruno 2 | 409    | CONTACTO_EXISTENTE    |
      | 998877665 | bruno   | 409    | ALIAS_DUPLICADO       |
      | 998877665 | Di      | 422    | ALIAS_INVALIDO        |
      | 998877665 | Diego!  | 422    | ALIAS_INVALIDO        |

  @HU-G4-02 @api
  Scenario Outline: Buscar contactos sin distinguir mayúsculas ni tildes
    Given que agregué el contacto 998877665 con alias "José"
    When busco mis contactos con "<texto>"
    Then encuentro <n> contactos

    Examples:
      | texto | n |
      | jose  | 1 |
      | PRIMA | 1 |
      | xyz   | 0 |

  @HU-G4-03 @api
  Scenario Outline: Editar el alias de un contacto
    When cambio el alias del contacto "Prima Carla" a "<alias>"
    Then la operación es "<resultado>"

    Examples:
      | alias       | resultado       |
      | Carla       | exitosa         |
      | prima carla | exitosa         |
      | bruno       | ALIAS_DUPLICADO |
      | C           | ALIAS_INVALIDO  |
      | Carla#1     | ALIAS_INVALIDO  |

  @HU-G4-03 @api
  Scenario: Marcar un contacto como favorito
    When marco como favorito al contacto "Prima Carla"
    Then la respuesta es 200
    And la respuesta tiene "favorito" igual a "true"

  @HU-G4-04 @api
  Scenario: Eliminar un contacto sin solicitudes pendientes
    When elimino el contacto "Prima Carla"
    Then la respuesta es 204
    And mis contactos son "Bruno"

  @HU-G4-04 @api
  Scenario: No se elimina un contacto con solicitudes pendientes
    When elimino el contacto "Bruno"
    Then la respuesta es 409 con el código "SOLICITUDES_PENDIENTES"
    And mis contactos son "Bruno, Prima Carla"

  @HU-G4-06 @api
  Scenario: Solicitar dinero a un contacto
    When solicito S/ 25.50 a mi contacto "Prima Carla" por "Pizza del sábado"
    Then la respuesta es 201
    And la respuesta tiene "estado" igual a "PENDIENTE"
    And la respuesta tiene "monto" igual a "25.50"
    And la solicitud vence 48 horas después de creada
    And Carla recibe un SMS que contiene "te solicita S/ 25.50"

  @HU-G4-06 @api
  Scenario Outline: Solicitud de dinero rechazada
    When solicito S/ <monto> a mi contacto "Prima Carla" por "<motivo>"
    Then la respuesta es 422 con el código "SOLICITUD_INVALIDA"

    Examples:
      | monto  | motivo |
      | 0.00   | Pizza  |
      | 500.01 | Pizza  |
      | 10.00  | ab     |

  @HU-G4-06 @api
  Scenario: Máximo 10 solicitudes pendientes enviadas
    Given que ya tengo 10 solicitudes pendientes enviadas
    When solicito S/ 10.00 a mi contacto "Prima Carla" por "Una más"
    Then la respuesta es 422 con el código "LIMITE_SOLICITUDES"

  @HU-G4-07 @api
  Scenario: Ver mis solicitudes enviadas y recibidas
    When consulto mis solicitudes
    Then veo la solicitud enviada "Taxi al aeropuerto" en estado "PENDIENTE"
    And veo la solicitud recibida "Almuerzo del viernes" en estado "PENDIENTE"
    And veo la solicitud recibida "Entradas al cine" en estado "VENCIDA"

  @HU-G4-07 @api
  Scenario: Filtrar mis solicitudes por estado
    When consulto mis solicitudes en estado "VENCIDA"
    Then veo 0 solicitudes enviadas y 1 recibidas
    When consulto mis solicitudes en estado "PERDIDA"
    Then la respuesta es 422 con el código "FILTRO_INVALIDO"

  @HU-G4-08 @api
  Scenario: Aceptar una solicitud transfiere el monto al solicitante
    When acepto la solicitud "Almuerzo del viernes"
    Then la respuesta es 200
    And la respuesta tiene "estado" igual a "ACEPTADA"
    And la solicitud quedó asociada a un código de operación
    And mi saldo queda en S/ 1455.00
    And Bruno recibe un SMS que contiene "aceptó tu solicitud de S/ 45.00"
    When acepto la solicitud "Almuerzo del viernes"
    Then la respuesta es 409 con el código "ESTADO_INVALIDO"

  @HU-G4-08 @api
  Scenario: Si la transferencia falla la solicitud sigue pendiente
    Given que mi saldo es S/ 10.00
    When acepto la solicitud "Almuerzo del viernes"
    Then la respuesta es 422 con el código "SALDO_INSUFICIENTE"
    And veo la solicitud recibida "Almuerzo del viernes" en estado "PENDIENTE"

  @HU-G4-08 @api
  Scenario: Solo el destinatario acepta una solicitud
    When acepto la solicitud "Taxi al aeropuerto"
    Then la respuesta es 404 con el código "SOLICITUD_NO_ENCONTRADA"

  @HU-G4-09 @api
  Scenario: Rechazar una solicitud con motivo
    When rechazo la solicitud "Almuerzo del viernes" con el motivo "Ya te pagué"
    Then la respuesta es 200
    And la respuesta tiene "estado" igual a "RECHAZADA"
    And la respuesta tiene "motivo_rechazo" igual a "Ya te pagué"
    And Bruno recibe un SMS que contiene "rechazó tu solicitud de S/ 45.00: Ya te pagué"

  @HU-G4-09 @api
  Scenario Outline: Rechazo no permitido
    When rechazo la solicitud "<solicitud>" con un motivo de <n> caracteres
    Then la respuesta es <estado> con el código "<codigo>"

    Examples:
      | solicitud            | n  | estado | codigo             |
      | Almuerzo del viernes | 61 | 422    | SOLICITUD_INVALIDA |
      | Entradas al cine     | 5  | 409    | ESTADO_INVALIDO    |

  @HU-G4-10 @api
  Scenario: Cancelar una solicitud enviada
    When cancelo la solicitud "Taxi al aeropuerto"
    Then la respuesta es 200
    And la respuesta tiene "estado" igual a "CANCELADA"
    When cancelo la solicitud "Taxi al aeropuerto"
    Then la respuesta es 409 con el código "ESTADO_INVALIDO"

  @HU-G4-10 @api
  Scenario: Solo el solicitante cancela una solicitud
    When cancelo la solicitud "Almuerzo del viernes"
    Then la respuesta es 404 con el código "SOLICITUD_NO_ENCONTRADA"
