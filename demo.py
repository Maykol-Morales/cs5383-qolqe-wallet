"""Alista y ejecuta la demo de la presentación (Linux, macOS y Windows; solo biblioteca estándar).

    python demo.py preparar        crea .venv e instala dependencias (una vez)
    python demo.py ensayo          corre todos los pasos seguidos y mide el tiempo
    python demo.py demo            igual, pero espera Enter entre pasos (para el vivo)
    python demo.py schemathesis    CLI de Schemathesis contra un servidor temporal; abre el dashboard
    python demo.py schemathesis todos   ídem con todos los checks (44 hallazgos, ver informe §2)
    python demo.py schemathesis g3      solo endpoints de G3 (movimientos y categorías); combinable: g3 todos
    python demo.py dashboard       regenera reportes/dashboard-contrato.html con el último log de Schemathesis
                                   (y la comparativa con pytest-bdd si antes corrió `reporte`)
    python demo.py plan-b          pytest -rx guardando la salida en reportes/ensayo.txt (pregrabada)
    python demo.py reporte         pytest -rx y abre el reporte Allure (dashboard + escenarios); requiere Node (npx)

En Windows, si `python` no existe, usar `py demo.py ...`. El paso 4 (contrato) repite lo que ya
corre en el paso 2: es opcional, SIN_CONTRATO=1 lo omite. PUERTO y VENV cambian puerto y entorno.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PUERTO = int(os.environ.get("PUERTO", "8765"))
VENV = RAIZ / os.environ.get("VENV", ".venv")
BIN = VENV / ("Scripts" if os.name == "nt" else "bin")
# UTF-8 en los hijos: la consola de Windows (cp1252) rompe con tildes y emojis de Schemathesis
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def herramienta(nombre):
    ruta = shutil.which(nombre, path=str(BIN))  # resuelve .exe en Windows
    if not ruta:
        sys.exit(f"Falta {nombre} en {VENV}: ejecuta python demo.py preparar")
    return ruta


def paso(titulo, comando, env=None, pausa=False):
    print(f"\n=== {titulo}\n$ {' '.join(comando)}", flush=True)
    if pausa:
        try:
            input("(Enter para ejecutar) ")
        except EOFError:
            pass
    t = time.monotonic()
    # los xfail/fallos esperados no deben cortar la demo
    rc = subprocess.call([herramienta(comando[0]), *comando[1:]], cwd=RAIZ, env={**ENV, **(env or {})})
    print(f"--- {titulo}: {time.monotonic() - t:.0f} s (rc={rc})")
    return rc


def pasos(pausa=False):
    paso("1. Escenarios de la historia HU-G3-01", ["pytest", "tests/api", "-m", "HU-G3-01", "-v"], pausa=pausa)
    paso("2. Todos los escenarios", ["pytest", "-rx", *ALLURE], pausa=pausa)
    if paso("3. Un defecto a la vista (DEF-07)", ["pytest", "tests/api", "-m", "DEF-07"],
            env={"MOSTRAR_DEFECTOS": "1"}, pausa=pausa):
        print("(esperado: los defectos fallan a la vista)")
    if os.environ.get("SIN_CONTRATO") != "1":
        paso("4. Contrato OpenAPI (Schemathesis dentro de pytest)",
             ["pytest", "tests/api/test_contrato.py", "-v"], pausa=pausa)
    allure()


ALLURE = ["--alluredir=reportes/allure-results", "--clean-alluredir"]


def allure():
    """Genera reportes/allure/ (config en allurerc.mjs; acumula historial entre corridas) y lo abre."""
    npx = shutil.which("npx")
    if not npx:
        return print("Sin Node (npx): no se genera el reporte Allure. Resultados crudos en reportes/allure-results/")
    subprocess.call([npx, "-y", "allure@3.21.0", "generate", "--clean", "reportes/allure-results"], cwd=RAIZ, env=ENV)
    indice = RAIZ / "reportes" / "allure" / "index.html"
    print(f"Reporte Allure: {indice}")
    webbrowser.open(indice.as_uri())


def reporte():
    subprocess.call([herramienta("pytest"), "-rx", *ALLURE], cwd=RAIZ, env=ENV)
    allure()


def schemathesis_cli(args):
    checks = ("not_a_server_error,status_code_conformance,content_type_conformance,"
              "response_headers_conformance,response_schema_conformance")
    incluir = []
    if "todos" in args:
        checks = "all"
    if "g3" in args:
        incluir = ["--include-path-regex", "^/api/(movimientos|categorias)"]
    uvicorn, schemathesis = herramienta("uvicorn"), herramienta("schemathesis")
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", PUERTO)) == 0:
            sys.exit(f"Puerto {PUERTO} ocupado: usa otro con la variable PUERTO")
    base = f"http://127.0.0.1:{PUERTO}"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        servidor = subprocess.Popen(
            [uvicorn, "qolqe.main:app", "--port", str(PUERTO), "--log-level", "warning"], cwd=RAIZ,
            env={**ENV, "QOLQE_BD": str(Path(tmp) / "q.db"), "QOLQE_MODO_PRUEBA": "1"})
        try:
            for _ in range(40):
                if servidor.poll() is not None:
                    break
                try:
                    urllib.request.urlopen(f"{base}/api/salud", timeout=1)
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                sys.exit("uvicorn no respondió a tiempo")
            if servidor.poll() is not None:
                sys.exit(f"uvicorn no arrancó (¿puerto {PUERTO} ocupado?)")
            print(f"Contrato: {base}/docs  (Swagger)  ·  {base}/openapi.json", flush=True)
            login = urllib.request.Request(
                f"{base}/api/auth/login", data=json.dumps({"celular": "987654321", "pin": "4826"}).encode(),
                headers={"Content-Type": "application/json"})
            token = json.load(urllib.request.urlopen(login))["access_token"]
            # Se excluyen operaciones que invalidan la sesión o el reloj compartidos
            subprocess.call([
                schemathesis, "run", f"{base}/openapi.json", "-H", f"Authorization: Bearer {token}",
                "--seed", "1", "--max-examples", "30", "--checks", checks, *incluir,
                "--exclude-path-regex",
                "/api/auth/logout|/api/seguridad/sesiones|/api/pruebas/reloj|/api/pruebas/reiniciar|/api/cuentas/me/cierre",
                "--report", "html,vcr,har", "--report-dir", "reporte-schemathesis"], cwd=RAIZ, env=ENV)
        finally:
            servidor.terminate()
            servidor.wait()  # en Windows la BD sigue bloqueada hasta que el proceso muere
    reportes = sorted((RAIZ / "reporte-schemathesis").glob("*/index.html"), key=lambda p: p.stat().st_mtime)
    if reportes:
        print(f"Reporte de Schemathesis: {reportes[-1]}")
    dashboard()


def dashboard():
    """Dashboard propio con los logs VCR + HAR y la comparativa con pytest-bdd (si hay resultados Allure)."""
    if subprocess.call([herramienta("python"), "tests/dashboard/dashboard.py"], cwd=RAIZ, env=ENV) == 0:
        webbrowser.open((RAIZ / "reportes" / "dashboard-contrato.html").as_uri())


def preparar():
    if not VENV.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    subprocess.check_call([herramienta("python"), "-m", "pip", "install", "-q", "-r", "requirements-dev.txt"], cwd=RAIZ)
    herramienta("schemathesis")
    print("Listo: pytest y schemathesis instalados.")


def plan_b():
    (RAIZ / "reportes").mkdir(exist_ok=True)
    with open(RAIZ / "reportes" / "ensayo.txt", "w", encoding="utf-8") as salida, subprocess.Popen(
            [herramienta("pytest"), "-rx"], cwd=RAIZ, env=ENV, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace") as p:
        for linea in p.stdout:  # equivalente a tee
            print(linea, end="")
            salida.write(linea)


if __name__ == "__main__":
    orden, resto = (sys.argv[1:2] or [""])[0], sys.argv[2:]
    acciones = {
        "preparar": preparar,
        "ensayo": pasos,
        "demo": lambda: pasos(pausa=True),
        "schemathesis": lambda: schemathesis_cli(resto),
        "plan-b": plan_b,
        "reporte": reporte,
        "dashboard": dashboard,
    }
    acciones.get(orden, lambda: print(__doc__))()
