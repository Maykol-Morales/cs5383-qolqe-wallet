# language: en
@nucleo
Feature: Transferencias
  Como cliente
  Quiero enviar dinero a otro usuario Qolqe o a otro banco
  Para pagar de inmediato

  Background:
    Given que inicié sesión como Ana

  @HU-N-07 @api
  Scenario: Transferencia exitosa a un usuario registrado
    When transfiero S/ 100.00 al celular 912345678
    Then la respuesta es 201
    And el comprobante muestra monto S/ 100.00, comisión S/ 0.00, total S/ 100.00 y mi nuevo saldo S/ 1400.00
    And el destinatario del comprobante es "Bruno D." con celular 912345678
    And mi saldo es S/ 1400.00
    And Bruno y yo vemos el mismo código de operación en el historial
    And Bruno recibe un SMS que contiene "100.00"

  @HU-N-07 @api
  Scenario: El saldo del destinatario aumenta
    When transfiero S/ 100.00 al celular 912345678
    Then el saldo de Bruno es S/ 900.00

  @HU-N-07 @api
  Scenario Outline: Validación del monto por operación
    When intento transferir S/ <monto> al celular 912345678
    Then la operación es "<resultado>"

    Examples:
      | monto  | resultado      |
      | 0.00   | MONTO_INVALIDO |
      | -1.00  | MONTO_INVALIDO |
      | 0.01   | exitosa        |
      | 500.00 | exitosa        |
      | 500.01 | MONTO_INVALIDO |
      | 10.005 | MONTO_INVALIDO |
      | 10.50  | exitosa        |
      | 100.50 | exitosa        |
      | -10.00 | MONTO_INVALIDO |
      | 600.00 | MONTO_INVALIDO |

  @HU-N-07 @api
  Scenario: Descripción de hasta 60 caracteres
    When transfiero S/ 10.00 al celular 912345678 con una descripción de 61 caracteres
    Then la respuesta es 422 con el código "SOLICITUD_INVALIDA"

  @HU-N-07 @api
  Scenario: Descripción de exactamente 60 caracteres
    When transfiero S/ 10.00 al celular 912345678 con una descripción de 60 caracteres
    Then la respuesta es 201

  @HU-N-07 @api
  Scenario: No se puede transferir a uno mismo
    When intento transferir S/ 10.00 al celular 987654321
    Then la respuesta es 422 con el código "TRANSFERENCIA_A_SI_MISMO"

  @HU-N-07 @api
  Scenario: No se puede transferir a un celular no registrado
    When intento transferir S/ 10.00 al celular 999999999
    Then la respuesta es 404 con el código "DESTINO_NO_REGISTRADO"

  @HU-N-07 @api @DEF-06
  Scenario: No se puede transferir a una cuenta cerrada
    When intento transferir S/ 10.00 al celular 934567812
    Then la respuesta es 422 con el código "DESTINO_INACTIVO"

  @HU-N-08 @api
  Scenario Outline: El saldo debe cubrir el monto más la comisión interbancaria
    Given que inicié sesión como Carla
    And que mi saldo es S/ 50.00
    When intento transferir S/ <monto> al CCI 00219300123456789012
    Then la operación es "<resultado>"

    Examples:
      | monto | resultado          |
      | 49.00 | exitosa            |
      | 60.00 | SALDO_INSUFICIENTE |

  @HU-N-08 @api @DEF-04
  Scenario: La comisión también debe estar cubierta por el saldo (límite exacto)
    Given que inicié sesión como Carla
    And que mi saldo es S/ 50.00
    When intento transferir S/ 49.01 al CCI 00219300123456789012
    Then la respuesta es 422 con el código "SALDO_INSUFICIENTE"
    And mi saldo es S/ 50.00

  @HU-N-07 @api
  Scenario Outline: El saldo nunca queda negativo en transferencias entre cuentas Qolqe
    Given que inicié sesión como Carla
    And que mi saldo es S/ 50.00
    When intento transferir S/ <monto> al celular 912345678
    Then la operación es "<resultado>"
    And mi saldo es S/ <saldo_final>

    Examples:
      | monto | resultado          | saldo_final |
      | 50.00 | exitosa            | 0.00        |
      | 49.99 | exitosa            | 0.01        |
      | 50.01 | SALDO_INSUFICIENTE | 50.00       |

  @HU-N-07 @api
  Scenario: El límite diario de S/ 1000.00 de Diego se respeta
    Given que inicié sesión como Diego
    And que ya transferí S/ 500.00 al celular 912345678
    And que ya transferí S/ 500.00 al celular 912345678
    When intento transferir S/ 0.01 al celular 912345678
    Then la respuesta es 422 con el código "LIMITE_DIARIO_EXCEDIDO"

  @HU-N-07 @api
  Scenario: Una transferencia que alcanza exactamente el límite diario es válida
    Given que inicié sesión como Diego
    And que ya transferí S/ 500.00 al celular 912345678
    When intento transferir S/ 500.00 al celular 912345678
    Then la operación es "exitosa"

  # Pertenece a la Parte 3 (rendimiento): se omite con skip y sus pasos se implementarán allí.
  @HU-N-07 @concurrencia
  Scenario: Transferencias simultáneas no superan el límite diario ni dejan el saldo negativo
    Given que inicié sesión como Carla
    And que mi saldo es S/ 50.00
    When envío 10 transferencias simultáneas de S/ 10.00
    Then mi saldo no es negativo

  @HU-N-08 @api
  Scenario Outline: Comisión interbancaria de 1.5 % con mínimo S/ 1.00 y máximo S/ 5.00
    When intento transferir S/ <monto> al CCI 00219300123456789012
    Then la comisión es S/ <comision> y el total S/ <total>

    Examples:
      | monto  | comision | total  |
      | 0.01   | 1.00     | 1.01   |
      | 10.00  | 1.00     | 11.00  |
      | 66.00  | 1.00     | 67.00  |
      | 100.00 | 1.50     | 101.50 |
      | 300.00 | 4.50     | 304.50 |
      | 332.99 | 4.99     | 337.98 |
      | 333.33 | 5.00     | 338.33 |
      | 400.00 | 5.00     | 405.00 |
      | 500.00 | 5.00     | 505.00 |
      | 66.99  | 1.00     | 67.99  |
      | 333.34 | 5.00     | 338.34 |

  @HU-N-08 @api @DEF-01
  Scenario Outline: La comisión usa redondeo comercial (0.005 sube)
    When intento transferir S/ <monto> al CCI 00219300123456789012
    Then la comisión es S/ <comision> y el total S/ <total>

    Examples:
      | monto  | comision | total  |
      | 67.00  | 1.01     | 68.01  |
      | 71.00  | 1.07     | 72.07  |

  @HU-N-08 @api
  Scenario Outline: Validación del CCI (20 dígitos)
    When intento transferir S/ 10.00 al CCI <cci>
    Then la operación es "<resultado>"

    Examples:
      | cci                   | resultado   |
      | 00219300123456789012  | exitosa     |
      | 0021930012345678901   | CCI_INVALIDO |
      | 002193001234567890123 | CCI_INVALIDO |
      | 0021930012345678901X  | CCI_INVALIDO |

  @HU-N-08 @api
  Scenario: El movimiento interbancario muestra solo los últimos 4 dígitos del CCI
    When transfiero S/ 100.00 al CCI 00219300123456789012
    Then la respuesta es 201
    And el comprobante muestra monto S/ 100.00, comisión S/ 1.50, total S/ 101.50 y mi nuevo saldo S/ 1398.50
    And el CCI del comprobante termina en "9012" y no revela el resto
    And el movimiento en mi historial y su detalle muestran el CCI terminado en "9012" sin revelar el resto

  @HU-N-09 @api
  Scenario Outline: Simulación de la comisión sin realizar ninguna operación
    When simulo una transferencia <tipo> de S/ 100.00
    Then veo comisión S/ <comision> y total S/ <total>
    And mi saldo es S/ 1500.00

    Examples:
      | tipo          | comision | total  |
      | QOLQE         | 0.00     | 100.00 |
      | INTERBANCARIA | 1.50     | 101.50 |

  @HU-N-09 @api
  Scenario: La simulación valida el monto
    When simulo una transferencia QOLQE de S/ 500.01
    Then la respuesta es 422 con el código "MONTO_INVALIDO"

  @HU-N-07 @api
  Scenario: El monto debe ser numérico
    When intento transferir S/ abc al celular 912345678
    Then la respuesta es 422 con el código "SOLICITUD_INVALIDA"

  @HU-N-07 @api
  Scenario: El monto es obligatorio
    When intento transferir sin monto al celular 912345678
    Then la respuesta es 422 con el código "SOLICITUD_INVALIDA"

  @HU-N-07 @api
  Scenario: Un acumulado un centavo bajo el límite diario es válido
    Given que inicié sesión como Diego
    And que ya transferí S/ 500.00 al celular 912345678
    And que ya transferí S/ 499.98 al celular 912345678
    When intento transferir S/ 0.01 al celular 912345678
    Then la operación es "exitosa"

  @HU-N-07 @api
  Scenario Outline: El límite diario se reinicia a medianoche de Lima
    Given que el reloj de Lima marca las 23:50:00 de hoy
    And que inicié sesión como Diego
    And que ya transferí S/ 500.00 al celular 912345678
    And que ya transferí S/ 500.00 al celular 912345678
    When el reloj de Lima marca las <hora> de <dia>
    And intento transferir S/ 0.01 al celular 912345678
    Then la operación es "<resultado>"

    Examples:
      | hora     | dia    | resultado              |
      | 23:59:59 | hoy    | LIMITE_DIARIO_EXCEDIDO |
      | 00:00:00 | mañana | exitosa                |

  @HU-N-08 @api
  Scenario: Con saldo igual al total de una interbancaria de S/ 100.00 la operación es válida
    Given que mi saldo es S/ 101.50
    When intento transferir S/ 100.00 al CCI 00219300123456789012
    Then la operación es "exitosa"
    And mi saldo es S/ 0.00

  @HU-N-08 @api @DEF-04
  Scenario Outline: Con saldo menor al total de una interbancaria de S/ 100.00 se rechaza
    Given que mi saldo es S/ <saldo>
    When intento transferir S/ 100.00 al CCI 00219300123456789012
    Then la respuesta es 422 con el código "SALDO_INSUFICIENTE"
    And mi saldo es S/ <saldo>

    Examples:
      | saldo  |
      | 101.49 |
      | 100.00 |

  @HU-N-09 @api
  Scenario: Un tipo de transferencia inexistente es rechazado
    When simulo una transferencia OTRO de S/ 100.00
    Then la respuesta es 422 con el código "SOLICITUD_INVALIDA"

  @HU-N-09 @api
  Scenario: Sin tipo la simulación se trata como transferencia entre cuentas Qolqe
    When simulo una transferencia de S/ 100.00 sin indicar el tipo
    Then veo comisión S/ 0.00 y total S/ 100.00

  @HU-N-08 @api
  Scenario Outline: El límite diario cuenta las transferencias interbancarias hasta el límite
    Given que inicié sesión como Diego
    And que ya transferí S/ 500.00 al CCI 00219300123456789012
    And que ya transferí S/ <segunda> al CCI 00219300123456789012
    When intento transferir S/ 0.01 al CCI 00219300123456789012
    Then la operación es "exitosa"

    Examples:
      | segunda |
      | 499.98  |
      | 499.99  |

  @HU-N-08 @api @DEF-13
  Scenario: Una interbancaria que supera el límite diario acumulado se rechaza
    Given que inicié sesión como Diego
    And que ya transferí S/ 500.00 al CCI 00219300123456789012
    And que ya transferí S/ 500.00 al CCI 00219300123456789012
    When intento transferir S/ 0.01 al CCI 00219300123456789012
    Then la respuesta es 422 con el código "LIMITE_DIARIO_EXCEDIDO"

  @HU-N-08 @api @DEF-13
  Scenario: Las interbancarias del día cuentan para el límite de una transferencia a Qolqe
    Given que inicié sesión como Diego
    And que ya transferí S/ 500.00 al CCI 00219300123456789012
    And que ya transferí S/ 500.00 al CCI 00219300123456789012
    When intento transferir S/ 0.01 al celular 912345678
    Then la respuesta es 422 con el código "LIMITE_DIARIO_EXCEDIDO"

  @HU-N-08 @api
  Scenario: Las transferencias a Qolqe del día cuentan para el límite de una interbancaria
    Given que inicié sesión como Diego
    And que ya transferí S/ 500.00 al celular 912345678
    And que ya transferí S/ 500.00 al celular 912345678
    When intento transferir S/ 0.01 al CCI 00219300123456789012
    Then la respuesta es 422 con el código "LIMITE_DIARIO_EXCEDIDO"

  @HU-N-07 @api @DEF-12
  Scenario: Dos transferencias en el mismo segundo tienen códigos de operación distintos
    Given que el reloj de Lima marca las 10:00:00 de hoy
    And que inicié sesión como Ana
    When transfiero S/ 1.00 al celular 912345678
    And transfiero S/ 2.00 al celular 912345678
    Then las dos últimas operaciones tienen códigos de operación distintos
