"""Núcleo común (HU-N-01 a HU-N-09), automatizado por API. Escenarios en features/nucleo_*.feature."""
from pytest_bdd import given, parsers, scenarios, then, when

from conftest import USUARIOS

scenarios("../../features/nucleo_registro.feature", "../../features/nucleo_sesion.feature",
          "../../features/nucleo_cuenta.feature", "../../features/nucleo_transferencias.feature")

VALIDOS = {"dni": "45678912", "nombres": "Lucía Fernández Rojas", "celular": "987000111", "pin": "4826"}


# ── Registro ───────────────────────────────────────────────────────────────────

@when(parsers.parse('me registro con {campo} "{valor}" y el resto de datos válidos'))
def _(ctx, campo, valor):
    datos = {**VALIDOS, campo.lower(): valor}
    ctx.llamar("POST", "/api/usuarios", token=None, json=datos)
    ctx.guardado["registrado"] = (datos["celular"], datos["pin"])


@then(parsers.parse("la cuenta nueva tiene saldo S/ {saldo} y límite diario de S/ {limite}"))
def _(ctx, saldo, limite):
    celular, pin = ctx.guardado["registrado"]
    ctx.login(celular, pin)
    assert ctx.llamar("GET", "/api/cuentas/me/saldo").json()["saldo"] == saldo
    assert ctx.llamar("GET", "/api/limites").json()["limite_diario"] == limite


# ── Sesión ─────────────────────────────────────────────────────────────────────

@when(parsers.parse('inicio sesión con el celular "{celular}" y el PIN "{pin}"'))
def _(ctx, celular, pin):
    ctx.login(celular, pin)


@when(parsers.parse('inicio sesión con el celular "{celular}", el PIN "{pin}" y el dispositivo "{dispositivo}"'))
def _(ctx, celular, pin, dispositivo):
    ctx.login(celular, pin, dispositivo_id=dispositivo)


@given(parsers.parse("que ya fallé {n:d} veces el PIN del celular {celular}"))
def _(ctx, n, celular):
    for _ in range(n):
        assert ctx.login(celular, "0000").status_code == 401


@given(parsers.parse("que la cuenta del celular {celular} se bloqueó hace {minutos:d} minutos"))
def _(ctx, celular, minutos):
    for _ in range(3):
        ctx.login(celular, "0000")
    assert ctx.respuesta.status_code == 423
    ctx.avanzar(minutos)


@then("recibo un token válido por 30 minutos")
def _(ctx):
    assert ctx.respuesta.status_code == 200, ctx.respuesta.text
    assert ctx.json()["expires_in"] == 30 * 60
    assert ctx.llamar("GET", "/api/cuentas/me/saldo").status_code == 200


@then("ambas respuestas tienen el mismo mensaje")
def _(ctx):
    a, b = ctx.respuestas[-2:]
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


@then(parsers.parse("Ana {alerta} un SMS de alerta de nuevo dispositivo"))
def _(ctx, alerta):
    hay = any("dispositivo" in m.lower() for m in ctx.sms(USUARIOS["Ana"][0]))
    assert hay == (alerta == "recibe")


@given("que inicié sesión como Ana en dos dispositivos")
def _(ctx):
    ctx.guardado["tokens"] = [ctx.como("Ana"), ctx.como("Ana")]
    ctx.token = ctx.guardado["tokens"][0]


@when("cierro mi sesión")
def _(ctx):
    assert ctx.llamar("POST", "/api/auth/logout").status_code == 204


@when("cierro mi primera sesión")
def _(ctx):
    assert ctx.llamar("POST", "/api/auth/logout", token=ctx.guardado["tokens"][0]).status_code == 204


@then("mi primera sesión ya no es válida")
def _(ctx):
    assert ctx.llamar("GET", "/api/cuentas/me/saldo", token=ctx.guardado["tokens"][0]).status_code == 401


@then("mi sesión anterior ya no es válida")
def _(ctx):
    assert ctx.llamar("GET", "/api/cuentas/me/saldo").status_code == 401


@then("mi segunda sesión sigue siendo válida")
def _(ctx):
    assert ctx.llamar("GET", "/api/cuentas/me/saldo", token=ctx.guardado["tokens"][1]).status_code == 200


# ── Cuenta ─────────────────────────────────────────────────────────────────────

@when("consulto mi saldo")
def _(ctx):
    ctx.llamar("GET", "/api/cuentas/me/saldo")


@when(parsers.parse("consulto mi saldo {situacion}"))
def _(ctx, situacion):
    if situacion == "sin token":
        ctx.llamar("GET", "/api/cuentas/me/saldo", token=None)
    elif situacion == "con un token inválido":
        ctx.llamar("GET", "/api/cuentas/me/saldo", token="no.es.un.jwt")
    else:
        ctx.avanzar(31)
        ctx.llamar("GET", "/api/cuentas/me/saldo")


@when("consulto mi perfil")
def _(ctx):
    ctx.llamar("GET", "/api/cuentas/me")


@then(parsers.parse("mi saldo es S/ {saldo}"))
def _(ctx, saldo):
    assert ctx.llamar("GET", "/api/cuentas/me/saldo").json()["saldo"] == saldo


@then(parsers.parse("el saldo de {nombre} es S/ {saldo}"))
def _(ctx, nombre, saldo):
    respuesta = ctx.llamar("GET", "/api/cuentas/me/saldo", token=ctx.como(nombre))
    assert respuesta.json()["saldo"] == saldo


@then(parsers.parse('la moneda es "{moneda}" y se indica la fecha de la última actualización'))
def _(ctx, moneda):
    datos = ctx.json()
    assert datos["moneda"] == moneda and datos["actualizado_en"]


