# language: en
@fuera-de-alcance
Feature: Límites y alertas de consumo (G5, fuera de alcance)
  Como cliente
  Quiero ajustar mi límite diario y recibir alertas de consumo
  Para controlar mis gastos

  # Escenarios para la cobertura del SUT: camino feliz y errores principales, no un análisis EP/VL.
  # Datos: Ana tiene límite diario de S/ 2000.00, una alerta ACTIVA de TRANSFERENCIAS con umbral
  # S/ 300.00 y hoy ya recargó S/ 10.00.

  Background:
    Given que inicié sesión como Ana

  @HU-G5-01 @api
  Scenario: Ver mis límites y lo usado hoy
    Given que ya transferí S/ 100.00 a Bruno
    When consulto mis límites
    Then la respuesta tiene "limite_por_operacion" igual a "500.00"
    And la respuesta tiene "limite_diario" igual a "2000.00"
    And la respuesta tiene "usado_hoy" igual a "100.00"
    And la respuesta tiene "disponible_hoy" igual a "1900.00"

  @HU-G5-02 @api
  Scenario: Una reducción del límite es inmediata
    When cambio mi límite diario a S/ 1000
    Then la respuesta es 200
    And la respuesta tiene "aplicacion" igual a "INMEDIATA"
    And la respuesta tiene "limite_diario" igual a "1000.00"
    And Ana recibe un SMS que contiene "Tu límite diario ahora es S/ 1000"

  @HU-G5-02 @api
  Scenario: Un aumento del límite entra en vigencia 24 horas después
    Given que mi límite diario es S/ 1000
    When cambio mi límite diario a S/ 1500
    Then la respuesta tiene "aplicacion" igual a "PROGRAMADA"
    And la respuesta tiene "limite_diario" igual a "1000.00"
    And la respuesta tiene "limite_pendiente" igual a "1500.00"
    And Ana recibe un SMS que contiene "estará vigente desde"
    When pasan 24 horas y vuelvo a iniciar sesión
    And consulto mis límites
    Then la respuesta tiene "limite_diario" igual a "1500.00"

  @HU-G5-02 @api
  Scenario Outline: Límite diario fuera de rango o no múltiplo de S/ 50
    When cambio mi límite diario a S/ <limite>
    Then la respuesta es 422 con el código "LIMITE_INVALIDO"

    Examples:
      | limite |
      | 50     |
      | 2050   |
      | 120    |

  @HU-G5-02 @api
  Scenario: Una reducción por debajo del umbral pausa la alerta de transferencias
    When cambio mi límite diario a S/ 250
    Then la alerta de TRANSFERENCIAS está "PAUSADA"

  @HU-G5-04 @HU-G5-05 @api
  Scenario: Crear una alerta de consumo
    When creo una alerta de RECARGAS con umbral S/ 50
    Then la respuesta es 201
    And la respuesta tiene "estado" igual a "ACTIVA"
    And la respuesta tiene "gasto_hoy" igual a "10.00"
    And tengo 2 alertas

  @HU-G5-04 @api
  Scenario Outline: Alerta rechazada
    When creo una alerta de <tipo> con umbral S/ <umbral>
    Then la respuesta es <estado> con el código "<codigo>"
    And tengo 1 alertas

    Examples:
      | tipo           | umbral | estado | codigo           |
      | TRANSFERENCIAS | 300    | 409    | ALERTA_DUPLICADA |
      | RECARGAS       | 5      | 422    | ALERTA_INVALIDA  |
      | RECARGAS       | 15     | 422    | ALERTA_INVALIDA  |
      | VIAJES         | 50     | 422    | ALERTA_INVALIDA  |

  @HU-G5-04 @api
  Scenario: El umbral de transferencias no supera el límite diario vigente
    Given que mi límite diario es S/ 1000
    When creo una alerta de TODAS con umbral S/ 1500
    Then la respuesta es 422 con el código "ALERTA_INVALIDA"

  @HU-G5-04 @api
  Scenario: Máximo 5 alertas
    Given que ya tengo 5 alertas
    When creo una alerta de PAGOS con umbral S/ 990
    Then la respuesta es 422 con el código "LIMITE_ALERTAS"

  @HU-G5-06 @api
  Scenario: Pausar, cambiar el umbral y reanudar una alerta
    When cambio la alerta de TRANSFERENCIAS al estado "PAUSADA"
    Then la respuesta tiene "estado" igual a "PAUSADA"
    When cambio el umbral de la alerta de TRANSFERENCIAS a S/ 400
    Then la respuesta tiene "umbral" igual a "400.00"
    When cambio la alerta de TRANSFERENCIAS al estado "ACTIVA"
    Then la respuesta tiene "estado" igual a "ACTIVA"
    When cambio la alerta de TRANSFERENCIAS al estado "APAGADA"
    Then la respuesta es 422 con el código "ALERTA_INVALIDA"

  @HU-G5-06 @api
  Scenario: No se reanuda una alerta cuyo umbral supera el límite vigente
    Given que mi límite diario es S/ 250
    When cambio la alerta de TRANSFERENCIAS al estado "ACTIVA"
    Then la respuesta es 422 con el código "ALERTA_INVALIDA"

  @HU-G5-07 @api
  Scenario: Eliminar una alerta
    When elimino la alerta de TRANSFERENCIAS
    Then la respuesta es 204
    And tengo 0 alertas
    When elimino la alerta eliminada
    Then la respuesta es 404 con el código "ALERTA_NO_ENCONTRADA"

  @HU-G5-08 @api
  Scenario: La alerta avisa al alcanzar el umbral
    Given que tengo una alerta de RECARGAS con umbral S/ 60
    When recargo S/ 50 al celular 987111222
    Then Ana recibe un SMS que contiene "Alerta Qolqe: tu gasto de hoy en recargas llegó a S/ 60.00"

  @HU-G5-08 @api
  Scenario: Una alerta pausada no avisa
    Given que tengo una alerta de RECARGAS con umbral S/ 60
    And que pausé la alerta de RECARGAS
    When recargo S/ 50 al celular 987111222
    Then Ana no recibe ningún SMS que contiene "Alerta Qolqe: tu gasto"
