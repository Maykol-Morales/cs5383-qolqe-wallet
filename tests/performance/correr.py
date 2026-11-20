"""Pruebas de rendimiento de Qolqe en Docker, en Windows, macOS y Linux (reemplaza a correr.sh).

Uso, desde cualquier carpeta del repo (en Windows: py tests/performance/correr.py ...):
  correr.py levantar            construye la imagen y crea el contenedor qolqe-rend (1 CPU, 1 GB)
  correr.py humo|carga|pico|estres   prepara datos, mide recursos, corre k6, verifica la integridad y grafica
  correr.py parar               detiene y borra el contenedor

Variables de entorno: USUARIOS (1000), DURACION, FLUJOS, TOPE, PASO (pasan a k6), ETIQUETA (sufijo del
directorio de resultados), QOLQE_URL (http://localhost:8001), CONTENEDOR (qolqe-rend).
Sale con el código de k6 (distinto de 0 si se incumple un umbral).

Qolqe corre en el contenedor y k6 en el equipo. Los datos de prueba y la verificación de integridad leen y
escriben la base SQLite, que vive en un volumen de Docker: por eso `datos.py` se ejecuta dentro del contenedor
(en Windows y macOS la base queda dentro de la máquina virtual de Docker y no se puede abrir desde el equipo).
Requisitos en el equipo: Docker (encendido), k6 >= 1.0, Python 3 con `pip install psutil matplotlib`."""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
CONTENEDOR = os.getenv("CONTENEDOR", "qolqe-rend")
IMAGEN = "qolqe-rendimiento"
VOLUMEN = "qolqe-rend-bd"
URL = os.getenv("QOLQE_URL", "http://localhost:8001")
PUERTO = URL.rsplit(":", 1)[-1]
EN_CONTENEDOR = "/tmp/rend"  # allí se copia datos.py; PYTHONPATH=/app trae el paquete qolqe de la imagen


def ejecutar(*cmd, capturar=False, **kw):
    return subprocess.run([str(c) for c in cmd], text=True, capture_output=capturar, **kw)


def salir(mensaje: str, codigo: int = 1):
    print(f"Error: {mensaje}", file=sys.stderr)
    sys.exit(codigo)


def revisar_requisitos(necesita_k6: bool):
    if not shutil.which("docker"):
        salir("no encuentro `docker` en el PATH. Instala Docker Desktop.")
    if ejecutar("docker", "info", capturar=True).returncode != 0:
        salir("el motor de Docker no responde. Abre Docker Desktop y espera a que diga 'Engine running'.")
    if necesita_k6 and not shutil.which("k6"):
        salir("no encuentro `k6` en el PATH. Windows: `winget install k6 --source winget`; macOS: `brew install k6`.")
    try:
        import matplotlib  # noqa: F401
        import psutil  # noqa: F401
    except ImportError:
        salir(f"faltan módulos de Python: `{Path(sys.executable).name} -m pip install psutil matplotlib`.")


