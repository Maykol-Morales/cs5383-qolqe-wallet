"""Comparativa del generador: el mismo escenario que saldo.js, en Locust.

    .venv/bin/locust -f tests/performance/comparativa/locustfile.py --headless -u 100 -r 2 -t 170s --host <URL>
"""
import itertools

from locust import HttpUser, constant, task

ids = itertools.count(1)


class Cliente(HttpUser):
    wait_time = constant(1)

    def on_start(self):
        r = self.client.post("/api/auth/login", json={"celular": f"9{next(ids):08d}", "pin": "2580"})
        self.client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    @task
    def saldo(self):
        self.client.get("/api/cuentas/me/saldo")
