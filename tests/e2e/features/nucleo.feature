# language: en
@nucleo @e2e @epic=Nucleo
Feature: Usar mi billetera: cuenta, sesión, perfil y transferencias
  Como cliente de Qolqe
  Quiero registrarme, ingresar, ver mis datos y transferir
  Para manejar mi dinero desde la web

  # Datos: Ana (987654321, PIN 4826) tiene S/ 1,500.00 y DNI ****8912; Bruno es 912345678.
  # Qolqe se reinicia antes de cada escenario (fixture en wdio.conf.js).

  @HU-N-01 @HU-N-02 @CP-W06 @story=HU-N-01 @story=HU-N-02 @severity=critical
  Scenario: CP-W06 · Registrarme e ingresar con la cuenta nueva
    When me registro con DNI "45678912", nombres "Rosa Quispe Mamani", celular "955555555" y PIN "2580"
    Then veo el aviso de inicio de sesión "Tu cuenta fue creada. Ya puedes ingresar."
    When inicio sesión con el celular "955555555" y el PIN "2580"
    Then veo el saludo "Hola, Rosa" y el saldo "S/ 0.00"

  @HU-N-01 @CP-W07 @story=HU-N-01 @severity=normal
  Scenario: CP-W07 · El registro rechaza un PIN secuencial
    When me registro con DNI "45678912", nombres "Rosa Quispe Mamani", celular "955555555" y PIN "1234"
    Then veo el error de registro "El PIN no puede ser una secuencia de dígitos"
    And sigo en la página "/registro"

  @HU-N-02 @CP-W08 @story=HU-N-02 @severity=critical
  Scenario: CP-W08 · Ingresar con un PIN incorrecto muestra un mensaje genérico
    When intento ingresar con el celular "987654321" y el PIN "0000"
    Then veo el error de inicio de sesión "Celular o PIN incorrectos"
    And sigo en la página "/login" con el PIN vacío

  # Comprueba la protección en el cliente (la UI borra el token y redirige). Que el servidor revoque el token
  # (HU-N-03 CA1) se prueba por API y hoy falla por DEF-05.
  @HU-N-03 @CP-W09 @story=HU-N-03 @severity=critical
  Scenario: CP-W09 · Cerrar sesión me devuelve al ingreso y protege las páginas
    Given que inicié sesión como Ana
    When cierro sesión
    Then veo el aviso de inicio de sesión "Cerraste sesión correctamente."
    And al abrir "/inicio" me lleva a "/login"

  @HU-N-04 @CP-W10 @story=HU-N-04 @severity=critical
  Scenario: CP-W10 · Ver y ocultar mi saldo en el inicio
    Given que inicié sesión como Ana
    Then veo el saludo "Hola, Ana" y el saldo "S/ 1,500.00"
    When oculto mi saldo
    Then el saldo se muestra como "S/ ••••••"

  @HU-N-04 @HU-N-05 @CP-W11 @story=HU-N-04 @story=HU-N-05 @severity=normal
  Scenario: CP-W11 · Ver mi perfil con el DNI enmascarado y cambiar mis nombres
    Given que inicié sesión como Ana
    And estoy en Mi perfil
    Then mi perfil muestra el DNI "****8912" y el celular "987654321"
    When cambio mis nombres a "Ana Torres Rojas"
    Then veo el mensaje del perfil "Tus datos fueron actualizados"
    And mi perfil muestra los nombres "Ana Torres Rojas"

  @HU-N-07 @HU-N-09 @CP-W12 @story=HU-N-07 @story=HU-N-09 @severity=blocker
  Scenario: CP-W12 · Transferir S/ 50.00 a otro usuario Qolqe sin comisión
    Given que inicié sesión como Ana
    And estoy en Transferir
    When preparo una transferencia de "50.00" al celular "912345678"
    Then la confirmación muestra monto "S/ 50.00", comisión "S/ 0.00" y total "S/ 50.00"
    When confirmo la transferencia
    Then el comprobante muestra destino "Bruno D. (912345678)", total "S/ 50.00" y saldo "S/ 1,450.00"

  @HU-N-07 @CP-W13 @story=HU-N-07 @severity=critical
  Scenario: CP-W13 · Una transferencia de S/ 500.01 se rechaza antes de confirmar
    Given que inicié sesión como Ana
    And estoy en Transferir
    When preparo una transferencia de "500.01" al celular "912345678"
    Then veo el error de transferencia "El monto supera el límite por operación de S/ 500.00" sin confirmación

  @HU-N-08 @HU-N-09 @CP-W14 @story=HU-N-08 @story=HU-N-09 @severity=critical
  Scenario: CP-W14 · Transferir S/ 100.00 a otro banco paga 1.5 % de comisión
    Given que inicié sesión como Ana
    And estoy en Transferir
    When preparo una transferencia de "100.00" al CCI "00212345678901234567"
    Then la confirmación muestra monto "S/ 100.00", comisión "S/ 1.50" y total "S/ 101.50"
    When confirmo la transferencia
    Then el comprobante muestra destino "CCI ****************4567", total "S/ 101.50" y saldo "S/ 1,398.50"

  @HU-N-06 @CP-W15 @story=HU-N-06 @severity=normal
  Scenario: CP-W15 · No puedo cerrar mi cuenta si tengo saldo
    Given que inicié sesión como Ana
    And estoy en Mi perfil
    When cierro mi cuenta con el PIN "4826"
    Then veo el error de cierre "Para cerrar tu cuenta el saldo debe ser S/ 0.00"
    And sigo en la página "/perfil"

  @HU-N-01 @HU-N-06 @CP-W16 @story=HU-N-06 @severity=critical
  Scenario: CP-W16 · Cerrar mi cuenta con saldo cero me impide volver a ingresar
    When me registro con DNI "45678912", nombres "Rosa Quispe Mamani", celular "955555555" y PIN "2580"
    And inicio sesión con el celular "955555555" y el PIN "2580"
    And estoy en Mi perfil
    And cierro mi cuenta con el PIN "2580"
    Then veo el aviso de inicio de sesión "Tu cuenta fue cerrada. Gracias por usar Qolqe."
    When intento ingresar con el celular "955555555" y el PIN "2580"
    Then veo el error de inicio de sesión "La cuenta fue cerrada"
