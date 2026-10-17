"""Módulo G3: historial, detalle, clasificación, exportación (HU-G3-01/02/07/08) y categorías (HU-G3-03 a 06)."""
import csv
import io
import re
from datetime import timedelta

from pytest_bdd import given, parsers, scenarios, then, when

from conftest import USUARIOS

scenarios("../../features/historial.feature", "../../features/categorias.feature")


# ── Ayudas ─────────────────────────────────────────────────────────────────────

def _id_categoria(ctx, nombre):
    categorias = ctx.http.get("/api/categorias", headers=ctx.encabezados(ctx.token)).json()
    return next((c["id"] for c in categorias if c["nombre"] == nombre), 99999)


def _todos(ctx, **params):
    """Todos los movimientos de un filtro, recorriendo las páginas (no altera la última respuesta)."""
    movimientos, pagina = [], 1
    while True:
        datos = ctx.http.get("/api/movimientos", params={**params, "pagina": pagina}, headers=ctx.encabezados(ctx.token)).json()
        movimientos += datos["movimientos"]
        if pagina >= datos["total_paginas"]:
            return movimientos
        pagina += 1


def _transferir(ctx, token, monto):
    respuesta = ctx.llamar("POST", "/api/transferencias", token=token, json={"celular_destino": USUARIOS["Bruno"][0], "monto": monto})
    assert respuesta.status_code == 201, respuesta.text
    ctx.guardado["codigo"] = respuesta.json()["codigo_operacion"]
    return respuesta


def _detalle(ctx):
    return ctx.llamar("GET", f"/api/movimientos/{ctx.guardado['codigo']}")


# ── Datos de partida ───────────────────────────────────────────────────────────

NUEVO = ("987000111", "4826")


def _usuario_nuevo(ctx):
    celular, pin = NUEVO
    assert ctx.http.post("/api/usuarios", json={"dni": "45678912", "nombres": "Lucía Fernández", "celular": celular, "pin": pin}).status_code == 201
    assert ctx.http.put("/api/pruebas/saldo", json={"celular": celular, "saldo": "100.00"}).status_code == 200
    ctx.login(celular, pin)


@given("que soy un usuario nuevo con saldo S/ 100.00")
def _(ctx):
    _usuario_nuevo(ctx)


@given(parsers.parse("que hice una transferencia de S/ {monto} a Bruno hace {dias:d} días a las {hora}"))
def _(ctx, monto, dias, hora):
    """Fija el reloj en ese instante, hace la transferencia y vuelve a la hora real."""
    dia = ctx.fecha("hoy") - timedelta(days=dias)
    assert ctx.http.put("/api/pruebas/reloj", json={"ahora": f"{dia.isoformat()}T{hora}"}).status_code == 200
    ctx.login(*NUEVO)
    _transferir(ctx, ctx.token, monto)
    ctx.http.delete("/api/pruebas/reloj")
    ctx.login(*NUEVO)


@given(parsers.parse("que tengo {n:d} movimientos de hace un día"))
def _(ctx, n):
    celular, pin = NUEVO
    _usuario_nuevo(ctx)
    for _ in range(n):
        _transferir(ctx, ctx.token, "0.01")
    ctx.avanzar(24 * 60)  # los movimientos quedan fechados "ayer"; el token vence, se vuelve a ingresar
    ctx.login(celular, pin)


@given(parsers.parse("que hice una transferencia de S/ {monto} a Bruno"))
def _(ctx, monto):
    _transferir(ctx, ctx.token, monto)
    ctx.guardado["original"] = _detalle(ctx).json()


@given(parsers.parse("que Ana transfirió S/ {monto} a Bruno"))
def _(ctx, monto):
    _transferir(ctx, ctx.como("Ana"), monto)


