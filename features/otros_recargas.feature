# language: en
@fuera-de-alcance
Feature: Recargas de celular (G1, fuera de alcance)
  Como cliente
  Quiero recargar celulares y programar recargas mensuales
  Para no quedarme sin saldo en mi línea

  # Escenarios para la cobertura del SUT: camino feliz y errores principales, no un análisis EP/VL.
  # Datos: Ana (saldo S/ 1500.00) tiene una programada ACTIVA ("Mamá": 987111222, día 15, S/ 20)
  # y una PAUSADA ("Trabajo": 999000111, día 5, S/ 10).

  Background:
    Given que inicié sesión como Ana

  @HU-G1-01 @HU-G1-02 @api
  Scenario: Recarga de S/ 50 con bono de 5 %
    When recargo S/ 50 al celular 987111222
    Then la respuesta es 201
    And la respuesta tiene "bono" igual a "2.50"
    And la respuesta tiene "saldo" igual a "1450.00"
    And se envía al celular 987111222 un SMS que contiene "S/ 50.00 + bono de S/ 2.50"
    And mi última recarga es de S/ 50.00 al celular 987111222 con origen "MANUAL"
    And la configuración de recargas ofrece los montos "5, 10, 20, 30, 50, 100"

  @HU-G1-01 @api
  Scenario Outline: Recarga rechazada
    Given que mi saldo es S/ <saldo>
    When recargo S/ <monto> al celular <celular>
    Then la respuesta es 422 con el código "<codigo>"
    And no se persiste ningún cambio si la operación fue rechazada

    Examples:
      | saldo   | monto | celular   | codigo             |
      | 1500.00 | 15    | 987111222 | MONTO_NO_PERMITIDO |
      | 1500.00 | 10    | 812345678 | CELULAR_INVALIDO   |
      | 5.00    | 10    | 987111222 | SALDO_INSUFICIENTE |

  @HU-G1-03 @HU-G1-04 @api
  Scenario Outline: La próxima ejecución es este mes si el día aún no pasó
    Given que hoy es <hoy> en Lima
    When programo una recarga de S/ 20 al celular 987000111 el día <dia> con alias "Papá"
    Then la respuesta es 201
    And la respuesta tiene "estado" igual a "ACTIVA"
    And la respuesta tiene "proxima_ejecucion" igual a "<proxima>"
    And la respuesta tiene "ultimo_resultado" igual a "SIN_EJECUCIONES"
    And veo 3 recargas programadas

    Examples:
      | hoy        | dia | proxima    |
      | 2026-11-10 | 20  | 2026-11-20 |
      | 2026-11-10 | 10  | 2026-12-10 |
      | 2026-12-10 | 5   | 2027-01-05 |

  @HU-G1-03 @api
  Scenario Outline: Programación rechazada
    When programo una recarga de S/ <monto> al celular <celular> el día <dia> con alias "<alias>"
    Then la respuesta es <estado> con el código "<codigo>"
    And veo 2 recargas programadas

    Examples:
      | monto | celular   | dia | alias                 | estado | codigo                 |
      | 20    | 987000111 | 29  | Papá                  | 422    | PROGRAMACION_INVALIDA  |
      | 15    | 987000111 | 10  | Papá                  | 422    | PROGRAMACION_INVALIDA  |
      | 20    | 912345    | 10  | Papá                  | 422    | PROGRAMACION_INVALIDA  |
      | 20    | 987000111 | 10  | Alias de 21 letras xx | 422    | PROGRAMACION_INVALIDA  |
      | 20    | 987111222 | 15  | Mamá                  | 409    | PROGRAMACION_DUPLICADA |

  @HU-G1-03 @api
  Scenario: Máximo 3 recargas programadas activas
    Given que ya tengo 3 recargas programadas activas
    When programo una recarga de S/ 20 al celular 987000111 el día 10 con alias "Papá"
    Then la respuesta es 422 con el código "LIMITE_PROGRAMADAS"

  @HU-G1-05 @api
  Scenario: Editar, pausar y reanudar una programada
    Given que hoy es 2026-11-10 en Lima
    When cambio la programada "Mamá" a S/ 30, el día 25 y el alias "Mamá celular"
    Then la respuesta es 200
    And la respuesta tiene "monto" igual a "30.00"
    And la respuesta tiene "proxima_ejecucion" igual a "2026-11-25"
    When pauso la programada "Mamá celular"
    Then la respuesta tiene "estado" igual a "PAUSADA"
    When pauso la programada "Mamá celular"
    Then la respuesta es 409 con el código "ESTADO_INVALIDO"
    When reanudo la programada "Mamá celular"
    Then la respuesta tiene "estado" igual a "ACTIVA"
    When reanudo la programada "Mamá celular"
    Then la respuesta es 409 con el código "ESTADO_INVALIDO"

  @HU-G1-05 @api
  Scenario: El cambio de una programada valida el día
    When cambio el día de la programada "Mamá" al 0
    Then la respuesta es 422 con el código "PROGRAMACION_INVALIDA"

  @HU-G1-06 @api
  Scenario: Eliminar una programada
    When elimino la programada "Trabajo"
    Then la respuesta es 204
    And veo 1 recargas programadas
    When pauso la programada eliminada
    Then la respuesta es 404 con el código "PROGRAMADA_NO_ENCONTRADA"

  @HU-G1-07 @api
  Scenario: El proceso diario ejecuta la programada que vence hoy una sola vez
    Given que hoy es la próxima ejecución de la programada "Mamá"
    When se ejecuta el proceso diario
    And se ejecuta el proceso diario
    Then la programada "Mamá" quedó "EXITOSA" y su próxima ejecución pasó al mes siguiente
    And mi última recarga es de S/ 20.00 al celular 987111222 con origen "PROGRAMADA"
    And las recargas de hoy al celular 987111222 son 1

  @HU-G1-07 @api
  Scenario: Sin saldo la ejecución queda FALLIDA y se avisa al titular
    Given que mi saldo es S/ 5.00
    And que hoy es la próxima ejecución de la programada "Mamá"
    When se ejecuta el proceso diario
    Then la programada "Mamá" quedó "FALLIDA" y su próxima ejecución pasó al mes siguiente
    And Ana recibe un SMS que contiene "No pudimos realizar tu recarga programada"
    And las recargas de hoy al celular 987111222 son 0
