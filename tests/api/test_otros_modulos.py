"""Módulos fuera de nuestro alcance (G1, G2, G4, G5, G6), automatizados por API para subir la cobertura del SUT.

Camino feliz y errores principales de cada HU; no es un análisis EP/VL. Escenarios en features/otros_*.feature.
"""
import json
import re
from datetime import date, timedelta

from pytest_bdd import given, parsers, scenarios, then, when

from conftest import USUARIOS, Contexto

scenarios("../../features/otros_recargas.feature", "../../features/otros_servicios.feature",
          "../../features/otros_contactos.feature", "../../features/otros_limites.feature",
          "../../features/otros_seguridad.feature")

PIN_DE = {celular: pin for celular, pin in USUARIOS.values()}


def _leer(ctx, ruta, token="__actual__", **params):
    """GET que no cuenta como «la respuesta» del escenario."""
    token = ctx.token if token == "__actual__" else token
    return ctx.http.get(ruta, headers=ctx.encabezados(token), params=params)


def _relogin(ctx):
    assert ctx.login(ctx.celular, PIN_DE[ctx.celular]).status_code == 200


def _fijar_hoy(ctx, dia: date):
    """Fija el reloj de Lima a las 10:00 de ese día y vuelve a iniciar sesión (el token depende del reloj)."""
    assert ctx.http.put("/api/pruebas/reloj", json={"ahora": f"{dia.isoformat()}T10:00:00"}).status_code == 200
    _relogin(ctx)


def _buscar(lista, clave, valor):
    encontrado = next((x for x in lista if x[clave] == valor), None)
    assert encontrado is not None, f"{clave}={valor!r} no está en {lista}"
    return encontrado


@then(parsers.parse('la respuesta tiene "{campo}" igual a "{valor}"'))
def _(ctx, campo, valor):
    actual = ctx.json()[campo]
    assert (actual if isinstance(actual, str) else json.dumps(actual)) == valor, ctx.respuesta.text


@when("se ejecuta el proceso diario")
def _(ctx):
    assert ctx.llamar("POST", "/api/pruebas/procesar-diario", token=None).status_code == 200


@then(parsers.parse("mi saldo queda en S/ {saldo}"))
def _(ctx, saldo):
    assert _leer(ctx, "/api/cuentas/me/saldo").json()["saldo"] == saldo


# ── G1 · Recargas ──────────────────────────────────────────────────────────────

@given(parsers.parse("que hoy es {dia} en Lima"))
def _(ctx, dia):
    _fijar_hoy(ctx, date.fromisoformat(dia))


@when(parsers.parse("recargo S/ {monto} al celular {celular}"))
def _(ctx, monto, celular):
    ctx.llamar("POST", "/api/recargas", json={"celular": celular, "monto": monto})


@then(parsers.parse('mi última recarga es de S/ {monto} al celular {celular} con origen "{origen}"'))
def _(ctx, monto, celular, origen):
    ultima = _leer(ctx, "/api/recargas").json()[0]
    assert (ultima["monto"], ultima["celular"], ultima["origen"]) == (monto, celular, origen), ultima


@then(parsers.parse('la configuración de recargas ofrece los montos "{montos}"'))
def _(ctx, montos):
    assert ", ".join(_leer(ctx, "/api/recargas/configuracion", token=None).json()["montos"]) == montos


@when(parsers.parse('programo una recarga de S/ {monto} al celular {celular} el día {dia:d} con alias "{alias}"'))
def _(ctx, monto, celular, dia, alias):
    ctx.llamar("POST", "/api/recargas/programadas", json={"celular": celular, "monto": monto, "dia": dia, "alias": alias})


@given("que ya tengo 3 recargas programadas activas")
def _(ctx):
    for dia in (1, 2):
        datos = {"celular": f"98700000{dia}", "monto": "10", "dia": dia}
        assert ctx.http.post("/api/recargas/programadas", json=datos, headers=ctx.encabezados(ctx.token)).status_code == 201


@then(parsers.parse("veo {n:d} recargas programadas"))
def _(ctx, n):
    assert len(_leer(ctx, "/api/recargas/programadas").json()) == n


