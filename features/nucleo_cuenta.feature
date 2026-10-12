# language: en
@nucleo
Feature: Mi cuenta: saldo, perfil y cierre
  Como cliente
  Quiero consultar y administrar mi cuenta
  Para mantener mis datos al día y dejar de usar Qolqe cuando quiera

  Background:
    Given que inicié sesión como Ana

  @HU-N-04 @api
  Scenario: Consulta de saldo
    When consulto mi saldo
    Then mi saldo es S/ 1500.00
    And la moneda es "PEN" y se indica la fecha de la última actualización

  @HU-N-04 @api
  Scenario: Consulta de perfil con DNI enmascarado
    When consulto mi perfil
    Then veo mis nombres "Ana Torres Quispe", mi celular "987654321" y mi correo "ana.torres@correo.pe"
    And el DNI se muestra como "****8912"

  @HU-N-04 @api
  Scenario Outline: Consulta sin una sesión válida
    When consulto mi saldo <situacion>
    Then la respuesta es 401 con el código "NO_AUTENTICADO"

    Examples:
      | situacion                 |
      | sin token                 |
      | con un token inválido     |
      | con un token vencido      |

  @HU-N-05 @api
  Scenario Outline: Longitud de los nombres (2 a 80 caracteres)
    When cambio mis nombres por un texto de <n> caracteres
    Then la operación es "<resultado>"

    Examples:
      | n  | resultado      |
      | 1  | PERFIL_INVALIDO |
      | 2  | exitosa        |
      | 80 | exitosa        |
      | 81 | PERFIL_INVALIDO |

  @HU-N-05 @api
  Scenario Outline: Cambio de correo
    When cambio mi correo por "<correo>"
    Then la operación es "<resultado>"

    Examples:
      | correo                 | resultado         |
      | nuevo.ana@correo.pe    | exitosa           |
      | nuevo.ana              | CORREO_INVALIDO   |
      | bruno.diaz@correo.pe   | CORREO_REGISTRADO |
      | BRUNO.DIAZ@CORREO.PE   | CORREO_REGISTRADO |
      | ANA.TORRES@correo.pe   | exitosa           |

  @HU-N-05 @api
  Scenario: El DNI y el celular no se pueden modificar
    When envío un cambio de perfil con el DNI "11111111" y el celular "900000000"
    And consulto mi perfil
    Then el DNI se muestra como "****8912"
    And veo mis nombres "Ana Torres Quispe", mi celular "987654321" y mi correo "ana.torres@correo.pe"

  @HU-N-05 @api
  Scenario: Al cambiar el correo se envía un SMS de aviso
    When cambio mi correo por "nuevo.ana@correo.pe"
    Then Ana recibe un SMS que contiene "correo"

  @HU-N-06 @api
  Scenario: Cierre con PIN incorrecto
    When cierro mi cuenta con el PIN "1111"
    Then la respuesta es 422 con el código "PIN_INCORRECTO"

  @HU-N-06 @api
  Scenario Outline: Solo se cierra con saldo exactamente S/ 0.00
    Given que mi saldo es S/ <saldo>
    When cierro mi cuenta con el PIN "4826"
    Then la operación es "<resultado>"

    Examples:
      | saldo   | resultado        |
      | 0.01    | SALDO_PENDIENTE  |
      | 1500.00 | SALDO_PENDIENTE  |

  @HU-N-06 @api
  Scenario: No se puede cerrar con solicitudes de dinero pendientes
    Given que mi saldo es S/ 0.00
    When cierro mi cuenta con el PIN "4826"
    Then la respuesta es 409 con el código "SOLICITUDES_PENDIENTES"

  @HU-N-06 @api
  Scenario: Cierre exitoso: no puedo volver a ingresar
    Given que inicié sesión como Diego
    And que mi saldo es S/ 0.00
    When cierro mi cuenta con el PIN "3604"
    Then la respuesta es 204
    And Diego no puede iniciar sesión por "CUENTA_CERRADA"

  @HU-N-06 @api
  Scenario: Cierre exitoso: mis sesiones se cierran
    Given que inicié sesión como Diego
    And que mi saldo es S/ 0.00
    When cierro mi cuenta con el PIN "3604"
    Then mi sesión anterior ya no es válida

  @HU-N-06 @api @DEF-06
  Scenario: Cierre exitoso: nadie puede transferirme
    Given que inicié sesión como Diego
    And que mi saldo es S/ 0.00
    When cierro mi cuenta con el PIN "3604"
    Then Ana no puede transferir S/ 10.00 al celular 998877665 por "DESTINO_INACTIVO"
