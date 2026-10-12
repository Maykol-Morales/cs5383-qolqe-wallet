# language: en
@nucleo
Feature: Registrarme
  Como visitante
  Quiero crear una cuenta con mi DNI y celular
  Para usar la billetera

  @HU-N-01 @api
  Scenario: Registro exitoso con saldo y límite diario iniciales
    When me registro con DNI "45678912" y el resto de datos válidos
    Then la respuesta es 201
    And la cuenta nueva tiene saldo S/ 0.00 y límite diario de S/ 2000.00

  @HU-N-01 @api
  Scenario: Se envía un SMS de bienvenida
    When me registro con DNI "45678912" y el resto de datos válidos
    Then se envía al celular 987000111 un SMS que contiene "Qolqe"

  @HU-N-01 @api
  Scenario Outline: Validación del DNI (8 dígitos numéricos)
    When me registro con DNI "<dni>" y el resto de datos válidos
    Then la operación es "<resultado>"

    Examples:
      | dni       | resultado   |
      | 45678912  | exitosa     |
      | 4567891   | DNI_INVALIDO |
      | 456789123 | DNI_INVALIDO |
      | 4567891A  | DNI_INVALIDO |
      | 00000000  | exitosa     |

  @HU-N-01 @api
  Scenario Outline: Validación del celular (9 dígitos y empieza con 9)
    When me registro con celular "<celular>" y el resto de datos válidos
    Then la operación es "<resultado>"

    Examples:
      | celular    | resultado         |
      | 987000111  | exitosa           |
      | 98700011   | CELULAR_INVALIDO  |
      | 9870001112 | CELULAR_INVALIDO  |
      | 887000111  | CELULAR_INVALIDO  |
      | 98700011X  | CELULAR_INVALIDO  |

  @HU-N-01 @api
  Scenario Outline: Un celular ya registrado, incluso con cuenta cerrada, no se puede reutilizar
    When me registro con celular "<celular>" y el resto de datos válidos
    Then la respuesta es 409 con el código "CELULAR_REGISTRADO"

    Examples:
      | celular   |
      | 987654321 |
      | 934567812 |

  @HU-N-01 @api
  Scenario Outline: Validación del PIN (4 dígitos, sin repetidos ni secuencias)
    When me registro con PIN "<pin>" y el resto de datos válidos
    Then la operación es "<resultado>"

    Examples:
      | pin   | resultado   |
      | 4826  | exitosa     |
      | 482   | PIN_INVALIDO |
      | 48261 | PIN_INVALIDO |
      | 48A6  | PIN_INVALIDO |
      | 1111  | PIN_INVALIDO |
      | 0000  | PIN_INVALIDO |
      | 1234  | PIN_INVALIDO |
      | 0123  | PIN_INVALIDO |
      | 6789  | PIN_INVALIDO |

  @HU-N-01 @api @DEF-02
  Scenario Outline: Un PIN con secuencia descendente es rechazado
    When me registro con PIN "<pin>" y el resto de datos válidos
    Then la operación es "PIN_INVALIDO"

    Examples:
      | pin  |
      | 4321 |
      | 9876 |
      | 3210 |

  @HU-N-01 @api
  Scenario Outline: Validación del correo
    When me registro con correo "<correo>" y el resto de datos válidos
    Then la operación es "<resultado>"

    Examples:
      | correo                | resultado         |
      | lucia@correo.pe       | exitosa           |
      | lucia.correo.pe       | CORREO_INVALIDO   |
      | lucia@                | CORREO_INVALIDO   |
      | ana.torres@correo.pe  | CORREO_REGISTRADO |
      | ANA.TORRES@CORREO.PE  | CORREO_REGISTRADO |
