# language: en
@nucleo
Feature: Iniciar y cerrar sesión
  Como cliente
  Quiero ingresar con mi celular y PIN y poder cerrar mi sesión
  Para acceder a mi cuenta de forma segura

  @HU-N-02 @api
  Scenario: Ingreso con credenciales correctas
    When inicio sesión con el celular "987654321" y el PIN "4826"
    Then recibo un token válido por 30 minutos
    And mi sesión aparece como activa en mis sesiones

  @HU-N-02 @api
  Scenario: Credenciales inválidas con mensaje genérico
    When inicio sesión con el celular "999999999" y el PIN "4826"
    And inicio sesión con el celular "987654321" y el PIN "1111"
    Then la respuesta es 401 con el código "CREDENCIALES_INVALIDAS"
    And ambas respuestas tienen el mismo mensaje

  @HU-N-02 @api
  Scenario: Bloqueo al tercer intento fallido consecutivo
    Given que ya fallé 2 veces el PIN del celular 912345678
    When inicio sesión con el celular "912345678" y el PIN "0000"
    Then la respuesta es 423 con el código "CUENTA_BLOQUEADA"
    And Bruno recibe un SMS que contiene "bloqueada"

  @HU-N-02 @api
  Scenario: Dos intentos fallidos no bloquean la cuenta
    Given que ya fallé 2 veces el PIN del celular 912345678
    When inicio sesión con el celular "912345678" y el PIN "7391"
    Then recibo un token válido por 30 minutos

  @HU-N-02 @api @DEF-03
  Scenario: Un ingreso exitoso reinicia el conteo de intentos fallidos
    Given que ya fallé 2 veces el PIN del celular 912345678
    And que inicié sesión como Bruno
    When inicio sesión con el celular "912345678" y el PIN "0000"
    Then la respuesta es 401 con el código "CREDENCIALES_INVALIDAS"

  @HU-N-02 @api
  Scenario Outline: Durante el bloqueo ni el PIN correcto permite ingresar; pasados 15 minutos sí
    Given que la cuenta del celular 912345678 se bloqueó hace <minutos> minutos
    When inicio sesión con el celular "912345678" y el PIN "7391"
    Then la operación es "<resultado>"

    Examples:
      | minutos | resultado        |
      | 0       | CUENTA_BLOQUEADA |
      | 14      | CUENTA_BLOQUEADA |
      | 15      | exitosa          |
      | 16      | exitosa          |

  @HU-N-02 @api
  Scenario: Una cuenta cerrada no puede iniciar sesión
    When inicio sesión con el celular "934567812" y el PIN "6029"
    Then la respuesta es 401 con el código "CUENTA_CERRADA"

  @HU-N-02 @api
  Scenario Outline: Aviso de nuevo dispositivo
    When inicio sesión con el celular "987654321", el PIN "4826" y el dispositivo "<dispositivo>"
    Then recibo un token válido por 30 minutos
    And Ana <alerta> un SMS de alerta de nuevo dispositivo

    Examples:
      | dispositivo      | alerta       |
      | a1b2c3d4e5f60718 | no recibe    |
      | ffffffffffffffff | recibe       |

  @HU-N-03 @api @DEF-05
  Scenario: Al cerrar sesión el token deja de ser válido
    Given que inicié sesión como Ana
    When cierro mi sesión
    And consulto mi saldo
    Then la respuesta es 401 con el código "NO_AUTENTICADO"

  @HU-N-03 @api
  Scenario: Cerrar una sesión no afecta mis otras sesiones
    Given que inicié sesión como Ana en dos dispositivos
    When cierro mi primera sesión
    Then mi segunda sesión sigue siendo válida

  @HU-N-03 @api @DEF-05
  Scenario: Al cerrar una de mis sesiones esa sesión deja de ser válida
    Given que inicié sesión como Ana en dos dispositivos
    When cierro mi primera sesión
    Then mi primera sesión ya no es válida

  @HU-N-02 @api
  Scenario: Un solo intento fallido no bloquea la cuenta
    Given que ya fallé 1 veces el PIN del celular 912345678
    When inicio sesión con el celular "912345678" y el PIN "7391"
    Then recibo un token válido por 30 minutos

  @HU-N-02 @api
  Scenario: Sin identificador de dispositivo no se envía la alerta
    When inicio sesión con el celular "987654321" y el PIN "4826"
    Then recibo un token válido por 30 minutos
    And Ana no recibe un SMS de alerta de nuevo dispositivo

  @HU-N-02 @api
  Scenario Outline: El token vale 30 minutos
    Given que inicié sesión como Ana
    When han pasado <minutos> minutos
    And consulto mi saldo
    Then la operación es "<resultado>"

    Examples:
      | minutos | resultado      |
      | 29      | exitosa        |
      | 30      | NO_AUTENTICADO |
      | 31      | NO_AUTENTICADO |
