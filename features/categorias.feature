# language: en
@g3
Feature: Categorías de movimientos
  Como cliente
  Quiero crear y administrar categorías propias
  Para organizar mis gastos

  # Datos: Ana tiene 3 categorías: Comida, Familia y Servicios.

  Background:
    Given que inicié sesión como Ana

  @HU-G3-03 @api
  Scenario: Crear una categoría con nombre y color de la paleta
    When creo la categoría "Transporte" de color "#43A047"
    Then la respuesta es 201
    And la categoría "Transporte" existe con color "#43A047" y 0 movimientos

  @HU-G3-03 @api
  Scenario Outline: Longitud del nombre (3 a 20 caracteres)
    When creo una categoría con nombre de <n> caracteres
    Then la operación es "<resultado>"

    Examples:
      | n  | resultado          |
      | 2  | CATEGORIA_INVALIDA |
      | 0  | CATEGORIA_INVALIDA |
      | 3  | exitosa            |
      | 20 | exitosa            |
      | 21 | CATEGORIA_INVALIDA |

  @HU-G3-03 @api
  Scenario Outline: El color debe ser de la paleta de 8 colores
    When creo la categoría "Transporte" de color "<color>"
    Then la operación es "<resultado>"

    Examples:
      | color   | resultado          |
      | #E53935 | exitosa            |
      | #6D4C41 | exitosa            |
      | #000000 | CATEGORIA_INVALIDA |
      | rojo    | CATEGORIA_INVALIDA |
      | #FDD835 | exitosa            |
      | #43A047 | exitosa            |
      | #00897B | exitosa            |
      | #1E88E5 | exitosa            |
      | #8E24AA | exitosa            |
      | #FB8C00 | exitosa            |

  @HU-G3-03 @api
  Scenario Outline: El nombre es único sin distinguir mayúsculas
    When creo la categoría "<nombre>" de color "#43A047"
    Then la operación es "<resultado>"

    Examples:
      | nombre    | resultado           |
      | Comida    | CATEGORIA_DUPLICADA |
      | COMIDA    | CATEGORIA_DUPLICADA |
      | comida    | CATEGORIA_DUPLICADA |
      | Comidas   | exitosa             |

  @HU-G3-03 @api
  Scenario Outline: Máximo 10 categorías por usuario (R-G3-03)
    Given que ya tengo <existentes> categorías
    When creo la categoría "Nueva cat" de color "#43A047"
    Then la operación es "<resultado>"

    Examples:
      | existentes | resultado         |
      | 8          | exitosa           |
      | 9          | exitosa           |
      | 10         | LIMITE_CATEGORIAS |

  @HU-G3-04 @api
  Scenario: Mis categorías en orden alfabético con su cantidad de movimientos
    When listo mis categorías
    Then veo las categorías "Comida, Familia, Servicios" en orden alfabético
    And la categoría "Servicios" tiene 5 movimientos y la categoría "Comida" tiene 0

  @HU-G3-04 @api
  Scenario: Solo veo mis categorías
    Given que Carla tiene la categoría "Ajena"
    When listo mis categorías
    Then veo las categorías "Comida, Familia, Servicios" en orden alfabético

  @HU-G3-05 @api
  Scenario: Cambiar el nombre y el color de una categoría
    When cambio la categoría "Comida" a nombre "Restaurantes" y color "#FB8C00"
    Then la categoría "Restaurantes" existe con color "#FB8C00" y 0 movimientos

  @HU-G3-05 @api
  Scenario: Cambiar solo el color conserva el nombre
    When cambio el color de la categoría "Comida" a "#FB8C00"
    Then la categoría "Comida" existe con color "#FB8C00" y 0 movimientos

  @HU-G3-05 @api
  Scenario Outline: Editar no compara la categoría consigo misma
    When renombro la categoría "Comida" como "<nombre>"
    Then la operación es "exitosa"
    And la categoría "<nombre>" existe con color "#E53935" y 0 movimientos

    Examples:
      | nombre |
      | Comida |
      | COMIDA |

  @HU-G3-05 @api @DEF-10
  Scenario Outline: Editar valida los nombres duplicados de otras categorías
    When renombro la categoría "Comida" como "<nombre>"
    Then la respuesta es 409 con el código "CATEGORIA_DUPLICADA"

    Examples:
      | nombre    |
      | Familia   |
      | SERVICIOS |

  @HU-G3-05 @api
  Scenario: Editar aplica la regla de color de la paleta
    When cambio la categoría "Comida" a nombre "Comida" y color "#123456"
    Then la operación es "CATEGORIA_INVALIDA"

  @HU-G3-05 @api
  Scenario: No puedo editar la categoría de otro usuario
    Given que Carla tiene la categoría "Ajena"
    When intento editar la categoría de Carla
    Then la respuesta es 404 con el código "CATEGORIA_NO_ENCONTRADA"

  @HU-G3-06 @api
  Scenario: Eliminar una categoría deja sus movimientos sin categoría
    When elimino la categoría "Servicios"
    Then la respuesta es 204
    And la categoría "Servicios" ya no existe
    And los 5 movimientos que tenía quedan sin categoría y conservan su monto, fecha y tipo

  @HU-G3-06 @api
  Scenario: Eliminar una categoría ajena responde 404 y no la borra
    Given que Carla tiene la categoría "Ajena"
    When intento eliminar la categoría de Carla
    Then la respuesta es 404 con el código "CATEGORIA_NO_ENCONTRADA"
    And la categoría de Carla sigue existiendo

  @HU-G3-06 @api
  Scenario: Eliminar una categoría no afecta los movimientos de otras categorías
    When elimino la categoría "Servicios"
    Then la respuesta es 204
    And los 5 movimientos de "Familia" siguen con su categoría

  @HU-G3-04 @api
  Scenario: Las categorías requieren sesión
    When listo mis categorías sin token
    Then la respuesta es 401 con el código "NO_AUTENTICADO"

  @HU-G3-03 @api
  Scenario: Un nombre de solo espacios es rechazado
    When creo la categoría "   " de color "#43A047"
    Then la operación es "CATEGORIA_INVALIDA"

  @HU-G3-03 @api
  Scenario: Un color en minúsculas se acepta y se guarda en mayúsculas
    When creo la categoría "Transporte" de color "#e53935"
    Then la operación es "exitosa"
    And la categoría "Transporte" existe con color "#E53935" y 0 movimientos

  @HU-G3-03 @api
  Scenario: El color es obligatorio
    When creo la categoría "Transporte" sin color
    Then la respuesta es 422 con el código "SOLICITUD_INVALIDA"

  @HU-G3-03 @api
  Scenario: Un color vacío es rechazado
    When creo la categoría "Transporte" con color vacío
    Then la operación es "CATEGORIA_INVALIDA"

  @HU-G3-03 @api
  Scenario: Otro usuario puede tener una categoría con el mismo nombre
    Given que Carla tiene la categoría "Ajena"
    When creo la categoría "Ajena" de color "#43A047"
    Then la operación es "exitosa"

  @HU-G3-05 @api
  Scenario Outline: Longitud del nombre al editar (3 a 20 caracteres)
    When renombro la categoría "Comida" con un nombre de <n> caracteres
    Then la operación es "<resultado>"

    Examples:
      | n  | resultado          |
      | 2  | CATEGORIA_INVALIDA |
      | 3  | exitosa            |
      | 20 | exitosa            |
      | 21 | CATEGORIA_INVALIDA |

  @HU-G3-05 @api
  Scenario: Editar una categoría que no existe responde 404
    When intento editar una categoría que no existe
    Then la respuesta es 404 con el código "CATEGORIA_NO_ENCONTRADA"

  @HU-G3-06 @api
  Scenario: Eliminar una categoría que no existe responde 404
    When intento eliminar una categoría que no existe
    Then la respuesta es 404 con el código "CATEGORIA_NO_ENCONTRADA"

  @HU-G3-06 @api
  Scenario: Eliminar dos veces la misma categoría responde 404 la segunda vez
    When elimino la categoría "Servicios"
    And elimino otra vez esa categoría
    Then la respuesta es 404 con el código "CATEGORIA_NO_ENCONTRADA"
