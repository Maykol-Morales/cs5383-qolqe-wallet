"""CPU y memoria cada segundo, a un CSV (script del enunciado §5, con la salida como argumento).

Uso:
  python monitor.py <PID> <salida.csv>                 proceso del sistema (k6); memoria = RSS
  python monitor.py --docker <contenedor> <salida.csv> contenedor (Qolqe); sirve en Windows, macOS y Linux
Se detiene con Ctrl+C o al terminar el proceso.

Con Docker Desktop (Windows/macOS) el proceso de Qolqe vive dentro de una máquina virtual y psutil no lo ve:
se mide con `docker stats`. Su CPU es el % de un núcleo (con --cpus=1 llega a 100) y su memoria es la del
cgroup del contenedor (incluye la caché de archivos, algo más que el RSS)."""
import csv
import re
import subprocess
import sys
import threading
import time

UNIDADES = {"B": 1e-6, "KB": 1e-3, "KIB": 1.024e-3, "MB": 1.0, "MIB": 1.048576, "GB": 1e3, "GIB": 1073.741824}


def a_mb(texto: str) -> float:
    """'67.5MiB' → 70.8 (MB)."""
    numero, unidad = re.match(r"([\d.]+)\s*([A-Za-z]+)", texto.strip()).groups()
    return float(numero) * UNIDADES[unidad.upper()]


def monitorear_docker(contenedor: str, salida: str) -> None:
    ultima = {"cpu": 0.0, "mem": 0.0, "fin": False}

    def leer():
        # `docker stats` emite una línea por contenedor cada ~1-2 s; aquí solo se guarda la última.
        proceso = subprocess.Popen(["docker", "stats", "--format", "{{.CPUPerc}}|{{.MemUsage}}", contenedor],
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        for linea in proceso.stdout:
            linea = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", linea).strip()  # códigos de pantalla si hay terminal
            if "|" not in linea:
                continue
            cpu, memoria = linea.split("|")
            try:
                ultima["cpu"], ultima["mem"] = float(cpu.strip().rstrip("%")), a_mb(memoria.split("/")[0])
            except (ValueError, AttributeError):
                continue
        ultima["fin"] = True

    threading.Thread(target=leer, daemon=True).start()
    espera = time.time() + 15
    while ultima["mem"] == 0 and not ultima["fin"] and time.time() < espera:  # primera muestra de docker stats
        time.sleep(0.2)
    escribir(salida, lambda: (ultima["cpu"], round(ultima["mem"], 1)), lambda: ultima["fin"])


def monitorear_proceso(pid: int, salida: str) -> None:
    import psutil

    p = psutil.Process(pid)
    p.cpu_percent(None)

    def muestra():
        try:
            return p.cpu_percent(None), round(p.memory_info().rss / 1e6, 1)
        except psutil.NoSuchProcess:
            return None

    escribir(salida, muestra, lambda: False)


def escribir(salida: str, muestra, terminado) -> None:
    with open(salida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hora", "cpu_%", "memoria_MB"])
        while not terminado():
            time.sleep(1)
            m = muestra()
            if m is None:  # el proceso medido terminó
                break
            w.writerow([time.strftime("%H:%M:%S"), *m])
            f.flush()


if __name__ == "__main__":
    try:
        if sys.argv[1] == "--docker":
            monitorear_docker(sys.argv[2], sys.argv[3])
        else:
            monitorear_proceso(int(sys.argv[1]), sys.argv[2])
    except KeyboardInterrupt:
        pass
