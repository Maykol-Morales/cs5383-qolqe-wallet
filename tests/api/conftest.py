"""Fixtures y pasos comunes de las pruebas de API (pytest + httpx + pytest-bdd).

Por defecto la app corre en el mismo proceso (TestClient) con una BD temporal.
Con QOLQE_URL=http://localhost:8000 las mismas pruebas corren contra un servidor real.
Defectos conocidos: los escenarios con la etiqueta @DEF-nn son xfail(strict) para que el
pipeline quede verde mientras el defecto exista; con MOSTRAR_DEFECTOS=1 fallan a la vista.
"""
import os
import tempfile
from datetime import date, datetime, timedelta

import httpx
import pytest
from pytest_bdd import given, parsers, then

URL = os.getenv("QOLQE_URL")
if not URL:
    os.environ.setdefault("QOLQE_BD", os.path.join(tempfile.mkdtemp(prefix="qolqe-"), "qolqe.db"))
    os.environ["QOLQE_MODO_PRUEBA"] = "1"

USUARIOS = {
    "Ana": ("987654321", "4826"), "Bruno": ("912345678", "7391"), "Carla": ("956781234", "5917"),
    "Diego": ("998877665", "3604"), "Elena": ("923456789", "8152"), "Fabián": ("934567812", "6029"),
}


@pytest.fixture(scope="session")
def http():
    if URL:
        with httpx.Client(base_url=URL, timeout=30) as cliente:
            yield cliente
    else:
        from fastapi.testclient import TestClient
        from qolqe.main import app
        with TestClient(app) as cliente:
            yield cliente


class Contexto:
    """Estado de un escenario: sesión actual, últimas respuestas y datos guardados."""

    def __init__(self, http):
        self.http = http
        self.token = None
        self.celular = None
        self.respuestas = []
        self.guardado = {}

    @property
    def respuesta(self):
        return self.respuestas[-1]

    def json(self):
        return self.respuesta.json()

    def encabezados(self, token):
        return {"Authorization": f"Bearer {token}"} if token else {}

    def llamar(self, metodo, ruta, token="__actual__", **kwargs):
        token = self.token if token == "__actual__" else token
        respuesta = self.http.request(metodo, ruta, headers=self.encabezados(token), **kwargs)
        self.respuestas.append(respuesta)
        return respuesta

    def login(self, celular, pin, **extra):
        respuesta = self.http.post("/api/auth/login", json={"celular": celular, "pin": pin, **extra})
        self.respuestas.append(respuesta)
        if respuesta.status_code == 200:
            self.token, self.celular = respuesta.json()["access_token"], celular
        return respuesta

    def como(self, nombre):
        """Token de otro usuario sin cambiar la sesión actual."""
        otro = Contexto(self.http)
        assert otro.login(*USUARIOS[nombre]).status_code == 200
        return otro.token

    def ahora(self) -> datetime:
        return datetime.fromisoformat(self.http.get("/api/pruebas/reloj").json()["ahora"])

    def fecha(self, texto: str) -> date | None:
        """'hoy', 'ayer', 'mañana', 'hace N días' (y '' para no enviar el filtro)."""
        hoy = self.ahora().date()
        if texto == "":
            return None
        if texto == "hoy":
            return hoy
        if texto == "ayer":
            return hoy - timedelta(days=1)
        if texto == "mañana":
            return hoy + timedelta(days=1)
        if texto.startswith("hace "):
            return hoy - timedelta(days=int(texto.split()[1]))
        raise ValueError(texto)

    def rango(self, desde="hace 90 días", hasta="hoy", **extra) -> dict:
        """Parámetros desde/hasta (ISO) a partir de frases como 'hace 5 días'; '' omite el filtro."""
        fechas = {"desde": self.fecha(desde), "hasta": self.fecha(hasta)}
        return {**{k: v.isoformat() for k, v in fechas.items() if v}, **extra}

    def avanzar(self, minutos: int):
        self.http.put("/api/pruebas/reloj", json={"avanzar_minutos": minutos})

    def sms(self, celular: str) -> list[str]:
        return [n["mensaje"] for n in self.http.get("/api/pruebas/notificaciones", params={"celular": celular}).json()]


@pytest.fixture(autouse=True)
def ctx(http):
    http.delete("/api/pruebas/reloj")
    assert http.post("/api/pruebas/reiniciar").status_code == 200
    return Contexto(http)


def pytest_collection_modifyitems(config, items):
    for item in items:
        for marca in item.iter_markers():
            if marca.name.startswith("DEF-") and not os.getenv("MOSTRAR_DEFECTOS"):
                item.add_marker(pytest.mark.xfail(strict=True, reason=f"Defecto conocido {marca.name} (docs/defectos.md)"))
            if marca.name == "concurrencia":
                item.add_marker(pytest.mark.skip(reason="Concurrencia: se cubre con la herramienta de rendimiento (Parte 3)"))


# ── Pasos comunes ──────────────────────────────────────────────────────────────

@given(parsers.parse("que inicié sesión como {nombre}"))
def _(ctx, nombre):
    assert ctx.login(*USUARIOS[nombre]).status_code == 200


@given(parsers.parse("que mi saldo es S/ {saldo}"))
def _(ctx, saldo):
    assert ctx.http.put("/api/pruebas/saldo", json={"celular": ctx.celular, "saldo": saldo}).status_code == 200


@given(parsers.parse("que el saldo de {nombre} es S/ {saldo}"))
def _(ctx, nombre, saldo):
    assert ctx.http.put("/api/pruebas/saldo", json={"celular": USUARIOS[nombre][0], "saldo": saldo}).status_code == 200


@then(parsers.parse("la respuesta es {estado:d}"))
def _(ctx, estado):
    assert ctx.respuesta.status_code == estado, ctx.respuesta.text


@then(parsers.parse('la respuesta es {estado:d} con el código "{codigo}"'))
def _(ctx, estado, codigo):
    assert ctx.respuesta.status_code == estado, ctx.respuesta.text
    assert ctx.json()["codigo"] == codigo


@then(parsers.parse('la operación es "{resultado}"'))
def _(ctx, resultado):
    if resultado == "exitosa":
        assert ctx.respuesta.status_code in (200, 201), ctx.respuesta.text
    else:
        assert ctx.respuesta.status_code >= 400 and ctx.json()["codigo"] == resultado, ctx.respuesta.text


@then(parsers.parse('{nombre} recibe un SMS que contiene "{texto}"'))
def _(ctx, nombre, texto):
    mensajes = ctx.sms(USUARIOS[nombre][0])
    assert any(texto in m for m in mensajes), mensajes


@then(parsers.parse('se envía al celular {celular} un SMS que contiene "{texto}"'))
def _(ctx, celular, texto):
    mensajes = ctx.sms(celular)
    assert any(texto in m for m in mensajes), mensajes