@given(parsers.parse('que Carla tiene la categoría "{nombre}"'))
def _(ctx, nombre):
    respuesta = ctx.http.post("/api/categorias", json={"nombre": nombre, "color": "#43A047"}, headers=ctx.encabezados(ctx.como("Carla")))
    assert respuesta.status_code == 201, respuesta.text
    ctx.guardado["categoria_ajena"] = respuesta.json()["id"]


@given(parsers.parse("que ya tengo {n:d} categorías"))
def _(ctx, n):
    actuales = len(ctx.http.get("/api/categorias", headers=ctx.encabezados(ctx.token)).json())
    for i in range(n - actuales):
        assert ctx.llamar("POST", "/api/categorias", json={"nombre": f"Extra {i}", "color": "#43A047"}).status_code == 201


# ── Historial ──────────────────────────────────────────────────────────────────

@when("consulto mi historial")
def _(ctx):
    ctx.llamar("GET", "/api/movimientos")


@when("consulto mi historial sin token")
def _(ctx):
    ctx.llamar("GET", "/api/movimientos", token=None)


@when(parsers.parse('consulto mi historial desde "{desde}" hasta "{hasta}"'))
def _(ctx, desde, hasta):
    ctx.llamar("GET", "/api/movimientos", params=ctx.rango(desde, hasta))


@when("consulto mi historial de los últimos 90 días")
def _(ctx):
    ctx.llamar("GET", "/api/movimientos", params=ctx.rango())


@when(parsers.parse('consulto mi historial de los últimos 90 días de tipo "{tipo}"'))
def _(ctx, tipo):
    ctx.llamar("GET", "/api/movimientos", params=ctx.rango(tipo=tipo))


@when(parsers.parse('consulto mi historial de los últimos 90 días de la categoría "{nombre}"'))
def _(ctx, nombre):
    ctx.llamar("GET", "/api/movimientos", params=ctx.rango(categoria_id=_id_categoria(ctx, nombre)))


@when(parsers.parse('consulto mi historial de la categoría "{nombre}"'))
def _(ctx, nombre):
    ctx.llamar("GET", "/api/movimientos", params={"categoria_id": _id_categoria(ctx, nombre)})


@when(parsers.parse('consulto mi historial con desde "{fecha}"'))
def _(ctx, fecha):
    ctx.llamar("GET", "/api/movimientos", params={"desde": fecha})


@when("consulto mi historial de la categoría de Carla")
def _(ctx):
    ctx.llamar("GET", "/api/movimientos", params={"categoria_id": ctx.guardado["categoria_ajena"]})


@when(parsers.parse('consulto la página "{pagina}" de mi historial'))
def _(ctx, pagina):
    ctx.llamar("GET", "/api/movimientos", params={"pagina": pagina})


@when(parsers.parse("consulto la página {pagina:d} de mi historial"))
def _(ctx, pagina):
    ctx.llamar("GET", "/api/movimientos", params={"pagina": pagina})


@then("el rango del historial es de hace 30 días hasta hoy")
def _(ctx):
    datos = ctx.json()
    assert (datos["desde"], datos["hasta"]) == (ctx.fecha("hace 30 días").isoformat(), ctx.fecha("hoy").isoformat())


@then("el movimiento más reciente es esa transferencia")
def _(ctx):
    assert ctx.json()["movimientos"][0]["codigo_operacion"] == ctx.guardado["codigo"]


@then(parsers.parse("el historial indica {total:d} movimientos y {paginas:d} páginas"))
def _(ctx, total, paginas):
    assert ctx.respuesta.status_code == 200, ctx.respuesta.text
    datos = ctx.json()
    assert (datos["total"], datos["total_paginas"]) == (total, paginas)


@then(parsers.parse("la página trae {n:d} movimientos"))
def _(ctx, n):
    assert len(ctx.json()["movimientos"]) == n


@then(parsers.parse('todos los movimientos son de tipo "{tipo}"'))
def _(ctx, tipo):
    assert {m["tipo"] for m in ctx.json()["movimientos"]} == {tipo}


