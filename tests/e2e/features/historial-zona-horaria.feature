# language: en
@g3 @e2e @epic=G3-Historial-y-categorias
Feature: Ver mi historial aunque mi celular use otra zona horaria
  R-G3-01: por defecto se muestran los últimos 30 días hasta hoy, incluyendo los de hoy,
  y un "día" se cuenta en hora de Lima (requisitos §1).
  Defecto conocido: `npm test` no lo corre; `npm run test:defectos` lo muestra fallando
  (si llega a pasar, el defecto se corrigió y hay que retirar @DEF-14).

  @HU-G3-01 @story=HU-G3-01 @DEF-14 @issue=DEF-14 @severity=normal
  Scenario: De noche en Lima, con el celular en hora UTC, el historial muestra los últimos 30 días
    Given en Lima son las 23:00 y mi celular está en hora UTC
    And que inicié sesión como Ana
    When abro la sección Movimientos
    Then veo mis movimientos de los últimos 30 días sin errores
