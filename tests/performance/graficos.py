"""Tablas y gráficos de una corrida: python graficos.py <dir>
Lee k6.json.gz y recursos-*.csv; deja por-minuto.csv (escalones del estrés), por-endpoint.csv, k6.png y recursos.png."""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def p95(valores):
    return sorted(valores)[int(len(valores) * 0.95)] if valores else 0


def leer(ruta):
    minutos = defaultdict(lambda: {"vus": 0, "reqs": 0, "fallas": 0, "consulta": [], "dinero": []})
    endpoints = defaultdict(list)
    with gzip.open(ruta, "rt") as f:
        for linea in f:
            if '"type":"Point"' not in linea:
                continue
            d = json.loads(linea)
            m, dato = d["metric"], d["data"]
            minuto, tags = dato["time"][11:16], dato.get("tags", {})
            if m == "vus":
                minutos[minuto]["vus"] = max(minutos[minuto]["vus"], dato["value"])
            elif m == "http_reqs":
                minutos[minuto]["reqs"] += 1
                minutos[minuto]["fallas"] += tags.get("expected_response") == "false"
            elif m == "http_req_duration":
                minutos[minuto][tags.get("tipo", "consulta")].append(dato["value"])
                endpoints[tags.get("name", "?")].append(dato["value"])
    return dict(sorted(minutos.items())), endpoints


def main(directorio: Path):
    minutos, endpoints = leer(directorio / "k6.json.gz")
    filas = [{"minuto": k, "vus": int(v["vus"]), "req_s": round(v["reqs"] / 60, 2),
              "p95_consulta_ms": round(p95(v["consulta"])), "p95_dinero_ms": round(p95(v["dinero"])),
              "fallas_%": round(100 * v["fallas"] / v["reqs"], 2) if v["reqs"] else 0} for k, v in minutos.items()]
    with open(directorio / "por-minuto.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=filas[0].keys())
        w.writeheader()
        w.writerows(filas)
    with open(directorio / "por-endpoint.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["endpoint", "peticiones", "p95_ms", "max_ms"])
        for nombre, v in sorted(endpoints.items(), key=lambda e: -p95(e[1])):
            w.writerow([nombre, len(v), round(p95(v)), round(max(v))])

    x = [f["minuto"] for f in filas]
    fig, ejes = plt.subplots(4, 1, figsize=(11, 10), sharex=True)
    ejes[0].plot(x, [f["p95_consulta_ms"] for f in filas], label="p95 consultas")
    ejes[0].plot(x, [f["p95_dinero_ms"] for f in filas], label="p95 dinero")
    umbral = 2 if directorio.name.startswith("pico") else 1  # mismos umbrales que qolqe.js
    ejes[0].axhline(800 * umbral, ls="--", c="C0", lw=0.8)
    ejes[0].axhline(1500 * umbral, ls="--", c="C1", lw=0.8)
    ejes[0].set_ylabel("ms")
    ejes[0].legend()
    for eje, clave, titulo in zip(ejes[1:], ["req_s", "fallas_%", "vus"], ["peticiones/s", "fallas técnicas %", "VUs"]):
        eje.plot(x, [f[clave] for f in filas])
        eje.set_ylabel(titulo)
    ejes[-1].tick_params(axis="x", rotation=90, labelsize=7)
    fig.suptitle(directorio.name)
    fig.tight_layout()
    fig.savefig(directorio / "k6.png", dpi=110)

    recursos = sorted(directorio.glob("recursos-*.csv"))
    if recursos:
        fig, (cpu, mem) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
        for ruta in recursos:
            datos = [d for d in csv.DictReader(open(ruta)) if float(d["memoria_MB"]) > 0]  # sin muestra todavía
            cpu.plot([float(d["cpu_%"]) for d in datos], label=ruta.stem.removeprefix("recursos-"))
            mem.plot([float(d["memoria_MB"]) for d in datos], label=ruta.stem.removeprefix("recursos-"))
        cpu.set_ylabel("CPU %")
        mem.set_ylabel("RSS MB")
        mem.set_xlabel("segundos")
        cpu.legend()
        fig.tight_layout()
        fig.savefig(directorio / "recursos.png", dpi=110)
    print(f"Gráficos y tablas en {directorio}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
