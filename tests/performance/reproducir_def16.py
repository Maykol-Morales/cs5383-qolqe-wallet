"""Reproduce DEF-16: con muchos inicios de sesión a la vez, Qolqe responde 500 "database is locked".

    QOLQE_URL=http://localhost:8003 .venv/bin/python tests/performance/reproducir_def16.py [N]

Qolqe dedicado y en modo prueba (reinicia la BD), idealmente en el contenedor de rendimiento (--cpus=1).
Lanza N logins (200 por defecto, usuarios de carga distintos, PIN correcto) liberados a la vez por una barrera.
Esperado: todos 200. Sale con 1 si alguno da 5xx o la conexión se corta.
"""
import collections
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from statistics import median

import httpx

URL = os.environ.get("QOLQE_URL", "http://localhost:8003")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200

httpx.post(f"{URL}/api/pruebas/reiniciar", timeout=300).raise_for_status()
barrera = threading.Barrier(N)
resultados, tiempos = collections.Counter(), []


def login(i):
    with httpx.Client(timeout=60) as c:
        barrera.wait()
        t = time.perf_counter()
        try:
            r = c.post(f"{URL}/api/auth/login", json={"celular": f"9{i:08d}", "pin": "2580"})
            resultados[r.status_code] += 1
        except httpx.HTTPError as e:
            resultados[type(e).__name__] += 1
        tiempos.append(time.perf_counter() - t)


with ThreadPoolExecutor(N) as ex:
    list(ex.map(login, range(1, N + 1)))

print(f"{N} logins simultáneos → {dict(resultados)}; mediana {median(tiempos):.1f} s, máx. {max(tiempos):.1f} s")
sys.exit(0 if resultados[200] == N else 1)
