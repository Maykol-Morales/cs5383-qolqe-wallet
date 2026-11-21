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

  # --- Entrega final: más escenarios de historial ---

  @HU-G3-01 @CP-W29 @story=HU-G3-01 @severity=normal
  Scenario: CP-W29 · Un rango de más de 90 días se rechaza
    When busco mis movimientos desde hace 91 días
    Then veo el error de historial "El rango máximo de consulta es de 90 días"

  @HU-G3-01 @CP-W30 @story=HU-G3-01 @severity=normal
  Scenario: CP-W30 · Filtrar el historial por tipo "Transferencias enviadas"
    When filtro mis movimientos por el tipo "Transferencias enviadas"
    Then todas las filas son de tipo "Transferencia enviada"

  @HU-G3-02 @CP-W31 @story=HU-G3-02 @severity=normal
  Scenario: CP-W31 · Ver el detalle del movimiento más reciente
    When abro el detalle de mi movimiento más reciente
    Then el detalle muestra el mismo código de operación, el tipo y el importe

  # --- Entrega final (2.ª tanda): exportar y filtrar ---

  @HU-G3-08 @CP-W38 @story=HU-G3-08 @severity=normal
  Scenario: CP-W38 · El CSV trae todos los movimientos del rango, no solo la página
    When busco mis movimientos desde hace 60 días
    Then veo 10 movimientos y el indicador "Página 1 de 2"
    When exporto el historial a CSV
    Then el CSV trae 20 movimientos

  @HU-G3-08 @CP-W39 @story=HU-G3-08 @severity=normal
  Scenario: CP-W39 · Exportar a CSV el historial filtrado por una categoría
    When busco mis movimientos desde hace 60 días
    And filtro mis movimientos por la categoría "Familia"
    And exporto el historial a CSV
    Then el CSV trae los mismos movimientos que la tabla, todos de la categoría "Familia"

  @HU-G3-08 @CP-W40 @story=HU-G3-08 @severity=normal
  Scenario: CP-W40 · Exportar un rango de más de 90 días se rechaza y no descarga nada
    When busco mis movimientos desde hace 91 días
    And intento exportar el historial a CSV
    Then veo el error de historial "El rango máximo de consulta es de 90 días"
    And no se descargó ningún CSV

  @HU-G3-01 @CP-W41 @story=HU-G3-01 @severity=normal
  Scenario: CP-W41 · Filtrar el historial por categoría
    When busco mis movimientos desde hace 60 días
    And filtro mis movimientos por la categoría "Servicios"
    Then todas las filas son de la categoría "Servicios"

  @HU-G3-01 @CP-W42 @story=HU-G3-01 @severity=normal
  Scenario: CP-W42 · Filtrar por un rango de fechas que excluye los últimos 30 días
    Given que anoto los movimientos de mis últimos 30 días
    When busco mis movimientos desde hace 60 días hasta hace 31 días
    Then veo al menos un movimiento y ninguno es de los últimos 30 días
