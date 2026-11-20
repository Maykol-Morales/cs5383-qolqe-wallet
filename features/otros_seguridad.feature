# language: en
@fuera-de-alcance
Feature: Seguridad (G6, fuera de alcance)
  Como cliente
  Quiero administrar mi PIN, mis dispositivos y mis sesiones
  Para proteger mi cuenta

  # Escenarios para la cobertura del SUT: camino feliz y errores principales, no un análisis EP/VL.
  # Datos: Ana (PIN 4826, anteriores 2468 y 1357) tiene el dispositivo "Celular de Ana";
  # Elena (923456789) está bloqueada.

  @HU-G6-01 @api
  Scenario: Cambiar mi PIN
    Given que inicié sesión como Ana
    When cambio mi PIN de "4826" a "7305"
    Then la respuesta es 200
    And Ana recibe un SMS que contiene "Tu PIN de Qolqe fue cambiado"
    And puedo iniciar sesión con el celular 987654321 y el PIN "7305", pero no con "4826"

  @HU-G6-01 @api
  Scenario Outline: Cambio de PIN rechazado
    Given que inicié sesión como <quien>
    When cambio mi PIN de "<actual>" a "<nuevo>"
    Then la respuesta es 422 con el código "<codigo>"

    Examples:
      | quien | actual | nuevo | codigo                |
      | Ana   | 0000   | 7305  | PIN_ACTUAL_INCORRECTO |
      | Ana   | 4826   | 1111  | PIN_INVALIDO          |
      | Ana   | 4826   | 1234  | PIN_INVALIDO          |
      | Diego | 3604   | 7665  | PIN_INVALIDO          |
      | Ana   | 4826   | 4826  | PIN_REUTILIZADO       |
      | Ana   | 4826   | 2468  | PIN_REUTILIZADO       |

  @HU-G6-03 @HU-G6-04 @api
  Scenario: Desbloquear la cuenta con el código del SMS
    When solicito un código de desbloqueo para el celular 923456789
    Then la respuesta es 202
    And se envía al celular 923456789 un SMS que contiene "Tu código de desbloqueo Qolqe es"
    When confirmo el desbloqueo del celular 923456789 con el código del SMS
    Then la respuesta es 200
    And Elena puede iniciar sesión

  @HU-G6-03 @api
  Scenario: La respuesta no revela si la cuenta existe o está bloqueada
    When solicito un código de desbloqueo para el celular 911111111
    And solicito un código de desbloqueo para el celular 987654321
    And solicito un código de desbloqueo para el celular 923456789
    Then las tres respuestas son 202 con el mismo mensaje

  @HU-G6-04 @api
  Scenario: El código se anula al tercer intento fallido
    Given que solicité un código de desbloqueo para el celular 923456789
    When confirmo el desbloqueo del celular 923456789 con un código incorrecto
    Then la respuesta es 422 con el código "CODIGO_INCORRECTO"
    And el mensaje indica que quedan 2 intentos
    When confirmo el desbloqueo del celular 923456789 con un código incorrecto
    And confirmo el desbloqueo del celular 923456789 con un código incorrecto
    Then la respuesta es 422 con el código "CODIGO_ANULADO"
    When confirmo el desbloqueo del celular 923456789 con el código del SMS
    Then la respuesta es 422 con el código "CODIGO_INVALIDO"

  @HU-G6-04 @api
  Scenario: El código vence a los 5 minutos
    Given que solicité un código de desbloqueo para el celular 923456789
    When han pasado 5 minutos desde que pedí el código
    And confirmo el desbloqueo del celular 923456789 con el código del SMS
    Then la respuesta es 422 con el código "CODIGO_EXPIRADO"

  @HU-G6-04 @api
  Scenario: Sin código activo no se desbloquea
    When confirmo el desbloqueo del celular 912345678 con el código "123456"
    Then la respuesta es 422 con el código "CODIGO_INVALIDO"

  @HU-G6-05 @HU-G6-06 @api
  Scenario: Registrar un dispositivo de confianza
    Given que inicié sesión como Ana
    When registro el dispositivo "Tablet de Ana" de tipo TABLET con el PIN "4826"
    Then la respuesta es 201
    And la respuesta tiene "tipo" igual a "TABLET"
    And el dispositivo tiene un identificador para el inicio de sesión
    And mis dispositivos son "Celular de Ana, Tablet de Ana"
    And Ana recibe un SMS que contiene "Registraste el dispositivo de confianza"

  @HU-G6-05 @api
  Scenario Outline: Registro de dispositivo rechazado
    Given que inicié sesión como Ana
    When registro el dispositivo "<nombre>" de tipo <tipo> con el PIN "<pin>"
    Then la respuesta es <estado> con el código "<codigo>"
    And mis dispositivos son "Celular de Ana"

    Examples:
      | nombre         | tipo    | pin  | estado | codigo                |
      | Ta             | TABLET  | 4826 | 422    | DISPOSITIVO_INVALIDO  |
      | Reloj de Ana   | RELOJ   | 4826 | 422    | DISPOSITIVO_INVALIDO  |
      | Tablet de Ana  | TABLET  | 0000 | 422    | PIN_INCORRECTO        |
      | celular de ana | CELULAR | 4826 | 409    | DISPOSITIVO_DUPLICADO |

  @HU-G6-05 @api
  Scenario: Máximo 3 dispositivos de confianza
    Given que inicié sesión como Ana
    And que registré los dispositivos "Tablet de Ana" y "Laptop de Ana"
    When registro el dispositivo "Otro de Ana" de tipo CELULAR con el PIN "4826"
    Then la respuesta es 422 con el código "LIMITE_DISPOSITIVOS"

  @HU-G6-07 @api
  Scenario Outline: Renombrar un dispositivo
    Given que inicié sesión como Ana
    And que registré los dispositivos "Tablet de Ana" y "Laptop de Ana"
    When renombro el dispositivo "Celular de Ana" a "<nombre>"
    Then la operación es "<resultado>"

    Examples:
      | nombre           | resultado             |
      | Celular personal | exitosa               |
      | CELULAR DE ANA   | exitosa               |
      | tablet de ana    | DISPOSITIVO_DUPLICADO |
      | Ce               | DISPOSITIVO_INVALIDO  |

  @HU-G6-08 @api
  Scenario: Eliminar un dispositivo
    Given que inicié sesión como Ana
    When elimino el dispositivo "Celular de Ana"
    Then la respuesta es 204
    And ya no tengo dispositivos de confianza
    And si inicio sesión desde el dispositivo eliminado recibo la alerta de nuevo dispositivo

  @HU-G6-09 @HU-G6-10 @api
  Scenario: Ver y cerrar una sesión específica
    Given que inicié sesión como Ana
    And que también inicié sesión como Ana en otro dispositivo
    When consulto mis sesiones
    Then veo 2 sesiones y solo una es la actual
    When cierro mi otra sesión
    Then la respuesta es 204
    And mi otra sesión ya no es válida
    And mi sesión actual sigue siendo válida

  @HU-G6-10 @api
  Scenario: Cerrar todas mis sesiones excepto la actual
    Given que inicié sesión como Ana
    And que también inicié sesión como Ana en otro dispositivo
    When cierro todas mis otras sesiones
    Then la respuesta tiene "sesiones_cerradas" igual a "1"
    And mi otra sesión ya no es válida
    And mi sesión actual sigue siendo válida

  @HU-G6-10 @api
  Scenario: No puedo cerrar la sesión de otro usuario
    Given que inicié sesión como Ana
    When Bruno intenta cerrar mi sesión
    Then la respuesta es 404 con el código "SESION_NO_ENCONTRADA"
    And mi sesión actual sigue siendo válida