@then(parsers.parse('todos los movimientos tienen la categoría "{nombre}"'))
def _(ctx, nombre):
    assert {m["categoria"]["nombre"] for m in ctx.json()["movimientos"]} == {nombre}


@then("los movimientos están ordenados del más reciente al más antiguo")
def _(ctx):
    fechas = [m["fecha"] for m in _todos(ctx, **ctx.rango())]
    assert len(fechas) >= 20 and fechas == sorted(fechas, reverse=True)


@then(parsers.parse('el movimiento más reciente muestra importe "{importe}", comisión "{comision}", saldo posterior "{saldo}" y tipo "{tipo}"'))
def _(ctx, importe, comision, saldo, tipo):
    m = ctx.json()["movimientos"][0]
    assert (m["importe"], m["comision"], m["saldo_posterior"], m["tipo"]) == (importe, comision, saldo, tipo)
    assert m["fecha"] and m["descripcion"] and "categoria" in m and "nota" in m and "contraparte" in m


# ── Detalle ────────────────────────────────────────────────────────────────────

@when("consulto el detalle de ese movimiento")
def _(ctx):
    _detalle(ctx)


@when(parsers.parse('consulto el detalle del movimiento "{codigo}"'))
def _(ctx, codigo):
    ctx.llamar("GET", f"/api/movimientos/{codigo}")


@then(parsers.parse('el detalle muestra tipo "{tipo}" y monto "{monto}"'))
def _(ctx, tipo, monto):
    assert ctx.respuesta.status_code == 200, ctx.respuesta.text
    assert (ctx.json()["tipo"], ctx.json()["monto"]) == (tipo, monto)


# ── Clasificación ──────────────────────────────────────────────────────────────

def _clasificar(ctx, **cambios):
    return ctx.llamar("PUT", f"/api/movimientos/{ctx.guardado['codigo']}/clasificacion", json=cambios)


@given(parsers.parse('que clasifiqué ese movimiento con la categoría "{nombre}"'))
@when(parsers.parse('clasifico ese movimiento con la categoría "{nombre}"'))
def _(ctx, nombre):
    _clasificar(ctx, categoria_id=_id_categoria(ctx, nombre))


@when("clasifico ese movimiento con la categoría de Carla")
def _(ctx):
    _clasificar(ctx, categoria_id=ctx.guardado["categoria_ajena"])


@when("clasifico ese movimiento con una categoría que no existe")
def _(ctx):
    _clasificar(ctx, categoria_id=999999)


@when(parsers.parse('clasifico el movimiento "{codigo}" con una nota de {n:d} caracteres'))
def _(ctx, codigo, n):
    ctx.llamar("PUT", f"/api/movimientos/{codigo}/clasificacion", json={"nota": "n" * n})


@when("le quito la categoría a ese movimiento")
def _(ctx):
    _clasificar(ctx, categoria_id=None)


@when(parsers.parse("agrego a ese movimiento una nota de {n:d} caracteres"))
@when(parsers.parse("clasifico ese movimiento con una nota de {n:d} caracteres"))
def _(ctx, n):
    _clasificar(ctx, nota="n" * n)


@given(parsers.parse('que agregué a ese movimiento la nota "{nota}"'))
def _(ctx, nota):
    assert _clasificar(ctx, nota=nota).status_code == 200


@when("le quito la nota a ese movimiento")
def _(ctx):
    _clasificar(ctx, nota=None)


@then(parsers.parse('el movimiento queda con la categoría "{nombre}"'))
def _(ctx, nombre):
    assert _detalle(ctx).json()["categoria"]["nombre"] == nombre


@then("el movimiento queda sin categoría")
def _(ctx):
    assert _detalle(ctx).json()["categoria"] is None


@then("el movimiento queda sin nota")
def _(ctx):
    assert _detalle(ctx).json()["nota"] is None


@then("el movimiento conserva su monto, fecha y tipo")
def _(ctx):
    antes, ahora = ctx.guardado["original"], _detalle(ctx).json()
    assert all(antes[c] == ahora[c] for c in ("monto", "fecha", "tipo", "comision", "importe"))


