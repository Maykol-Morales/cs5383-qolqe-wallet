# language: en
@fuera-de-alcance
Feature: Pago de servicios (G2, fuera de alcance)
  Como cliente
  Quiero consultar y pagar mis servicios, y afiliarlos con débito automático
  Para no atrasarme con los recibos

  # Escenarios para la cobertura del SUT: camino feliz y errores principales, no un análisis EP/VL.
  # Datos: Ana tiene afiliados "Luz casa" (ELECTRO 10000001, deuda de S/ 120.00 que vence en 10 días),
  # "Agua depa" (AGUA 2000000008, con débito automático, vence en 3 días) e "Internet casa"
  # (INTERNET 300000000007, 61 días de atraso: en cobranza).

  Background:
    Given que inicié sesión como Ana

  @HU-G2-01 @api
  Scenario: Consultar las deudas pendientes de un suministro
    When consulto las deudas de ELECTRO con el suministro 100000009
    Then la respuesta es 200
    And veo 2 deudas de la más antigua a la más reciente con titular "Diego S."
    And la deuda que aún no vence no tiene mora
    And las empresas de servicios son "AGUA, ELECTRO, INTERNET"

  @HU-G2-01 @api
  Scenario Outline: Consulta de deudas rechazada
    When consulto las deudas de <empresa> con el suministro <suministro>
    Then la respuesta es <estado> con el código "<codigo>"

    Examples:
      | empresa | suministro | estado | codigo                |
      | GAS     | 10000001   | 404    | EMPRESA_NO_ENCONTRADA |
      | ELECTRO | 1234567    | 422    | SUMINISTRO_INVALIDO   |
      | ELECTRO | 1000000A   | 422    | SUMINISTRO_INVALIDO   |
      | ELECTRO | 12345678   | 404    | SIN_DEUDA_PENDIENTE   |

  @HU-G2-02 @HU-G2-04 @HU-G2-07 @api
  Scenario: Pagar una deuda que aún no vence
    When pago la deuda de ELECTRO con el suministro 10000001
    Then la respuesta es 201
    And la respuesta tiene "mora" igual a "0.00"
    And la respuesta tiene "total" igual a "120.00"
    And la respuesta tiene "saldo" igual a "1380.00"
    And mi saldo queda en S/ 1380.00
    And el pago aparece en mis pagos y en los de la afiliación "Luz casa"
    And veo el comprobante del pago, pero Bruno no
    And la afiliación "Luz casa" está en situación "AL_DIA"

  @HU-G2-02 @api
  Scenario: No se paga dos veces la misma deuda
    Given que pagué la deuda de ELECTRO con el suministro 10000001
    When pago otra vez la misma deuda
    Then la respuesta es 409 con el código "DEUDA_YA_PAGADA"

  @HU-G2-02 @api
  Scenario: Una deuda en cobranza no se paga en Qolqe
    When pago la deuda de INTERNET con el suministro 300000000007
    Then la respuesta es 422 con el código "DEUDA_EN_COBRANZA"
    And no se persiste ningún cambio si la operación fue rechazada

  @HU-G2-02 @api
  Scenario: Sin saldo no se paga la deuda
    Given que mi saldo es S/ 10.00
    When pago la deuda de ELECTRO con el suministro 10000001
    Then la respuesta es 422 con el código "SALDO_INSUFICIENTE"
    And no se persiste ningún cambio si la operación fue rechazada

  @HU-G2-02 @api
  Scenario: Deuda inexistente
    When pago la deuda número 999999
    Then la respuesta es 404 con el código "DEUDA_NO_ENCONTRADA"

  @HU-G2-03 @HU-G2-04 @api
  Scenario: Afiliar un servicio con el débito automático desactivado
    When afilio el suministro 10000002 de ELECTRO con alias "Luz oficina"
    Then la respuesta es 201
    And la respuesta tiene "debito_automatico" igual a "false"
    And la respuesta tiene "situacion" igual a "CON_DEUDA"
    And la afiliación "Agua depa" está en situación "CON_DEUDA"
    And la afiliación "Internet casa" está en situación "EN_COBRANZA"

  @HU-G2-03 @api
  Scenario Outline: Afiliación rechazada
    When afilio el suministro <suministro> de <empresa> con alias "<alias>"
    Then la respuesta es <estado> con el código "<codigo>"

    Examples:
      | empresa | suministro | alias       | estado | codigo                   |
      | ELECTRO | 10000001   | Luz otra    | 409    | AFILIACION_DUPLICADA     |
      | ELECTRO | 10000002   | ab          | 422    | AFILIACION_INVALIDA      |
      | ELECTRO | 1234       | Luz oficina | 422    | AFILIACION_INVALIDA      |
      | ELECTRO | 99999999   | Luz oficina | 404    | SUMINISTRO_NO_ENCONTRADO |
      | GAS     | 10000002   | Gas casa    | 404    | EMPRESA_NO_ENCONTRADA    |

  @HU-G2-03 @api
  Scenario: Máximo 8 servicios afiliados
    Given que ya tengo 8 servicios afiliados
    When afilio el suministro 4000000009 de AGUA con alias "Agua nueve"
    Then la respuesta es 422 con el código "LIMITE_AFILIACIONES"

  @HU-G2-05 @api
  Scenario: Renombrar una afiliación y activar su débito automático
    When cambio la afiliación "Luz casa" al alias "Luz depa" con el débito automático activado
    Then la respuesta es 200
    And la respuesta tiene "alias" igual a "Luz depa"
    And la respuesta tiene "debito_automatico" igual a "true"
    And Ana recibe un SMS que contiene "Débito automático activado para Luz depa"

  @HU-G2-05 @api
  Scenario: El débito automático paga la deuda el día de su vencimiento, sin mora
    Given que hoy es el vencimiento de la deuda de AGUA con el suministro 2000000008
    When se ejecuta el proceso diario
    Then la respuesta tiene "debitos_pagados" igual a "1"
    And mi último pago es del suministro 2000000008 con origen "DEBITO_AUTOMATICO" y mora "0.00"

  @HU-G2-05 @api
  Scenario: Sin saldo el débito automático no paga y avisa al titular
    Given que mi saldo es S/ 5.00
    And que hoy es el vencimiento de la deuda de AGUA con el suministro 2000000008
    When se ejecuta el proceso diario
    Then la respuesta tiene "debitos_fallidos" igual a "1"
    And Ana recibe un SMS que contiene "No pudimos pagar con débito automático Agua depa"

  @HU-G2-06 @api
  Scenario: Desafiliar un servicio
    When desafilio el servicio "Luz casa"
    Then la respuesta es 204
    And no tengo afiliado el servicio "Luz casa"

  @HU-G2-06 @api
  Scenario: No se desafilia un servicio con el débito automático activo
    When desafilio el servicio "Agua depa"
    Then la respuesta es 409 con el código "DEBITO_ACTIVO"