def _programada(ctx, alias):
    programada = _buscar(_leer(ctx, "/api/recargas/programadas").json(), "alias", alias)
    ctx.guardado["programada"] = programada["id"]
    return programada


@when(parsers.parse('cambio la programada "{alias}" a S/ {monto}, el día {dia:d} y el alias "{nuevo}"'))
def _(ctx, alias, monto, dia, nuevo):
    ruta = f"/api/recargas/programadas/{_programada(ctx, alias)['id']}"
    ctx.llamar("PUT", ruta, json={"monto": monto, "dia": dia, "alias": nuevo})


@when(parsers.parse('cambio el día de la programada "{alias}" al {dia:d}'))
def _(ctx, alias, dia):
    ctx.llamar("PUT", f"/api/recargas/programadas/{_programada(ctx, alias)['id']}", json={"dia": dia})


@when(parsers.parse('pauso la programada "{alias}"'))
def _(ctx, alias):
    ctx.llamar("POST", f"/api/recargas/programadas/{_programada(ctx, alias)['id']}/pausar")


@when(parsers.parse('reanudo la programada "{alias}"'))
def _(ctx, alias):
    ctx.llamar("POST", f"/api/recargas/programadas/{_programada(ctx, alias)['id']}/reanudar")


@when(parsers.parse('elimino la programada "{alias}"'))
def _(ctx, alias):
    ctx.llamar("DELETE", f"/api/recargas/programadas/{_programada(ctx, alias)['id']}")


@when("pauso la programada eliminada")
def _(ctx):
    ctx.llamar("POST", f"/api/recargas/programadas/{ctx.guardado['programada']}/pausar")


@given(parsers.parse('que hoy es la próxima ejecución de la programada "{alias}"'))
def _(ctx, alias):
    _fijar_hoy(ctx, date.fromisoformat(_programada(ctx, alias)["proxima_ejecucion"]))