@then(parsers.parse('veo mis nombres "{nombres}", mi celular "{celular}" y mi correo "{correo}"'))
def _(ctx, nombres, celular, correo):
    datos = ctx.json()
    assert (datos["nombres"], datos["celular"], datos["correo"]) == (nombres, celular, correo)


@then(parsers.parse('el DNI se muestra como "{dni}"'))
def _(ctx, dni):
    assert ctx.json()["dni"] == dni


@when(parsers.parse("cambio mis nombres por un texto de {n:d} caracteres"))
def _(ctx, n):
    ctx.llamar("PUT", "/api/cuentas/me", json={"nombres": "A" * n})


@when(parsers.parse('cambio mi correo por "{correo}"'))
def _(ctx, correo):
    ctx.llamar("PUT", "/api/cuentas/me", json={"correo": correo})


@when(parsers.parse('envío un cambio de perfil con el DNI "{dni}" y el celular "{celular}"'))
def _(ctx, dni, celular):
    ctx.llamar("PUT", "/api/cuentas/me", json={"dni": dni, "celular": celular, "nombres": "Ana Torres Quispe"})


@when(parsers.parse('cierro mi cuenta con el PIN "{pin}"'))
def _(ctx, pin):
    ctx.llamar("POST", "/api/cuentas/me/cierre", json={"pin": pin})


@then(parsers.parse('{quien} no puede transferir S/ {monto} al celular {celular} por "{codigo}"'))
def _(ctx, quien, monto, celular, codigo):
    respuesta = ctx.llamar("POST", "/api/transferencias", token=ctx.como(quien),
                           json={"celular_destino": celular, "monto": monto})
    assert respuesta.json()["codigo"] == codigo, respuesta.text


@then(parsers.parse('{quien} no puede iniciar sesión por "{codigo}"'))
def _(ctx, quien, codigo):
    ctx.login(*USUARIOS[quien])
    assert ctx.respuesta.status_code == 401 and ctx.json()["codigo"] == codigo


# ── Transferencias ─────────────────────────────────────────────────────────────

def _transferir(ctx, monto, **destino):
    return ctx.llamar("POST", "/api/transferencias", json={"monto": monto, **destino})


@when(parsers.parse("transfiero S/ {monto} al celular {celular}"))
@when(parsers.parse("intento transferir S/ {monto} al celular {celular}"))
def _(ctx, monto, celular):
    _transferir(ctx, monto, celular_destino=celular)


@when(parsers.parse("transfiero S/ {monto} al CCI {cci}"))
@when(parsers.parse("intento transferir S/ {monto} al CCI {cci}"))
def _(ctx, monto, cci):
    _transferir(ctx, monto, tipo="INTERBANCARIA", cci=cci)


@when(parsers.parse("transfiero S/ {monto} al celular {celular} con una descripción de {n:d} caracteres"))
def _(ctx, monto, celular, n):
    _transferir(ctx, monto, celular_destino=celular, descripcion="d" * n)


@given(parsers.parse("que ya transferí S/ {monto} al celular {celular}"))
def _(ctx, monto, celular):
    assert _transferir(ctx, monto, celular_destino=celular).status_code == 201


@then(parsers.parse("el comprobante muestra monto S/ {monto}, comisión S/ {comision}, total S/ {total} y mi nuevo saldo S/ {saldo}"))
def _(ctx, monto, comision, total, saldo):
    datos = ctx.json()
    assert (datos["monto"], datos["comision"], datos["total"], datos["saldo"]) == (monto, comision, total, saldo)
    assert datos["codigo_operacion"] and datos["fecha"]


@then(parsers.parse('el destinatario del comprobante es "{nombre}" con celular {celular}'))
def _(ctx, nombre, celular):
    destinatario = ctx.json()["destinatario"]
    assert (destinatario["nombre"], destinatario["celular"]) == (nombre, celular)


@then(parsers.parse('el CCI del comprobante termina en "{ultimos}" y no revela el resto'))
def _(ctx, ultimos):
    cci = ctx.json()["destinatario"]["cci"]
    assert cci.endswith(ultimos) and set(cci[:-4]) == {"*"} and len(cci) == 20


@then("Bruno y yo vemos el mismo código de operación en el historial")
def _(ctx):
    mio = ctx.llamar("GET", "/api/movimientos/recientes?limite=1").json()[0]
    de_bruno = ctx.llamar("GET", "/api/movimientos/recientes?limite=1", token=ctx.como("Bruno")).json()[0]
    assert mio["codigo_operacion"] == de_bruno["codigo_operacion"]
    assert (mio["tipo"], de_bruno["tipo"]) == ("TRANSFERENCIA_ENVIADA", "TRANSFERENCIA_RECIBIDA")


@when(parsers.parse("simulo una transferencia {tipo} de S/ {monto}"))
def _(ctx, tipo, monto):
    ctx.llamar("GET", "/api/transferencias/comision", params={"monto": monto, "tipo": tipo})


@then(parsers.parse("veo comisión S/ {comision} y total S/ {total}"))
def _(ctx, comision, total):
    datos = ctx.json()
    assert (datos["comision"], datos["total"]) == (comision, total)


@then(parsers.parse("la comisión es S/ {comision} y el total S/ {total}"))
def _(ctx, comision, total):
    """Se verifica con el simulador y con la transferencia real: ambos deben coincidir (RN-09)."""
    real = ctx.json()
    assert ctx.respuesta.status_code == 201, ctx.respuesta.text
    assert (real["comision"], real["total"]) == (comision, total)
    simulada = ctx.llamar("GET", "/api/transferencias/comision", params={"monto": real["monto"], "tipo": "INTERBANCARIA"}).json()
    assert (simulada["comision"], simulada["total"]) == (comision, total)