def contenedor_activo() -> bool:
    r = ejecutar("docker", "inspect", "-f", "{{.State.Running}}", CONTENEDOR, capturar=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def levantar():
    revisar_requisitos(necesita_k6=False)
    print("Construyendo la imagen…")
    if ejecutar("docker", "build", "-f", AQUI / "Dockerfile", "-t", IMAGEN, RAIZ).returncode != 0:
        salir("falló `docker build`.")
    ejecutar("docker", "rm", "-f", CONTENEDOR, capturar=True)
    # Un solo proceso (el reloj de modo prueba está en memoria) y la base en un volumen del propio Docker.
    r = ejecutar("docker", "run", "-d", "--name", CONTENEDOR, "--cpus=1", "--memory=1g", "-p", f"{PUERTO}:8000",
                 "-v", f"{VOLUMEN}:/bd", "-e", "QOLQE_BD=/bd/qolqe.db", "-e", "QOLQE_BD_PLANTILLA=/bd/plantilla_carga.db",
                 IMAGEN, capturar=True)
    if r.returncode != 0:
        salir(r.stderr.strip())
    esperar_servidor()
    print(f"Qolqe en {URL} (contenedor {CONTENEDOR}: 1 CPU, 1 GB).")


def esperar_servidor():
    import urllib.request
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{URL}/docs", timeout=2)
            return
        except OSError:
            time.sleep(1)
    salir(f"Qolqe no responde en {URL}. Mira `docker logs {CONTENEDOR}`.")


def datos(accion: str, *args):
    """Corre datos.py dentro del contenedor (donde está la base)."""
    ejecutar("docker", "exec", CONTENEDOR, "mkdir", "-p", f"{EN_CONTENEDOR}/tests/performance/out")
    ejecutar("docker", "cp", AQUI / "datos.py", f"{CONTENEDOR}:{EN_CONTENEDOR}/tests/performance/datos.py", check=True)
    return ejecutar("docker", "exec", "-e", "PYTHONPATH=/app", "-e", "QOLQE_URL=http://localhost:8000", CONTENEDOR, "python",
                    f"{EN_CONTENEDOR}/tests/performance/datos.py", accion, f"{EN_CONTENEDOR}/tests/performance/out", *args).returncode


def correr(prueba: str):
    revisar_requisitos(necesita_k6=True)
    if not contenedor_activo():
        salir(f"el contenedor {CONTENEDOR} no está corriendo. Primero: correr.py levantar")
    usuarios = os.getenv("USUARIOS", "1000")
    nombre = f"{prueba}-{time.strftime('%Y%m%d-%H%M')}-docker" + (f"-{os.environ['ETIQUETA']}" if os.getenv("ETIQUETA") else "")
    directorio = AQUI / "resultados" / nombre
    directorio.mkdir(parents=True, exist_ok=True)

    if datos("preparar", usuarios) != 0:
        salir("no se pudieron preparar los datos.")
    ejecutar("docker", "cp", f"{CONTENEDOR}:{EN_CONTENEDOR}/tests/performance/out/foto.json", directorio / "foto.json", check=True)

    entorno = {**os.environ, "K6_WEB_DASHBOARD": "true", "K6_WEB_DASHBOARD_EXPORT": str(directorio / "dashboard.html"),
               "USUARIOS": usuarios}
    k6_args = ["k6", "run", "-e", f"PRUEBA={prueba}", "-e", f"QOLQE_URL={URL}"]
    for variable in ("USUARIOS", "DURACION", "FLUJOS", "TOPE", "PASO"):
        if os.getenv(variable):
            k6_args += ["-e", f"{variable}={os.environ[variable]}"]
    k6_args += ["--out", f"json={directorio / 'k6.json.gz'}", "--summary-export", str(directorio / "summary.json"),
                str(AQUI / "qolqe.js")]

    monitor = [sys.executable, str(AQUI / "monitor.py")]
    mon_qolqe = subprocess.Popen([*monitor, "--docker", CONTENEDOR, str(directorio / "recursos-qolqe.csv")])
    (directorio / "horario.txt").write_text(f"inicio {time.strftime('%H:%M:%S')}\n")
    k6 = subprocess.Popen(k6_args, env=entorno, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="replace")
    mon_k6 = subprocess.Popen([*monitor, str(k6.pid), str(directorio / "recursos-k6.csv")])
    try:
        with open(directorio / "k6.txt", "w", encoding="utf-8") as registro:
            for linea in k6.stdout:  # k6 a la pantalla y al archivo a la vez
                sys.stdout.write(linea)
                registro.write(linea)
        rc = k6.wait()
    except KeyboardInterrupt:
        k6.terminate()
        rc = k6.wait()
    with open(directorio / "horario.txt", "a") as f:
        f.write(f"fin {time.strftime('%H:%M:%S')}\n")
    for m in (mon_qolqe, mon_k6):
        m.terminate()
    for m in (mon_qolqe, mon_k6):
        m.wait()

    ejecutar("docker", "cp", directorio / "k6.json.gz", f"{CONTENEDOR}:{EN_CONTENEDOR}/tests/performance/out/k6.json.gz", check=True)
    ejecutar("docker", "cp", directorio / "foto.json", f"{CONTENEDOR}:{EN_CONTENEDOR}/tests/performance/out/foto.json", check=True)
    datos("verificar")
    ejecutar("docker", "cp", f"{CONTENEDOR}:{EN_CONTENEDOR}/tests/performance/out/integridad.txt", directorio / "integridad.txt")
    ejecutar(sys.executable, AQUI / "graficos.py", directorio)
    print(f"Resultados en {directorio} (k6 salió con {rc})")
    sys.exit(rc)


def parar():
    revisar_requisitos(necesita_k6=False)
    ejecutar("docker", "rm", "-f", CONTENEDOR)


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden == "levantar":
        levantar()
    elif orden == "parar":
        parar()
    elif orden in ("humo", "carga", "pico", "estres"):
        correr(orden)
    else:
        print(__doc__)
        sys.exit(2)