# ── Exportación ────────────────────────────────────────────────────────────────

@when("exporto mis movimientos")
def _(ctx):
    ctx.llamar("GET", "/api/movimientos/exportar")


@when(parsers.parse('exporto mis movimientos desde "{desde}" hasta "{hasta}"'))
def _(ctx, desde, hasta):
    ctx.llamar("GET", "/api/movimientos/exportar", params=ctx.rango(desde, hasta))


@when(parsers.parse('exporto mis movimientos de los últimos 90 días de tipo "{tipo}"'))
def _(ctx, tipo):
    ctx.llamar("GET", "/api/movimientos/exportar", params=ctx.rango(tipo=tipo))


@when(parsers.parse('exporto mis movimientos de los últimos 90 días de la categoría "{nombre}"'))
def _(ctx, nombre):
    ctx.llamar("GET", "/api/movimientos/exportar", params=ctx.rango(categoria_id=_id_categoria(ctx, nombre)))


def _filas_csv(ctx):
    assert ctx.respuesta.status_code == 200, ctx.respuesta.text
    texto = ctx.respuesta.content.decode("utf-8")
    assert not texto.startswith("﻿")
    return list(csv.reader(io.StringIO(texto), delimiter=";"))


@then(parsers.parse('recibo un archivo CSV en UTF-8 con el encabezado "{encabezado}"'))
def _(ctx, encabezado):
    tipo = ctx.respuesta.headers["content-type"].lower()
    assert "text/csv" in tipo and "utf-8" in tipo
    assert "attachment" in ctx.respuesta.headers["content-disposition"]
    assert _filas_csv(ctx)[0] == encabezado.split(";")


@then(parsers.parse("el CSV tiene {n:d} filas de datos con 9 columnas, punto decimal y separador punto y coma"))
def _(ctx, n):
    filas = _filas_csv(ctx)
    assert len(filas) - 1 == n
    for fila in filas:
        assert len(fila) == 9
    for fila in filas[1:]:
        assert all(re.fullmatch(r"-?\d+\.\d{2}", c) for c in fila[4:7]), fila


@then(parsers.parse('todas las filas del CSV son de tipo "{tipo}"'))
def _(ctx, tipo):
    assert {f[2] for f in _filas_csv(ctx)[1:]} == {tipo}


@then(parsers.parse('todas las filas del CSV tienen la categoría "{nombre}"'))
def _(ctx, nombre):
    filas = _filas_csv(ctx)[1:]
    assert filas and {f[7] for f in filas} == {nombre}


# ── Categorías ─────────────────────────────────────────────────────────────────

@when(parsers.parse('creo la categoría "{nombre}" de color "{color}"'))
def _(ctx, nombre, color):
    ctx.llamar("POST", "/api/categorias", json={"nombre": nombre, "color": color})


@when(parsers.parse("creo una categoría con nombre de {n:d} caracteres"))
def _(ctx, n):
    ctx.llamar("POST", "/api/categorias", json={"nombre": "x" * n, "color": "#43A047"})


@when(parsers.parse('creo la categoría "{nombre}" sin color'))
def _(ctx, nombre):
    ctx.llamar("POST", "/api/categorias", json={"nombre": nombre})


@when(parsers.parse('renombro la categoría "{nombre}" con un nombre de {n:d} caracteres'))
def _(ctx, nombre, n):
    ctx.llamar("PUT", f"/api/categorias/{_id_categoria(ctx, nombre)}", json={"nombre": "x" * n})


@when("intento editar una categoría que no existe")
def _(ctx):
    ctx.llamar("PUT", "/api/categorias/999999", json={"nombre": "Fantasma"})


@when("intento eliminar una categoría que no existe")
def _(ctx):
    ctx.llamar("DELETE", "/api/categorias/999999")


@when("listo mis categorías")
def _(ctx):
    ctx.llamar("GET", "/api/categorias")


