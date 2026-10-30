"""Fixtures y pasos comunes de las pruebas de API (pytest + httpx + pytest-bdd).

Por defecto la app corre en el mismo proceso (TestClient) con una BD temporal.
Con QOLQE_URL=http://localhost:8000 las mismas pruebas corren contra un servidor real.
Defectos conocidos: los escenarios con la etiqueta @DEF-nn son xfail(strict) para que el
pipeline quede verde mientras el defecto exista; con MOSTRAR_DEFECTOS=1 fallan a la vista.
"""
import json
import os
import re
import tempfile
from datetime import date, datetime, timedelta

import allure
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


# ── Reporte Allure: módulo → HU, severidad y enlace de cada DEF, petición/respuesta por paso ──

DEFECTOS_MD = "https://github.com/Maykol-Morales/cs5383-qolqe-wallet/blob/parte-2/docs/defectos.md"
SEVERIDAD = {"Crítica": "blocker", "Alta": "critical", "Media": "normal", "Baja": "minor"}
with open(os.path.join(os.path.dirname(__file__), "../../docs/defectos.md"), encoding="utf-8") as _f:
    DEFECTOS = {  # "DEF-07": ("El historial excluye…", "Alta")
        m[0]: (m[1], m[2]) for m in re.findall(r"^## (DEF-\d+): (.+?)\n(?:(?!## ).*\n)*?\| Severidad \| (\w+)", _f.read(), re.M)}


@pytest.hookimpl(trylast=True)  # después de que allure-pytest-bdd cree el resultado
def pytest_bdd_before_scenario(request, feature, scenario):
    allure.dynamic.epic("Núcleo" if "nucleo_" in feature.rel_filename else "G3 · Historial y categorías")
    for etiqueta in sorted(scenario.tags | feature.tags):
        if etiqueta.startswith("HU-"):
            allure.dynamic.story(etiqueta)
        elif etiqueta in DEFECTOS:
            titulo, severidad = DEFECTOS[etiqueta]
            allure.dynamic.issue(DEFECTOS_MD, f"{etiqueta}: {titulo}")
            allure.dynamic.severity(SEVERIDAD[severidad])
    request.node._respuestas_vistas = 0
    # Trazabilidad (.github/scripts/reportes.py): el JUnit lleva el escenario de origen de cada prueba
    request.node.user_properties.append(("escenario", f"{os.path.basename(feature.filename)}::{scenario.name}"))


@pytest.hookimpl(tryfirst=True)  # antes de que allure cierre el paso
def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    _adjuntar_http(request)


@pytest.hookimpl(tryfirst=True)
def pytest_bdd_step_error(request, feature, scenario, step, step_func, step_func_args, exception):
    _adjuntar_http(request)


def _adjuntar_http(request):
    """Adjunta al paso las peticiones HTTP que hizo desde el paso anterior."""
    respuestas = request.getfixturevalue("ctx").respuestas
    for r in respuestas[getattr(request.node, "_respuestas_vistas", 0):]:
        try:
            cuerpo = json.dumps(r.json(), ensure_ascii=False, indent=2)
        except ValueError:
            cuerpo = r.text
        enviado = r.request.content.decode("utf-8", "replace")
        token = " · con token" if "authorization" in r.request.headers else " · sin token"
        allure.attach(f"{r.request.method} {r.request.url}{token}\n{enviado}\n\n← {r.status_code}\n{cuerpo}",
                      name=f"{r.request.method} {r.request.url.path} → {r.status_code}",
                      attachment_type=allure.attachment_type.TEXT)
    request.node._respuestas_vistas = len(respuestas)


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