@then(parsers.parse('la programada "{alias}" quedó "{resultado}" y su próxima ejecución pasó al mes siguiente'))
def _(ctx, alias, resultado):
    programada, hoy = _programada(ctx, alias), ctx.ahora().date()
    siguiente = date(hoy.year + hoy.month // 12, hoy.month % 12 + 1, programada["dia"])
    assert (programada["ultimo_resultado"], programada["proxima_ejecucion"]) == (resultado, siguiente.isoformat()), programada


@then(parsers.parse("las recargas de hoy al celular {celular} son {n:d}"))
def _(ctx, celular, n):
    hoy = ctx.ahora().date().isoformat()
    recargas = [r for r in _leer(ctx, "/api/recargas").json() if r["celular"] == celular and r["fecha"].startswith(hoy)]
    assert len(recargas) == n, recargas


# ── G2 · Servicios ─────────────────────────────────────────────────────────────

def _deudas(ctx, empresa, suministro):
    return _leer(ctx, "/api/servicios/deudas", empresa=empresa, suministro=suministro).json()


@when(parsers.parse("consulto las deudas de {empresa} con el suministro {suministro}"))
def _(ctx, empresa, suministro):
    ctx.llamar("GET", "/api/servicios/deudas", params={"empresa": empresa, "suministro": suministro})


@then(parsers.parse('veo {n:d} deudas de la más antigua a la más reciente con titular "{titular}"'))
def _(ctx, n, titular):
    deudas = ctx.json()
    assert len(deudas) == n and {d["titular"] for d in deudas} == {titular}, deudas
    assert [d["vencimiento"] for d in deudas] == sorted(d["vencimiento"] for d in deudas)


@then("la deuda que aún no vence no tiene mora")
def _(ctx):
    deuda = ctx.json()[-1]
    assert (deuda["dias_atraso"], deuda["mora"], deuda["total"], deuda["estado"]) == (0, "0.00", deuda["monto"], "PENDIENTE"), deuda


@then(parsers.parse('las empresas de servicios son "{empresas}"'))
def _(ctx, empresas):
    assert ", ".join(sorted(e["codigo"] for e in _leer(ctx, "/api/servicios/empresas", token=None).json())) == empresas


def _pagar(ctx, deuda_id):
    respuesta = ctx.llamar("POST", "/api/servicios/pagos", json={"deuda_id": deuda_id})
    ctx.guardado["deuda"] = deuda_id
    if respuesta.status_code == 201:
        ctx.guardado["pago"] = respuesta.json()["codigo_operacion"]
    return respuesta


@when(parsers.parse("pago la deuda de {empresa} con el suministro {suministro}"))
def _(ctx, empresa, suministro):
    _pagar(ctx, _deudas(ctx, empresa, suministro)[0]["id"])


@given(parsers.parse("que pagué la deuda de {empresa} con el suministro {suministro}"))
def _(ctx, empresa, suministro):
    assert _pagar(ctx, _deudas(ctx, empresa, suministro)[0]["id"]).status_code == 201


@when("pago otra vez la misma deuda")
def _(ctx):
    _pagar(ctx, ctx.guardado["deuda"])


@when(parsers.parse("pago la deuda número {deuda_id:d}"))
def _(ctx, deuda_id):
    _pagar(ctx, deuda_id)


def _afiliacion(ctx, alias):
    return _buscar(_leer(ctx, "/api/servicios/afiliaciones").json(), "alias", alias)


@then(parsers.parse('el pago aparece en mis pagos y en los de la afiliación "{alias}"'))
def _(ctx, alias):
    codigo = ctx.guardado["pago"]
    assert _leer(ctx, "/api/servicios/pagos").json()[0]["codigo_operacion"] == codigo
    filtrados = _leer(ctx, "/api/servicios/pagos", afiliacion_id=_afiliacion(ctx, alias)["id"]).json()
    assert [p["codigo_operacion"] for p in filtrados] == [codigo]


@then("veo el comprobante del pago, pero Bruno no")
def _(ctx):
    ruta = f"/api/servicios/pagos/{ctx.guardado['pago']}"
    assert _leer(ctx, ruta).json()["total"] == "120.00"
    ajeno = _leer(ctx, ruta, token=ctx.como("Bruno"))
    assert (ajeno.status_code, ajeno.json()["codigo"]) == (404, "PAGO_NO_ENCONTRADO")


@then(parsers.parse('la afiliación "{alias}" está en situación "{situacion}"'))
def _(ctx, alias, situacion):
    assert _afiliacion(ctx, alias)["situacion"] == situacion


@when(parsers.parse('afilio el suministro {suministro} de {empresa} con alias "{alias}"'))
def _(ctx, suministro, empresa, alias):
    ctx.llamar("POST", "/api/servicios/afiliaciones", json={"empresa": empresa, "suministro": suministro, "alias": alias})


@given("que ya tengo 8 servicios afiliados")
def _(ctx):
    for n in range(1, 6):  # Ana ya tiene 3
        datos = {"empresa": "AGUA", "suministro": f"400000000{n}", "alias": f"Agua {n}"}
        assert ctx.http.post("/api/servicios/afiliaciones", json=datos, headers=ctx.encabezados(ctx.token)).status_code == 201


@when(parsers.parse('cambio la afiliación "{alias}" al alias "{nuevo}" con el débito automático activado'))
def _(ctx, alias, nuevo):
    ctx.llamar("PUT", f"/api/servicios/afiliaciones/{_afiliacion(ctx, alias)['id']}",
               json={"alias": nuevo, "debito_automatico": True})


@given(parsers.parse("que hoy es el vencimiento de la deuda de {empresa} con el suministro {suministro}"))
def _(ctx, empresa, suministro):
    _fijar_hoy(ctx, date.fromisoformat(_deudas(ctx, empresa, suministro)[0]["vencimiento"]))


@then(parsers.parse('mi último pago es del suministro {suministro} con origen "{origen}" y mora "{mora}"'))
def _(ctx, suministro, origen, mora):
    pago = _leer(ctx, "/api/servicios/pagos").json()[0]
    assert (pago["suministro"], pago["origen"], pago["mora"]) == (suministro, origen, mora), pago


@when(parsers.parse('desafilio el servicio "{alias}"'))
def _(ctx, alias):
    ctx.llamar("DELETE", f"/api/servicios/afiliaciones/{_afiliacion(ctx, alias)['id']}")


@then(parsers.parse('no tengo afiliado el servicio "{alias}"'))
def _(ctx, alias):
    assert alias not in [a["alias"] for a in _leer(ctx, "/api/servicios/afiliaciones").json()]


# ── G4 · Contactos y solicitudes ───────────────────────────────────────────────

def _contacto(ctx, alias):
    return _buscar(_leer(ctx, "/api/contactos").json()["contactos"], "alias", alias)


@when(parsers.parse('agrego el contacto {celular} con alias "{alias}"'))
def _(ctx, celular, alias):
    ctx.llamar("POST", "/api/contactos", json={"celular": celular, "alias": alias})


@given(parsers.parse('que agregué el contacto {celular} con alias "{alias}"'))
def _(ctx, celular, alias):
    assert ctx.llamar("POST", "/api/contactos", json={"celular": celular, "alias": alias}).status_code == 201


@then(parsers.parse('mis contactos son "{aliases}"'))
def _(ctx, aliases):
    pagina = _leer(ctx, "/api/contactos").json()
    assert ", ".join(c["alias"] for c in pagina["contactos"]) == aliases and pagina["total"] == len(aliases.split(", "))


@when(parsers.parse('busco mis contactos con "{texto}"'))
def _(ctx, texto):
    ctx.llamar("GET", "/api/contactos", params={"buscar": texto})


@then(parsers.parse("encuentro {n:d} contactos"))
def _(ctx, n):
    assert ctx.json()["total"] == len(ctx.json()["contactos"]) == n


@when(parsers.parse('cambio el alias del contacto "{alias}" a "{nuevo}"'))
def _(ctx, alias, nuevo):
    ctx.llamar("PUT", f"/api/contactos/{_contacto(ctx, alias)['id']}", json={"alias": nuevo})


@when(parsers.parse('marco como favorito al contacto "{alias}"'))
def _(ctx, alias):
    ctx.llamar("PUT", f"/api/contactos/{_contacto(ctx, alias)['id']}", json={"favorito": True})


@when(parsers.parse('elimino el contacto "{alias}"'))
def _(ctx, alias):
    ctx.llamar("DELETE", f"/api/contactos/{_contacto(ctx, alias)['id']}")


@when(parsers.parse('solicito S/ {monto} a mi contacto "{alias}" por "{motivo}"'))
def _(ctx, monto, alias, motivo):
    ctx.llamar("POST", "/api/solicitudes", json={"contacto_id": _contacto(ctx, alias)["id"], "monto": monto, "motivo": motivo})


@then("la solicitud vence 48 horas después de creada")
def _(ctx):
    creada, vence = (date.fromisoformat(ctx.json()[k][:10]) for k in ("creada_en", "vence_en"))
    assert vence == creada + timedelta(days=2) and ctx.json()["vence_en"][10:] == ctx.json()["creada_en"][10:]


@given("que ya tengo 10 solicitudes pendientes enviadas")
def _(ctx):
    bruno = _contacto(ctx, "Bruno")["id"]
    for n in range(9):  # Ana ya tiene 1 («Taxi al aeropuerto»)
        datos = {"contacto_id": bruno, "monto": "10.00", "motivo": f"Deuda {n}"}
        assert ctx.http.post("/api/solicitudes", json=datos, headers=ctx.encabezados(ctx.token)).status_code == 201


def _solicitud(ctx, motivo):
    todas = _leer(ctx, "/api/solicitudes").json()
    return _buscar(todas["enviadas"] + todas["recibidas"], "motivo", motivo)


@when("consulto mis solicitudes")
def _(ctx):
    ctx.llamar("GET", "/api/solicitudes")


@when(parsers.parse('consulto mis solicitudes en estado "{estado}"'))
def _(ctx, estado):
    ctx.llamar("GET", "/api/solicitudes", params={"estado": estado})


@then(parsers.parse('veo la solicitud {lado} "{motivo}" en estado "{estado}"'))
def _(ctx, lado, motivo, estado):
    lista = _leer(ctx, "/api/solicitudes").json()[{"enviada": "enviadas", "recibida": "recibidas"}[lado]]
    assert _buscar(lista, "motivo", motivo)["estado"] == estado


@then(parsers.parse("veo {enviadas:d} solicitudes enviadas y {recibidas:d} recibidas"))
def _(ctx, enviadas, recibidas):
    assert (len(ctx.json()["enviadas"]), len(ctx.json()["recibidas"])) == (enviadas, recibidas), ctx.json()


@when(parsers.parse('acepto la solicitud "{motivo}"'))
def _(ctx, motivo):
    ctx.llamar("POST", f"/api/solicitudes/{_solicitud(ctx, motivo)['id']}/aceptar")


@then("la solicitud quedó asociada a un código de operación")
def _(ctx):
    codigo = ctx.json()["codigo_operacion"]
    assert codigo and _leer(ctx, f"/api/movimientos/{codigo}").json()["tipo"] == "TRANSFERENCIA_ENVIADA"


@when(parsers.parse('rechazo la solicitud "{motivo}" con el motivo "{texto}"'))
def _(ctx, motivo, texto):
    ctx.llamar("POST", f"/api/solicitudes/{_solicitud(ctx, motivo)['id']}/rechazar", json={"motivo": texto})


@when(parsers.parse('rechazo la solicitud "{motivo}" con un motivo de {n:d} caracteres'))
def _(ctx, motivo, n):
    ctx.llamar("POST", f"/api/solicitudes/{_solicitud(ctx, motivo)['id']}/rechazar", json={"motivo": "a" * n})


@when(parsers.parse('cancelo la solicitud "{motivo}"'))
def _(ctx, motivo):
    ctx.llamar("POST", f"/api/solicitudes/{_solicitud(ctx, motivo)['id']}/cancelar")


# ── G5 · Límites y alertas ─────────────────────────────────────────────────────

@given(parsers.parse("que ya transferí S/ {monto} a Bruno"))
def _(ctx, monto):
    datos = {"monto": monto, "celular_destino": USUARIOS["Bruno"][0]}
    assert ctx.http.post("/api/transferencias", json=datos, headers=ctx.encabezados(ctx.token)).status_code == 201


@when("consulto mis límites")
def _(ctx):
    ctx.llamar("GET", "/api/limites")


@when(parsers.parse("cambio mi límite diario a S/ {limite}"))
def _(ctx, limite):
    ctx.llamar("PUT", "/api/limites", json={"limite_diario": limite})


@given(parsers.parse("que mi límite diario es S/ {limite}"))
def _(ctx, limite):
    assert ctx.llamar("PUT", "/api/limites", json={"limite_diario": limite}).status_code == 200


@when("pasan 24 horas y vuelvo a iniciar sesión")
def _(ctx):
    ctx.avanzar(24 * 60)
    _relogin(ctx)


def _alerta(ctx, tipo):
    alerta = _buscar(_leer(ctx, "/api/limites/alertas").json(), "tipo", tipo)
    ctx.guardado["alerta"] = alerta["id"]
    return alerta


@then(parsers.parse('la alerta de {tipo} está "{estado}"'))
def _(ctx, tipo, estado):
    assert _alerta(ctx, tipo)["estado"] == estado


@when(parsers.parse("creo una alerta de {tipo} con umbral S/ {umbral}"))
def _(ctx, tipo, umbral):
    ctx.llamar("POST", "/api/limites/alertas", json={"tipo": tipo, "umbral": umbral})


@given(parsers.parse("que tengo una alerta de {tipo} con umbral S/ {umbral}"))
def _(ctx, tipo, umbral):
    assert ctx.llamar("POST", "/api/limites/alertas", json={"tipo": tipo, "umbral": umbral}).status_code == 201


@given("que ya tengo 5 alertas")
def _(ctx):
    for umbral in (10, 20, 30, 40):  # Ana ya tiene 1
        assert ctx.llamar("POST", "/api/limites/alertas", json={"tipo": "RECARGAS", "umbral": umbral}).status_code == 201


@then(parsers.parse("tengo {n:d} alertas"))
def _(ctx, n):
    assert len(_leer(ctx, "/api/limites/alertas").json()) == n


@when(parsers.parse('cambio la alerta de {tipo} al estado "{estado}"'))
def _(ctx, tipo, estado):
    ctx.llamar("PUT", f"/api/limites/alertas/{_alerta(ctx, tipo)['id']}", json={"estado": estado})


@given(parsers.parse("que pausé la alerta de {tipo}"))
def _(ctx, tipo):
    assert ctx.llamar("PUT", f"/api/limites/alertas/{_alerta(ctx, tipo)['id']}", json={"estado": "PAUSADA"}).status_code == 200


@when(parsers.parse("cambio el umbral de la alerta de {tipo} a S/ {umbral}"))
def _(ctx, tipo, umbral):
    ctx.llamar("PUT", f"/api/limites/alertas/{_alerta(ctx, tipo)['id']}", json={"umbral": umbral})


@when(parsers.parse("elimino la alerta de {tipo}"))
def _(ctx, tipo):
    ctx.llamar("DELETE", f"/api/limites/alertas/{_alerta(ctx, tipo)['id']}")


@when("elimino la alerta eliminada")
def _(ctx):
    ctx.llamar("DELETE", f"/api/limites/alertas/{ctx.guardado['alerta']}")


@then(parsers.parse('{nombre} no recibe ningún SMS que contiene "{texto}"'))
def _(ctx, nombre, texto):
    assert not [m for m in ctx.sms(USUARIOS[nombre][0]) if texto in m]


# ── G6 · Seguridad ─────────────────────────────────────────────────────────────

@when(parsers.parse('cambio mi PIN de "{actual}" a "{nuevo}"'))
def _(ctx, actual, nuevo):
    ctx.llamar("PUT", "/api/seguridad/pin", json={"pin_actual": actual, "pin_nuevo": nuevo})


@then(parsers.parse('puedo iniciar sesión con el celular {celular} y el PIN "{nuevo}", pero no con "{viejo}"'))
def _(ctx, celular, nuevo, viejo):
    assert Contexto(ctx.http).login(celular, nuevo).status_code == 200
    assert Contexto(ctx.http).login(celular, viejo).status_code == 401


def _codigo_sms(ctx, celular):
    return next(m[1] for s in ctx.sms(celular) if (m := re.search(r"desbloqueo Qolqe es (\d{6})", s)))


@when(parsers.parse("solicito un código de desbloqueo para el celular {celular}"))
def _(ctx, celular):
    ctx.llamar("POST", "/api/seguridad/desbloqueo/solicitar", token=None, json={"celular": celular})


@given(parsers.parse("que solicité un código de desbloqueo para el celular {celular}"))
def _(ctx, celular):
    assert ctx.llamar("POST", "/api/seguridad/desbloqueo/solicitar", token=None, json={"celular": celular}).status_code == 202


def _confirmar(ctx, celular, codigo):
    ctx.llamar("POST", "/api/seguridad/desbloqueo/confirmar", token=None, json={"celular": celular, "codigo": codigo})


@when(parsers.parse("confirmo el desbloqueo del celular {celular} con el código del SMS"))
def _(ctx, celular):
    _confirmar(ctx, celular, _codigo_sms(ctx, celular))


@when(parsers.parse("confirmo el desbloqueo del celular {celular} con un código incorrecto"))
def _(ctx, celular):
    _confirmar(ctx, celular, f"{(int(_codigo_sms(ctx, celular)) + 1) % 10**6:06d}")


@when(parsers.parse('confirmo el desbloqueo del celular {celular} con el código "{codigo}"'))
def _(ctx, celular, codigo):
    _confirmar(ctx, celular, codigo)


@then(parsers.parse("{nombre} puede iniciar sesión"))
def _(ctx, nombre):
    assert Contexto(ctx.http).login(*USUARIOS[nombre]).status_code == 200


@then("las tres respuestas son 202 con el mismo mensaje")
def _(ctx):
    ultimas = ctx.respuestas[-3:]
    assert [r.status_code for r in ultimas] == [202] * 3 and len({r.text for r in ultimas}) == 1


@then(parsers.parse("el mensaje indica que quedan {n:d} intentos"))
def _(ctx, n):
    assert f"Te quedan {n} intentos" in ctx.json()["detail"]


@when(parsers.parse("han pasado {n:d} minutos desde que pedí el código"))
def _(ctx, n):
    ctx.avanzar(n)


def _registrar(ctx, nombre, tipo, pin):
    return ctx.llamar("POST", "/api/seguridad/dispositivos", json={"nombre": nombre, "tipo": tipo, "pin": pin})


@when(parsers.parse('registro el dispositivo "{nombre}" de tipo {tipo} con el PIN "{pin}"'))
def _(ctx, nombre, tipo, pin):
    _registrar(ctx, nombre, tipo, pin)


@given(parsers.parse('que registré los dispositivos "{primero}" y "{segundo}"'))
def _(ctx, primero, segundo):
    for nombre in (primero, segundo):
        assert _registrar(ctx, nombre, "TABLET", PIN_DE[ctx.celular]).status_code == 201


@then("el dispositivo tiene un identificador para el inicio de sesión")
def _(ctx):
    dispositivo = ctx.json()
    assert re.fullmatch(r"[0-9a-f]{16}", dispositivo["id"]) and dispositivo["ultimo_ingreso"] is None
    assert Contexto(ctx.http).login(ctx.celular, PIN_DE[ctx.celular], dispositivo_id=dispositivo["id"]).status_code == 200
    assert _buscar(_leer(ctx, "/api/seguridad/dispositivos").json(), "id", dispositivo["id"])["ultimo_ingreso"]


@then(parsers.parse('mis dispositivos son "{nombres}"'))
def _(ctx, nombres):
    assert ", ".join(d["nombre"] for d in _leer(ctx, "/api/seguridad/dispositivos").json()) == nombres


@then("ya no tengo dispositivos de confianza")
def _(ctx):
    assert _leer(ctx, "/api/seguridad/dispositivos").json() == []


def _dispositivo(ctx, nombre):
    dispositivo = _buscar(_leer(ctx, "/api/seguridad/dispositivos").json(), "nombre", nombre)
    ctx.guardado["dispositivo"] = dispositivo["id"]
    return dispositivo


@when(parsers.parse('renombro el dispositivo "{nombre}" a "{nuevo}"'))
def _(ctx, nombre, nuevo):
    ctx.llamar("PUT", f"/api/seguridad/dispositivos/{_dispositivo(ctx, nombre)['id']}", json={"nombre": nuevo})


@when(parsers.parse('elimino el dispositivo "{nombre}"'))
def _(ctx, nombre):
    ctx.llamar("DELETE", f"/api/seguridad/dispositivos/{_dispositivo(ctx, nombre)['id']}")


@then("si inicio sesión desde el dispositivo eliminado recibo la alerta de nuevo dispositivo")
def _(ctx):
    antes = len(ctx.sms(ctx.celular))
    assert Contexto(ctx.http).login(ctx.celular, PIN_DE[ctx.celular], dispositivo_id=ctx.guardado["dispositivo"]).status_code == 200
    mensajes = ctx.sms(ctx.celular)
    assert len(mensajes) == antes + 1 and "nuevo dispositivo" in mensajes[0], mensajes


@given(parsers.parse("que también inicié sesión como {nombre} en otro dispositivo"))
def _(ctx, nombre):
    ctx.guardado["otra"] = ctx.como(nombre)


@when("consulto mis sesiones")
def _(ctx):
    ctx.llamar("GET", "/api/seguridad/sesiones")


@then(parsers.parse("veo {n:d} sesiones y solo una es la actual"))
def _(ctx, n):
    sesiones = ctx.json()
    assert len(sesiones) == n and sum(s["actual"] for s in sesiones) == 1, sesiones


def _sesion(ctx, actual):
    return next(s["id"] for s in _leer(ctx, "/api/seguridad/sesiones").json() if s["actual"] == actual)


@when("cierro mi otra sesión")
def _(ctx):
    ctx.llamar("DELETE", f"/api/seguridad/sesiones/{_sesion(ctx, actual=False)}")


@when("cierro todas mis otras sesiones")
def _(ctx):
    ctx.llamar("DELETE", "/api/seguridad/sesiones")


@when("Bruno intenta cerrar mi sesión")
def _(ctx):
    ctx.llamar("DELETE", f"/api/seguridad/sesiones/{_sesion(ctx, actual=True)}", token=ctx.como("Bruno"))


@then("mi otra sesión ya no es válida")
def _(ctx):
    assert _leer(ctx, "/api/cuentas/me", token=ctx.guardado["otra"]).status_code == 401


@then("mi sesión actual sigue siendo válida")
def _(ctx):
    assert _leer(ctx, "/api/cuentas/me").status_code == 200