@when("listo mis categorías sin token")
def _(ctx):
    ctx.llamar("GET", "/api/categorias", token=None)


def _categoria(ctx, nombre):
    categorias = ctx.http.get("/api/categorias", headers=ctx.encabezados(ctx.token)).json()
    return next((c for c in categorias if c["nombre"] == nombre), None)


@then(parsers.parse('la categoría "{nombre}" existe con color "{color}" y {n:d} movimientos'))
def _(ctx, nombre, color, n):
    categoria = _categoria(ctx, nombre)
    assert categoria and (categoria["color"], categoria["cantidad_movimientos"]) == (color, n)


@then(parsers.parse('veo las categorías "{lista}" en orden alfabético'))
def _(ctx, lista):
    nombres = [c["nombre"] for c in ctx.json()]
    assert nombres == lista.split(", ") and nombres == sorted(nombres, key=str.lower)


@then(parsers.parse('la categoría "{a}" tiene {n:d} movimientos y la categoría "{b}" tiene {m:d}'))
def _(ctx, a, n, b, m):
    cantidades = {c["nombre"]: c["cantidad_movimientos"] for c in ctx.json()}
    assert (cantidades[a], cantidades[b]) == (n, m)


@when(parsers.parse('cambio la categoría "{nombre}" a nombre "{nuevo}" y color "{color}"'))
def _(ctx, nombre, nuevo, color):
    ctx.llamar("PUT", f"/api/categorias/{_id_categoria(ctx, nombre)}", json={"nombre": nuevo, "color": color})


@when(parsers.parse('renombro la categoría "{nombre}" como "{nuevo}"'))
def _(ctx, nombre, nuevo):
    ctx.llamar("PUT", f"/api/categorias/{_id_categoria(ctx, nombre)}", json={"nombre": nuevo})


@when(parsers.parse('cambio el color de la categoría "{nombre}" a "{color}"'))
def _(ctx, nombre, color):
    ctx.llamar("PUT", f"/api/categorias/{_id_categoria(ctx, nombre)}", json={"color": color})


@when("intento editar la categoría de Carla")
def _(ctx):
    ctx.llamar("PUT", f"/api/categorias/{ctx.guardado['categoria_ajena']}", json={"nombre": "Robada"})


@when("intento eliminar la categoría de Carla")
def _(ctx):
    ctx.llamar("DELETE", f"/api/categorias/{ctx.guardado['categoria_ajena']}")


@when(parsers.parse('elimino la categoría "{nombre}"'))
def _(ctx, nombre):
    ctx.guardado["antes"] = {m["codigo_operacion"]: m for m in _todos(ctx, **ctx.rango())}
    ctx.guardado["eliminada"] = nombre
    ctx.llamar("DELETE", f"/api/categorias/{_id_categoria(ctx, nombre)}")


@then(parsers.parse('la categoría "{nombre}" ya no existe'))
def _(ctx, nombre):
    assert _categoria(ctx, nombre) is None


@then(parsers.parse("los {n:d} movimientos que tenía quedan sin categoría y conservan su monto, fecha y tipo"))
def _(ctx, n):
    antes, despues = ctx.guardado["antes"], {m["codigo_operacion"]: m for m in _todos(ctx, **ctx.rango())}
    afectados = [c for c, m in antes.items() if m["categoria"] and m["categoria"]["nombre"] == ctx.guardado["eliminada"]]
    assert len(afectados) == n and set(antes) == set(despues)
    for codigo in afectados:
        assert despues[codigo]["categoria"] is None
        assert all(antes[codigo][c] == despues[codigo][c] for c in ("monto", "fecha", "tipo", "importe", "comision"))


@then(parsers.parse('los {n:d} movimientos de "{nombre}" siguen con su categoría'))
def _(ctx, n, nombre):
    assert sum(1 for m in _todos(ctx, **ctx.rango()) if m["categoria"] and m["categoria"]["nombre"] == nombre) == n
