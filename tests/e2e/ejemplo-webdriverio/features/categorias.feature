# language: en
@g3
Feature: Categorías de movimientos (web)
  Como cliente
  Quiero crear categorías propias desde la página de historial
  Para organizar mis gastos

  # Copia reducida de features/categorias.feature (escenarios @api), ejecutada por la interfaz web.
  # Datos: Ana tiene 3 categorías: Comida, Familia y Servicios.

  Background:
    Given que inicié sesión como Ana en la web
    And estoy en la página de historial

  @HU-G3-03
  Scenario: Crear una categoría con nombre y color de la paleta
    When creo la categoría "Transporte" de color "#43A047"
    Then veo el aviso 'Categoría "Transporte" creada'
    And la categoría "Transporte" aparece en mi lista con 0 movimientos
    And el contador de categorías muestra "4 de 10"

  @HU-G3-03
  Scenario: Crear una categoría y verla con el color elegido
    When creo la categoría "Mascotas" de color "#1E88E5"
    Then veo el aviso 'Categoría "Mascotas" creada'
    And la categoría "Mascotas" aparece en mi lista con 0 movimientos
    And la categoría "Mascotas" se muestra con el color "#1E88E5"
    And el contador de categorías muestra "4 de 10"

  @HU-G3-03
  Scenario: Un nombre de 2 caracteres es rechazado
    When creo la categoría "Tr" de color "#43A047"
    Then veo el error "El nombre de la categoría debe tener entre 3 y 20 caracteres"
    And el contador de categorías muestra "3 de 10"

  @HU-G3-03
  Scenario: El nombre es único sin distinguir mayúsculas
    When creo la categoría "COMIDA" de color "#43A047"
    Then veo el error "Ya tienes una categoría con ese nombre"
    And el contador de categorías muestra "3 de 10"
