"""Alista y ejecuta la demo de la presentación (Linux, macOS y Windows; solo biblioteca estándar).

    python demo.py preparar        crea .venv e instala dependencias (una vez)
    python demo.py ensayo          corre todos los pasos seguidos y mide el tiempo
    python demo.py demo            igual, pero espera Enter entre pasos (para el vivo)
    python demo.py schemathesis    contrato OpenAPI: CLI de Schemathesis contra un servidor temporal (única
                                   ejecución del contrato; en el CI es el primer job y su gate); abre el dashboard
    python demo.py schemathesis todos   ídem con todos los checks (44 hallazgos, ver informe §2)
    python demo.py schemathesis g3      solo endpoints de G3 (movimientos y categorías); combinable: g3 todos
    python demo.py dashboard       regenera reportes/dashboard-contrato.html con el último log de Schemathesis
                                   (y la comparativa con pytest-bdd si antes corrió `reporte`)
    python demo.py plan-b          pytest -rx guardando la salida en reportes/ensayo.txt (pregrabada)
    python demo.py reporte         pytest -rx y abre el reporte Allure (dashboard + escenarios); requiere Node (npx)
    python demo.py ci lanzar       Parte 2: lanza el pipeline en parte-2 y abre el run (al empezar la exposición)
    python demo.py ci              Parte 2: espera el último run y abre Pages, Allure web y la matriz (requiere gh;
                                   sin gh abre lo último publicado)
    python demo.py final           demo final de las 3 partes (~7 min), con Enter entre pasos: k6 (hora punta corta en
                                   Docker, :8001) arranca en segundo plano; API HU-G3-01 + DEF-07, contrato G3, web E2E
                                   (CP-W12 + HU-G3-01, Chrome visible), resultado de k6 e integridad, Allure y Pages
    python demo.py final ensayo    igual sin pausas; al final, tiempo por paso. HEADED= (vacío) corre Chrome oculto

En Windows, si `python` no existe, usar `py demo.py ...`. El paso 4 (contrato, ~50 s) es opcional:
SIN_CONTRATO=1 lo omite. PUERTO y VENV cambian puerto y entorno.
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


def esperar_enter(pausa):
    if pausa:
        try:
            input("(Enter para ejecutar) ")
        except EOFError:
            pass


TIEMPOS = []  # (paso, segundos) para el resumen de `final ensayo`


def paso(titulo, comando, env=None, pausa=False, cwd=RAIZ):
    print(f"\n=== {titulo}\n$ {' '.join(comando)}", flush=True)
    esperar_enter(pausa)
    t = time.monotonic()
    # los xfail/fallos esperados no deben cortar la demo
    rc = subprocess.call([herramienta(comando[0]), *comando[1:]], cwd=cwd, env={**ENV, **(env or {})})
    TIEMPOS.append((titulo, time.monotonic() - t))
    print(f"--- {titulo}: {TIEMPOS[-1][1]:.0f} s (rc={rc})")
    return rc


def pasos(pausa=False):
    paso("1. Escenarios de la historia HU-G3-01", ["pytest", "tests/api", "-m", "HU-G3-01", "-v"], pausa=pausa)
    paso("2. Todos los escenarios", ["pytest", "-rx", *ALLURE], pausa=pausa)
    if paso("3. Un defecto a la vista (DEF-07)", ["pytest", "tests/api", "-m", "DEF-07"],
            env={"MOSTRAR_DEFECTOS": "1"}, pausa=pausa):
        print("(esperado: los defectos fallan a la vista)")
    if os.environ.get("SIN_CONTRATO") != "1":
        print("\n=== 4. Contrato OpenAPI (CLI de Schemathesis)", flush=True)
        esperar_enter(pausa)
        schemathesis_cli([])
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
    schemathesis = herramienta("schemathesis")
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", PUERTO)) == 0:
            sys.exit(f"Puerto {PUERTO} ocupado: usa otro con la variable PUERTO")
    base = f"http://127.0.0.1:{PUERTO}"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        servidor = levantar_qolqe(PUERTO, Path(tmp) / "q.db")
        try:
            print(f"Contrato: {base}/docs  (Swagger)  ·  {base}/openapi.json", flush=True)
            login = urllib.request.Request(
                f"{base}/api/auth/login", data=json.dumps({"celular": "987654321", "pin": "4826"}).encode(),
                headers={"Content-Type": "application/json"})
            token = json.load(urllib.request.urlopen(login))["access_token"]
            # Se excluyen operaciones que invalidan la sesión o el reloj compartidos
            rc = subprocess.call([
                schemathesis, "run", f"{base}/openapi.json", "-H", f"Authorization: Bearer {token}",
                "--seed", "1", "--max-examples", "30", "--checks", checks, *incluir,
                "--exclude-path-regex",
                "/api/auth/logout|/api/seguridad/sesiones|/api/pruebas/reloj|/api/pruebas/reiniciar|/api/cuentas/me/cierre",
                "--report", "html,vcr,har,junit", "--report-dir", "reporte-schemathesis",
                "--report-junit-path", "reporte-schemathesis/junit-contrato.xml",], cwd=RAIZ, env=ENV)
        finally:
            servidor.terminate()
            servidor.wait()  # en Windows la BD sigue bloqueada hasta que el proceso muere
        if rc:  # DEF-15 (500 intermitente al repetir el registro) es defecto conocido; cualquier otra falla sigue en rojo
            sys.path.insert(0, str(RAIZ / ".github/scripts"))
            import reportes
            casos = reportes.pruebas(reportes.CONTRATO)
            fallas = [tc for tc in casos if reportes.estado(tc) != "pasa"]
            if fallas and all(reportes.def15(tc) for tc in fallas):
                print("Contrato: la única falla es DEF-15 (defecto conocido, docs/defectos.md): rc 0")
                rc = 0
    reportes = sorted((RAIZ / "reporte-schemathesis").glob("*/index.html"), key=lambda p: p.stat().st_mtime)
    if reportes:
        print(f"Reporte de Schemathesis: {reportes[-1]}")
    if not os.environ.get("CI"):  # en el CI el dashboard se arma en el job api, con los resultados BDD
        dashboard()
    return rc


def vivo(puerto):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/salud", timeout=1)
        return True
    except OSError:
        return False


def levantar_qolqe(puerto, bd):
    """uvicorn con una BD aparte en modo prueba; espera /api/salud. Quien llama lo termina."""
    servidor = subprocess.Popen(
        [herramienta("uvicorn"), "qolqe.main:app", "--port", str(puerto), "--log-level", "warning"], cwd=RAIZ,
        env={**ENV, "QOLQE_BD": str(bd), "QOLQE_MODO_PRUEBA": "1"})
    for _ in range(40):
        if servidor.poll() is not None:
            sys.exit(f"uvicorn no arrancó (¿puerto {puerto} ocupado?)")
        if vivo(puerto):
            return servidor
        time.sleep(0.5)
    servidor.terminate()
    sys.exit("uvicorn no respondió a tiempo")


def dashboard():
    """Dashboard propio con los logs VCR + HAR y la comparativa con pytest-bdd (si hay resultados Allure)."""
    if subprocess.call([herramienta("python"), "tests/dashboard/dashboard.py"], cwd=RAIZ, env=ENV) == 0:
        webbrowser.open((RAIZ / "reportes" / "dashboard-contrato.html").as_uri())


PAGES = "https://maykol-morales.github.io/cs5383-qolqe-wallet/"


def ci(args):
    """Demo de la Parte 2: run real del pipeline, reporte publicado y matriz. Sin gh, abre lo último publicado."""
    gh = shutil.which("gh")
    os.environ.setdefault("GH_REPO", "Maykol-Morales/cs5383-qolqe-wallet")  # hay dos remotos (origin y wdio)
    if gh:
        if "lanzar" in args:
            subprocess.check_call([gh, "workflow", "run", "pruebas.yml", "--ref", "parte-2"], cwd=RAIZ)
            time.sleep(5)  # ponytail: GitHub tarda unos segundos en listar el run nuevo
        run = json.loads(subprocess.check_output(
            [gh, "run", "list", "--workflow", "pruebas.yml", "--branch", "parte-2", "--limit", "1",
             "--json", "databaseId,number,url,status,conclusion"], cwd=RAIZ))[0]
        print(f"Run #{run['number']}: {run['status']} {run['conclusion'] or ''}\n{run['url']}", flush=True)
        webbrowser.open(run["url"])
        if "lanzar" in args:
            return print("El pipeline tarda ~7 min. En el slide de la demo: python demo.py ci")
        if run["status"] != "completed":
            subprocess.call([gh, "run", "watch", str(run["databaseId"]), "--exit-status"], cwd=RAIZ)
    else:
        print("Sin gh: se abre el último reporte publicado (plan B).")
    for ruta in ("", "web/", "trazabilidad.html"):
        print(PAGES + ruta)
        webbrowser.open(PAGES + ruta)


RENDIMIENTO = RAIZ / "tests" / "performance"


def k6_en_segundo_plano():
    """Parte 3: hora punta corta (2 min de rampa + DURACION) con correr.py contra Qolqe en Docker (:8001).
    Arranca primero porque es lo más largo; su salida va a reportes/k6-final.log."""
    sys.path.insert(0, str(RENDIMIENTO))
    import correr
    k6 = shutil.which("k6") or shutil.which("k6", path=str(Path.home() / ".local" / "bin"))
    if not (k6 and shutil.which("docker")) or subprocess.call(["docker", "info"], stdout=subprocess.DEVNULL,
                                                              stderr=subprocess.DEVNULL):
        print("Parte 3 omitida: faltan k6 o Docker encendido (ver tests/performance/README.md). Plan B: "
              f"{RENDIMIENTO / 'resultados' / 'carga-20261112-0747-ec2' / 'dashboard.html'}")
        return None
    if not correr.contenedor_activo():
        print(f"Iniciando el contenedor {correr.CONTENEDOR}…", flush=True)
        if subprocess.call(["docker", "start", correr.CONTENEDOR], stdout=subprocess.DEVNULL):
            subprocess.check_call([herramienta("python"), str(RENDIMIENTO / "correr.py"), "levantar"], cwd=RAIZ)
    correr.esperar_servidor()
    (RAIZ / "reportes").mkdir(exist_ok=True)
    log = open(RAIZ / "reportes" / "k6-final.log", "w", encoding="utf-8")
    env = {**ENV, "PATH": f"{Path(k6).parent}{os.pathsep}{ENV['PATH']}", "USUARIOS": "120",
           "DURACION": os.environ.get("DURACION", "1m"), "ETIQUETA": "demo-final"}
    proceso = subprocess.Popen([herramienta("python"), str(RENDIMIENTO / "correr.py"), "carga"], cwd=RAIZ, env=env,
                               stdout=log, stderr=subprocess.STDOUT)
    print(f"k6 corriendo en segundo plano (hora punta, 120 usuarios, 2 min + {env['DURACION']}): "
          f"dashboard en vivo http://localhost:5665 · salida en {log.name}", flush=True)
    return proceso


def final(args):
    """Demo final de las 3 partes. `final ensayo` sin pausas y con tiempos por paso."""
    pausa = "ensayo" not in args
    inicio = time.monotonic()
    print("=== 0. Rendimiento: arranca k6 en segundo plano (se ve en el paso 4)", flush=True)
    esperar_enter(pausa)
    k6 = k6_en_segundo_plano()
    if k6:
        time.sleep(3)  # ponytail: tiempo para que k6 abra el dashboard antes de abrir el navegador
        webbrowser.open("http://localhost:5665")

    paso("1a. API: escenarios de HU-G3-01 (pytest-bdd)", ["pytest", "tests/api", "-m", "HU-G3-01", *ALLURE],
         pausa=pausa)
    if paso("1b. API: defecto a la vista (DEF-07, el historial excluye el día `hasta`)",
            ["pytest", "tests/api", "-m", "DEF-07"], env={"MOSTRAR_DEFECTOS": "1"}, pausa=pausa):
        print("(esperado: rc=1 a propósito, el defecto falla a la vista)")

    if os.environ.get("SIN_CONTRATO") != "1":
        print("\n=== 2. Contrato OpenAPI de G3 (CLI de Schemathesis)", flush=True)
        esperar_enter(pausa)
        t = time.monotonic()
        schemathesis_cli(["g3"])
        TIEMPOS.append(("2. Contrato G3", time.monotonic() - t))

    servidor = None
    if not vivo(8000):  # la UI se prueba contra :8000 (wdio.conf.js); si ya hay un Qolqe ahí, se reusa
        servidor = levantar_qolqe(8000, Path(tempfile.gettempdir()) / "qolqe-demo-final.db")
    try:
        e2e = RAIZ / "tests" / "e2e"
        paso("3. Web E2E: transferencia (CP-W12) e historial (HU-G3-01) en Chrome",
             [shutil.which("npx") or "npx", "wdio", "run", "wdio.conf.js", "--spec", "features/nucleo.feature",
              "--spec", "features/historial.feature", "--cucumberOpts.tags=@CP-W12 or @HU-G3-01"],
             env={"HEADED": os.environ.get("HEADED", "1")}, pausa=pausa, cwd=e2e)
    finally:
        if servidor:
            servidor.terminate()
            servidor.wait()

    if k6:
        print("\n=== 4. Rendimiento: resultado de k6 (umbrales e integridad)", flush=True)
        esperar_enter(pausa)
        t = time.monotonic()
        rc = k6.wait()
        TIEMPOS.append(("4. Espera a k6", time.monotonic() - t))
        salida = (RAIZ / "reportes" / "k6-final.log").read_text(encoding="utf-8", errors="replace")
        print(salida[salida.rfind("THRESHOLDS"):] if "THRESHOLDS" in salida else salida[-3000:])
        carpeta = max((RENDIMIENTO / "resultados").glob("carga-*-demo-final"), key=lambda p: p.stat().st_mtime)
        # integridad.txt aparte: la salida de `docker exec` llega al log desordenada respecto de la de correr.py
        print(*(carpeta / "integridad.txt").read_text(encoding="utf-8").strip().splitlines()[-2:], sep="\n")
        print(f"(k6 salió con rc={rc}: 0 = todos los umbrales en verde) · resultados en {carpeta}")
        for archivo in ("dashboard.html", "k6.png", "recursos.png"):
            webbrowser.open((carpeta / archivo).as_uri())

    print("\n=== 5. Reportes", flush=True)
    esperar_enter(pausa)
    allure()
    print(f"Web E2E (Allure crudo): {RAIZ / 'tests' / 'e2e' / 'reportes' / 'allure-results'}\nPages: {PAGES}")
    webbrowser.open(PAGES)
    if not pausa:
        print("\nTiempos del ensayo:")
        for titulo, s in TIEMPOS:
            print(f"  {s:6.0f} s  {titulo}")
        print(f"  {time.monotonic() - inicio:6.0f} s  TOTAL")


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
        "schemathesis": lambda: sys.exit(schemathesis_cli(resto)),
        "plan-b": plan_b,
        "reporte": reporte,
        "dashboard": dashboard,
        "ci": lambda: ci(resto),
        "final": lambda: final(resto),
    }
    acciones.get(orden, lambda: print(__doc__))()
