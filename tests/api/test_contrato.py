"""Pruebas de contrato: Schemathesis contra /openapi.json de un servidor real (subproceso o QOLQE_URL)."""
import os
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import pytest
import schemathesis
from hypothesis import HealthCheck, settings

URL = os.getenv("QOLQE_URL")
# Operaciones que invalidan la sesión o el reloj compartidos por todos los casos generados
EXCLUIDAS = r"/api/auth/logout|/api/seguridad/sesiones|/api/pruebas/reloj|/api/pruebas/reiniciar|/api/cuentas/me/cierre"
# Conformidad con el contrato. No se exigen los checks de rigor sobre aceptar/rechazar datos
# (positive/negative_data_acceptance) ni la cabecera Allow: generan ruido sin ser defectos de negocio.
CHECKS = [schemathesis.checks.not_a_server_error, schemathesis.checks.status_code_conformance,
          schemathesis.checks.content_type_conformance, schemathesis.checks.response_headers_conformance,
          schemathesis.checks.response_schema_conformance]


# derandomize: mismos ejemplos en cada corrida, para que el pipeline sea repetible.
# Para explorar con otras semillas: quitar derandomize y subir CONTRATO_EJEMPLOS.


@pytest.fixture(scope="session")
def servidor():
    if URL:
        yield URL
        return
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    base = f"http://127.0.0.1:{puerto}"
    entorno = {**os.environ, "QOLQE_BD": os.path.join(tempfile.mkdtemp(prefix="qolqe-contrato-"), "q.db"), "QOLQE_MODO_PRUEBA": "1"}
    proceso = subprocess.Popen([sys.executable, "-m", "uvicorn", "qolqe.main:app", "--port", str(puerto), "--log-level", "warning"], env=entorno)
    try:
        for _ in range(120):
            try:
                if httpx.get(f"{base}/api/salud").status_code == 200:
                    break
            except httpx.TransportError:
                time.sleep(0.5)
        yield base
    finally:
        proceso.terminate()
        proceso.wait(10)


@pytest.fixture(scope="session")
def esquema(servidor):
    return schemathesis.openapi.from_url(f"{servidor}/openapi.json")


@pytest.fixture(scope="session")
def autorizacion(servidor):
    token = httpx.post(f"{servidor}/api/auth/login", json={"celular": "987654321", "pin": "4826"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


lazy = schemathesis.pytest.from_fixture("esquema")


@lazy.exclude(path_regex=EXCLUIDAS).parametrize()
@settings(max_examples=int(os.getenv("CONTRATO_EJEMPLOS", "15")), deadline=None, derandomize=True, suppress_health_check=list(HealthCheck))
@pytest.mark.contrato
def test_contrato_openapi(case, autorizacion):
    """Respuestas conformes al esquema: códigos, tipos, cabeceras y sin errores 5xx."""
    case.call_and_validate(headers=autorizacion, checks=CHECKS)
