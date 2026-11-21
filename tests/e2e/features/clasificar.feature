# language: en
@g3 @e2e @epic=G3-Historial-y-categorias
Feature: Clasificar mis movimientos en categorías propias
  Como cliente de Qolqe
  Quiero crear categorías y asignarlas a mis movimientos
  Para organizar mis gastos

  # Datos: Ana tiene 3 categorías (Comida, Familia y Servicios).
  # Qolqe se reinicia antes de cada escenario (fixture en wdio.conf.js).

  Background:
    Given que inicié sesión como Ana
    And estoy en la sección Movimientos

  @HU-G3-03 @HU-G3-07 @CP-W01 @story=HU-G3-03 @story=HU-G3-07 @severity=critical
  Scenario: CP-W01 · Clasificar el último movimiento en una categoría nueva
    When creo la categoría "Viajes" de color "#1E88E5"
    And clasifico mi movimiento más reciente en "Viajes" con la nota "Pasaje a Cusco"
    Then la fila del movimiento muestra la categoría "Viajes" y la nota "Pasaje a Cusco"
    And la categoría "Viajes" cuenta 1 movimientos

  # --- Entrega final: validaciones y eliminación de categorías ---

  @HU-G3-03 @CP-W32 @story=HU-G3-03 @severity=normal
  Scenario: CP-W32 · No se crea una categoría con nombre de 2 caracteres
    When intento crear la categoría "Ab" de color "#1E88E5"
    Then veo el error de categoría "El nombre de la categoría debe tener entre 3 y 20 caracteres"
    And la lista de categorías no incluye "Ab"

  @HU-G3-03 @CP-W33 @story=HU-G3-03 @severity=normal
  Scenario: CP-W33 · No se crea una categoría con un nombre repetido sin distinguir mayúsculas
    When intento crear la categoría "comida" de color "#1E88E5"
    Then veo el error de categoría "Ya tienes una categoría con ese nombre"

  @HU-G3-06 @CP-W34 @story=HU-G3-06 @severity=normal
  Scenario: CP-W34 · Eliminar una categoría la quita de la lista
    When elimino la categoría "Comida"
    Then veo el aviso "Categoría eliminada"
    And la lista de categorías no incluye "Comida"
    And el contador de categorías muestra "2 de 10"
