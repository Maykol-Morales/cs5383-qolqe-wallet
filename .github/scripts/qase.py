"""Sube el run de CI a Qase (gestión de casos): sincroniza los casos y crea un test run con un resultado por caso.

    QASE_API_TOKEN=... python .github/scripts/qase.py           sube a Qase (proyecto QASE_PROJECT, por defecto QOLQE)
    python .github/scripts/qase.py --seco                       imprime las peticiones (JSON) sin enviarlas

Sin QASE_API_TOKEN avisa, hace la prueba en seco y sale con 0: el pipeline no depende de la cuenta.
Los casos salen de reportes.casos_con_resultados() (mismos .feature y JUnit que la matriz). En Qase el título empieza
por nuestro ID (`CP-A-historial-03 · …`, `CP-W01 · …`): así se reconoce un caso ya creado. Las etiquetas @HU-… y
@DEF-nn y el nivel van como tags. Resultado por caso, como en la matriz: pasa → passed, defecto conocido → failed
con defect=true, falla → failed, omitido → skipped. Ver docs/gestion-casos.md.
"""
import itertools
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import reportes  # noqa: E402

API = "https://api.qase.io/v1"
TOKEN, PROYECTO = os.environ.get("QASE_API_TOKEN"), os.environ.get("QASE_PROJECT", "QOLQE")
SECO = "--seco" in sys.argv or not TOKEN
FALSOS = itertools.count(1)  # ids simulados en seco
ESTADO = {"pasa": "passed", "defecto": "failed", "falla": "failed", "otro": "skipped"}


def api(metodo, ruta, cuerpo=None):
    if SECO:
        print(json.dumps({"metodo": metodo, "url": f"{API}{ruta}", "cuerpo": cuerpo}, ensure_ascii=False, indent=1))
        n = len(cuerpo["cases"]) if ruta.endswith("/bulk") and "cases" in (cuerpo or {}) else 0
        return {"total": 0, "entities": [], "ids": [next(FALSOS) for _ in range(n)], "id": 0}  # respuesta simulada
    pet = urllib.request.Request(f"{API}{ruta}", method=metodo, data=json.dumps(cuerpo).encode() if cuerpo else None,
                                 headers={"Token": TOKEN, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(pet, timeout=30) as r:
            return json.load(r).get("result", {})
    except urllib.error.HTTPError as e:
        sys.exit(f"Qase {metodo} {ruta}: {e.code} {e.read().decode(errors='replace')[:500]}")


def ids_existentes():
    """{nuestro ID: id de Qase}, leyendo todos los casos del proyecto (páginas de 100)."""
    salida, offset = {}, 0
    while True:
        r = api("GET", f"/case/{PROYECTO}?limit=100&offset={offset}")
        for e in r["entities"]:
            salida[e["title"].split(" · ")[0]] = e["id"]
        offset += 100
        if offset >= r["total"]:
            return salida


def main():
    if not TOKEN:
        reportes.aviso("Sin QASE_API_TOKEN: no se sube a Qase (prueba en seco).")
    run = reportes.datos_run()
    casos = [c for c in reportes.casos_con_resultados() if c["ejecuciones"]]
    qase = ids_existentes()

    nuevos = [c for c in casos if c["id"] not in qase]
    # Creación en lote: "isManual": 0 = automatizado (probado 2026-11-11; "automation" y false se ignoran o rechazan aquí)
    if nuevos:  # ponytail: no actualiza título ni tags de casos ya creados; se editan en Qase o se borran para recrearlos
        cuerpo = [{"title": f"{c['id']} · {c['nombre']}"[:255], "tags": c["hu"] + c["defs"] + [c["nivel"]],
                   "description": f"Escenario de {c['archivo']}", "isManual": 0} for c in nuevos]
        for i in range(0, len(cuerpo), 100):
            ids = api("POST", f"/case/{PROYECTO}/bulk", {"cases": cuerpo[i:i + 100]})["ids"]
            qase.update(zip((c["id"] for c in nuevos[i:i + 100]), ids))

    run_id = api("POST", f"/run/{PROYECTO}", {
        "title": f"CI run #{run['numero']} · {run['corto']} {run['rama']}".strip(), "is_autotest": True,
        "description": f"{run['url'] or 'Corrida local'}\nCommit {run['commit']}", "cases": [qase[c["id"]] for c in casos],
        "tags": [t for t in (run["rama"],) if t]})["id"]

    resultados = []
    for c in casos:
        res = reportes.resultado(c)
        k = reportes.clase(res)
        resultados.append({"case_id": qase[c["id"]], "status": ESTADO[k], "defect": k == "defecto",
                           "comment": f"{res} · {len(c['ejecuciones'])} ejecución(es) · {run['url'] or 'local'}"})
    try:
        for i in range(0, len(resultados), 200):  # máximo 200 por petición
            api("POST", f"/result/{PROYECTO}/{run_id}/bulk", {"results": resultados[i:i + 200]})
    finally:  # se cierra aunque falle la subida: el plan gratuito admite solo 2 runs activos
        api("POST", f"/run/{PROYECTO}/{run_id}/complete")
    print(f"Qase: {len(nuevos)} casos nuevos, run {run_id} con {len(resultados)} resultados"
          + (" (en seco)" if SECO else f" → https://app.qase.io/run/{PROYECTO}/dashboard/{run_id}"), file=sys.stderr)


if __name__ == "__main__":
    main()
