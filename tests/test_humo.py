"""Prueba de humo: verifica que la app levanta y responde."""
from fastapi.testclient import TestClient

from qolqe.main import app


def test_la_app_responde():
    with TestClient(app) as cliente:
        respuesta = cliente.get("/api/salud")
        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "ok"
