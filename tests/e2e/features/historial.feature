# language: en
@g3 @e2e @epic=G3-Historial-y-categorias
Feature: Consultar y exportar mi historial
  Como cliente de Qolqe
  Quiero filtrar, paginar y exportar mis movimientos
  Para revisar en qué gasto

  # Datos: en los últimos 30 días Ana tiene 10 movimientos (3 recargas, 3 pagos de servicios);
  # en los últimos 60, 20 movimientos (2 páginas de 10).

  Background:
    Given que inicié sesión como Ana
    And estoy en la sección Movimientos

  @HU-G3-01 @story=HU-G3-01 @severity=critical
  Scenario Outline: <cp> · Filtrar el historial por tipo "<tipo>"
    When filtro mis movimientos por el tipo "<tipo>"
    Then todas las filas son de tipo "<nombre>"

    @CP-W02
    Examples: Recargas
      | cp     | tipo     | nombre  |
      | CP-W02 | Recargas | Recarga |

    @CP-W03
    Examples: Pagos de servicios
      | cp     | tipo               | nombre           |
      | CP-W03 | Pagos de servicios | Pago de servicio |

  @HU-G3-01 @CP-W04 @story=HU-G3-01 @severity=normal
  Scenario: CP-W04 · Paginar el historial de 10 en 10 con Siguiente y Anterior
    When busco mis movimientos desde hace 60 días
    Then veo 10 movimientos y el indicador "Página 1 de 2"
    When paso a la página siguiente
    Then veo 10 movimientos y el indicador "Página 2 de 2"
    And las filas son otras que las de la página anterior
    And no puedo avanzar más
    When vuelvo a la página anterior
    Then veo 10 movimientos y el indicador "Página 1 de 2"

  @HU-G3-08 @CP-W05 @story=HU-G3-08 @severity=critical
  Scenario: CP-W05 · Exportar a CSV el historial filtrado por recargas
    When filtro mis movimientos por el tipo "Recargas"
    And exporto el historial a CSV
    Then el CSV tiene el encabezado "fecha;codigo_operacion;tipo;descripcion;monto;comision;importe;categoria;nota"
    And el CSV trae los mismos movimientos que la tabla, todos de tipo "RECARGA"
