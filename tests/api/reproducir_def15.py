"""Reproduce DEF-15: Qolqe envía la respuesta antes de confirmar la transacción en la BD.

    python tests/api/reproducir_def15.py      (desde la raíz; sale con 1 mientras el defecto exista)

El commit de `obtener_bd` corre después de enviar la respuesta. En la CI la ventana es de milisegundos y aparece de
vez en cuando (Schemathesis, run 42991620965). Para verlo siempre, la prueba demora 300 ms cada commit (inyección de
demora en la conexión; `qolqe/` no se modifica) y manda la siguiente petición en cuanto recibe la respuesta.
"""
import os
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("QOLQE_MODO_PRUEBA", "1")
os.environ.setdefault("QOLQE_BD", str(Path(tempfile.mkdtemp()) / "def15.db"))

import httpx  # noqa: E402
import uvicorn  # noqa: E402

import qolqe.bd as bd  # noqa: E402

DEMORA, PUERTO = 0.3, 8015


class ConexionLenta(sqlite3.Connection):
    def commit(self):
        time.sleep(DEMORA)
        super().commit()


def conectar():
    c = sqlite3.connect(bd.config.RUTA_BD, timeout=10, check_same_thread=False, factory=ConexionLenta)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA busy_timeout = 10000")
    return c


def main():
    bd.conectar = conectar
    servidor = uvicorn.Server(uvicorn.Config("qolqe.main:app", port=PUERTO, log_level="critical"))
    threading.Thread(target=servidor.run, daemon=True).start()
    c = httpx.Client(base_url=f"http://127.0.0.1:{PUERTO}", timeout=10)
    while not servidor.started:
        time.sleep(0.05)
    c.post("/api/pruebas/reiniciar")
    time.sleep(2 * DEMORA)

    rosa = {"dni": "45678912", "nombres": "Rosa Quispe Mamani", "celular": "955000001", "pin": "2580"}
    casos = []
    r1 = c.post("/api/usuarios", json=rosa)
    r2 = c.post("/api/usuarios", json=rosa)
    casos.append(("Registro repetido inmediato → 409 CELULAR_REGISTRADO", r1.status_code == 201 and r2.status_code == 409,
                  f"{r1.status_code} y luego {r2.status_code}"))
    time.sleep(2 * DEMORA)

    c.post("/api/usuarios", json={**rosa, "dni": "45678913", "celular": "955000002"})
    login = c.post("/api/auth/login", json={"celular": "955000002", "pin": "2580"})
    casos.append(("Login inmediato tras registrarse → 200", login.status_code == 200,
                  f"{login.status_code} {login.json().get('codigo', '')}"))
    time.sleep(2 * DEMORA)

    token = c.post("/api/auth/login", json={"celular": "987654321", "pin": "4826"}).json()["access_token"]
    saldo = c.get("/api/cuentas/me/saldo", headers={"Authorization": f"Bearer {token}"})
    casos.append(("Saldo con el token recién emitido → 200", saldo.status_code == 200,
                  f"{saldo.status_code} {saldo.json().get('codigo', '')}"))

    for nombre, ok, obtenido in casos:
        print(f"{'✅' if ok else '❌'} {nombre}: obtenido {obtenido}")
    servidor.should_exit = True
    return 0 if all(ok for _, ok, _ in casos) else 1


if __name__ == "__main__":
    sys.exit(main())
