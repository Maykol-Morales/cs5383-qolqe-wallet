"""Dashboard de Schemathesis (logs VCR + HAR) y comparativa con los escenarios pytest-bdd (resultados Allure).

    python tests/dashboard/dashboard.py [vcr.yaml] [har.json]   →  reportes/dashboard-contrato.html

Sin argumentos toma el VCR más reciente de reporte-schemathesis/ y su HAR (mismo sello de tiempo).
La comparativa usa reportes/allure-results/ (python demo.py reporte); si no existe, se omite.
Cada caso se reduce a (operación, estado HTTP, código de error): es la unidad que se compara.
"""
import json
import os
import re
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import jsonschema_rs
import yaml

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "reportes" / "dashboard-contrato.html"
FASES = {"examples": "Ejemplos del esquema", "coverage": "Cobertura (límites y tipos)",
         "fuzzing": "Fuzzing (aleatorio)", "stateful": "Con estado (encadenados)"}
MODULOS = [("/api/auth", "Núcleo"), ("/api/usuarios", "Núcleo"), ("/api/cuentas", "Núcleo"),
           ("/api/transferencias", "Núcleo"), ("/api/movimientos", "G3"), ("/api/categorias", "G3"),
           ("/api/recargas", "G1"), ("/api/servicios", "G2"), ("/api/contactos", "G4"), ("/api/solicitudes", "G4"),
           ("/api/limites", "G5"), ("/api/seguridad", "G6"), ("/api/pruebas", "Soporte"), ("/api/salud", "Soporte")]
# Pasos Then que solo miran el estado HTTP y el código de error (no el contenido de negocio)
THEN_GENERICOS = {"la respuesta es #", "la respuesta es # con el código #", "la operación es #"}


def modulo(ruta):
    return next((m for prefijo, m in MODULOS if ruta.startswith(prefijo)), "Otro")


def contrato():
    """Operaciones documentadas, función (método, url) → operación y función que dice qué restricciones
    del OpenAPI viola una petición (cuerpo, query, ruta y seguridad)."""
    os.environ.setdefault("QOLQE_BD", os.path.join(tempfile.mkdtemp(prefix="qolqe-dash-"), "q.db"))
    sys.path.insert(0, str(RAIZ))
    from qolqe.main import app
    rutas = app.openapi()["paths"]
    plantillas = sorted(rutas, key=lambda p: (p.count("{"), -len(p)))  # literales antes que {parámetros}
    patrones = [(p, re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", p) + "$")) for p in plantillas]
    documentadas = {f"{m.upper()} {p}" for p, ops in rutas.items() for m in ops}

    def operacion(metodo, url):
        ruta = urlsplit(url).path
        plantilla = next((p for p, rx in patrones if rx.match(ruta)), ruta)
        return f"{metodo.upper()} {plantilla}"

    componentes = app.openapi().get("components", {})

    def esquema_de(propiedades, requeridos):
        return {"type": "object", "properties": propiedades, "required": requeridos, "components": componentes}

    def viola(op, url, cuerpo, con_token):
        metodo, plantilla = op.split(" ", 1)
        spec = rutas.get(plantilla, {}).get(metodo.lower())
        if spec is None:
            return ["operación no documentada"]
        motivos = []
        if spec.get("security") and not con_token:
            motivos.append("seguridad: falta Authorization")
        partes = urlsplit(url)
        valores = {"query": dict(parse_qsl(partes.query, keep_blank_values=True)), "path": {}}
        nombres = re.findall(r"\{([^}]+)\}", plantilla)
        if nombres:
            valores["path"] = dict(zip(nombres, re.match("^" + re.sub(r"\{[^}]+\}", "([^/]+)", plantilla) + "$",
                                                          partes.path).groups()))
        for lugar in ("query", "path"):
            parametros = [p for p in spec.get("parameters", []) if p["in"] == lugar]
            instancia = {}
            for p in parametros:
                if p["name"] in valores[lugar]:
                    texto, tipos = valores[lugar][p["name"]], json.dumps(p["schema"])
                    try:  # los parámetros llegan como texto: se convierten al tipo declarado
                        instancia[p["name"]] = int(texto) if '"integer"' in tipos else float(texto) if '"number"' in tipos else texto
                    except ValueError:
                        instancia[p["name"]] = texto
            esquema = esquema_de({p["name"]: p["schema"] for p in parametros}, [p["name"] for p in parametros if p.get("required")])
            motivos += [f"{lugar}.{'.'.join(map(str, e.instance_path)) or '*'}: {e.schema_path[-1]}"
                        for e in jsonschema_rs.validator_for(esquema, validate_formats=True).iter_errors(instancia)]
        cuerpo_spec = spec.get("requestBody", {}).get("content", {}).get("application/json")
        if cuerpo_spec:
            try:
                instancia = json.loads(cuerpo) if cuerpo else None
            except ValueError:
                instancia = cuerpo
            if instancia is None:
                if spec["requestBody"].get("required"):
                    motivos.append("body: falta el cuerpo")
            else:
                esquema = {**cuerpo_spec["schema"], "components": componentes}
                motivos += [f"body.{'.'.join(map(str, e.instance_path)) or '*'}: {e.schema_path[-1]}"
                            for e in jsonschema_rs.validator_for(esquema, validate_formats=True).iter_errors(instancia)]
        return sorted(set(motivos))
    return documentadas, operacion, viola


def codigo_error(texto):
    try:
        cuerpo = json.loads(texto or "")
    except ValueError:
        return ""
    return cuerpo.get("codigo", "") if isinstance(cuerpo, dict) else ""


def recortar(texto, n=240):
    texto = (texto or "").strip()
    return texto if len(texto) <= n else texto[:n] + "…"


def schemathesis(vcr, har, operacion):
    datos = yaml.load(vcr.read_text(encoding="utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    tiempos = {}
    for e in json.loads(har.read_text(encoding="utf-8"))["log"]["entries"]:
        caso = next((h["value"] for h in e["request"]["headers"] if h["name"] == "X-Schemathesis-TestCaseId"), None)
        tiempos[caso] = (e["time"], e["response"]["bodySize"])
    casos = []
    for i in datos["http_interactions"]:
        resp, req = i.get("response") or {}, i["request"]
        cuerpo = (resp.get("body") or {}).get("string", "")
        ms, tam = tiempos.get(i["id"], (float(resp.get("elapsed", 0)) * 1000, len(cuerpo)))
        fase = i["phase"]
        casos.append({
            "id": i["id"], "op": operacion(req["method"], req["uri"]), "fase": fase["name"],
            "modo": i["generation"]["mode"], "estado": int(resp["status"]["code"]) if resp else 0,
            "codigo": codigo_error(cuerpo), "ms": round(ms, 1), "bytes": tam, "resultado": i["status"],
            "desc": (fase.get("data") or {}).get("description", ""), "param": (fase.get("data") or {}).get("parameter") or "",
            "checks": {c["name"]: c["status"] for c in i["checks"]},
            "fallos": [f"{c['name']}: {c['message']}" for c in i["checks"] if c["status"] != "SUCCESS"],
            "url": urlsplit(req["uri"]).path + (f"?{urlsplit(req['uri']).query}" if urlsplit(req["uri"]).query else ""),
            "metodo": req["method"], "envio": recortar((req.get("body") or {}).get("string", "")), "respuesta": recortar(cuerpo),
        })
    marcas = sorted(i["recorded_at"] for i in datos["http_interactions"])
    from datetime import datetime
    duracion = (datetime.fromisoformat(marcas[-1]) - datetime.fromisoformat(marcas[0])).total_seconds() if marcas else 0
    return datos.get("command", ""), datos.get("seed"), casos, round(duracion)


def bdd(carpeta, operacion, viola):
    """Escenarios pytest-bdd con las peticiones HTTP de sus pasos When y el tipo de sus pasos Then."""
    escenarios = []
    for archivo in sorted(carpeta.glob("*-result.json")):
        r = json.loads(archivo.read_text(encoding="utf-8"))
        etiquetas = {l["name"]: l["value"] for l in r["labels"] if l["name"] in ("epic", "story", "feature")}
        defs = sorted(l["value"] for l in r["labels"] if l["name"] == "tag" and l["value"].startswith("DEF-"))
        cuando, entonces, clave = [], [], None
        for paso in r["steps"]:
            palabra, texto = (paso["name"].split(" ", 1) + [""])[:2]
            clave = clave if palabra in ("And", "But") else palabra
            if clave == "Then":
                entonces.append(re.sub(r'"[^"]*"|\d+(?:\.\d+)?', "#", texto))
            if clave != "When":
                continue
            for adjunto in paso.get("attachments", []):
                contenido = (carpeta / adjunto["source"]).read_text(encoding="utf-8")
                linea, _, resto = contenido.partition("\n")
                peticion, _, token = linea.partition(" · ")
                metodo, url = peticion.split(" ", 1)
                enviado, _, respuesta = resto.partition("\n\n← ")
                estado, _, cuerpo = respuesta.partition("\n")
                op = operacion(metodo, url)
                cuando.append({"op": op, "estado": int(estado), "codigo": codigo_error(cuerpo),
                               "url": urlsplit(url).path + (f"?{urlsplit(url).query}" if urlsplit(url).query else ""),
                               "envio": recortar(enviado), "viola": viola(op, url, enviado, token != "sin token")})
        escenarios.append({
            "nombre": r["name"], "feature": etiquetas.get("feature", ""), "hu": etiquetas.get("story", ""),
            "modulo": "Núcleo" if etiquetas.get("epic") == "Núcleo" else "G3", "estado": r["status"], "defs": defs,
            "params": ", ".join(f"{p['name']}={p['value']}" for p in r.get("parameters", [])),
            "cuando": cuando, "entonces": entonces})
    return escenarios


def p95(valores):
    return round(statistics.quantiles(valores, n=20)[-1], 1) if len(valores) > 1 else (valores or [0])[0]


def coincide(violacion, caso):
    """¿El caso de Schemathesis atacó la misma restricción? (por la descripción de la fase de cobertura)"""
    if violacion.startswith("seguridad"):
        return "Authorization" in caso["desc"]
    if violacion.endswith(("required", "falta el cuerpo")):
        return caso["desc"].startswith(("Missing required", "Missing request body"))
    campo = violacion.split(":")[0].split(".")[-1]
    return caso["modo"] == "negative" and (caso["param"] == campo or caso["desc"].startswith(f"{campo}:"))


def comparar(casos, escenarios, documentadas):
    """Clasifica cada escenario por lo que su paso When ejercita frente a lo que Schemathesis cubre:
    contrato    error provocado por una petición que ya viola el OpenAPI y Then solo mira estado/código:
                Schemathesis explora esas restricciones de forma sistemática (candidato a redundante)
    regla       error con una petición válida según el OpenAPI: regla de negocio que el esquema no expresa
    feliz       éxito en un valor concreto (p. ej. un límite) verificado solo por estado
    contenido   algún Then verifica datos de negocio (saldo, comisión, CSV, SMS…)
    y marca no_visto si Schemathesis nunca obtuvo esa (operación, estado, código)."""
    vistos_st = {(c["op"], c["estado"], c["codigo"]) for c in casos}
    for e in escenarios:
        llamadas = e["cuando"]
        e["genericos"] = all(t in THEN_GENERICOS for t in e["entonces"])
        e["no_vistas"] = [f"{t['op']} → {t['estado']} {t['codigo']}".strip()
                          for t in llamadas if (t["op"], t["estado"], t["codigo"]) not in vistos_st]
        errores = [t for t in llamadas if t["estado"] >= 400]
        if not llamadas:
            e["clase"] = "sin-when"
        elif not e["genericos"]:
            e["clase"] = "contenido"
        elif not errores:
            e["clase"] = "feliz"
        elif all(t["viola"] for t in errores):
            e["clase"] = "contrato"
        else:
            e["clase"] = "regla"
        if e["clase"] == "contrato":  # casos de Schemathesis que tocaron la misma restricción
            e["evidencia"] = sorted({c["id"] for t in errores for v in t["viola"] for c in casos
                                     if c["op"] == t["op"] and c["estado"] == t["estado"] and coincide(v, c)})[:5]

    # Repetidos: ejemplos de un mismo escenario con la misma respuesta y la misma restricción violada.
    # Si son representantes de una misma partición de equivalencia, sobra uno; si son dos lados de un
    # valor límite que responden igual, no sobran (el doc EP/VL decide).
    grupos = defaultdict(list)
    for i, e in enumerate(escenarios):
        if e["cuando"] and e["clase"] != "contenido":
            firma = (e["nombre"], json.dumps(sorted((t["op"], t["estado"], t["codigo"], t["viola"]) for t in e["cuando"])))
            grupos[firma].append(i)
    repetidos = sorted((g for g in grupos.values() if len(g) > 1), key=len, reverse=True)

    alcance = sorted(op for op in documentadas if modulo(op.split(" ", 1)[1]) in ("Núcleo", "G3"))
    filas = []
    for op in alcance:
        st = [c for c in casos if c["op"] == op]
        esc = [e for e in escenarios if any(t["op"] == op for t in e["cuando"])]
        est_bdd = sorted({t["estado"] for e in esc for t in e["cuando"] if t["op"] == op})
        est_st = sorted({c["estado"] for c in st})
        cod_bdd = sorted({t["codigo"] for e in esc for t in e["cuando"] if t["op"] == op and t["codigo"]})
        cod_st = sorted({c["codigo"] for c in st if c["codigo"]})
        filas.append({"op": op, "modulo": modulo(op.split(" ", 1)[1]), "casos_st": len(st), "escenarios": len(esc),
                      "est_bdd": est_bdd, "est_st": est_st, "cod_bdd": cod_bdd, "cod_st": cod_st,
                      "st_2xx": any(200 <= c["estado"] < 300 for c in st)})
    tripletas_bdd = {(t["op"], t["estado"], t["codigo"]) for e in escenarios for t in e["cuando"]}
    solo_st = sorted(t for t in vistos_st - tripletas_bdd if modulo(t[0].split(" ", 1)[1]) in ("Núcleo", "G3"))
    return {"filas": filas, "repetidos": repetidos,
            "venn": {"ambos": len(tripletas_bdd & vistos_st), "solo_bdd": len(tripletas_bdd - vistos_st),
                     "solo_st": len(solo_st)},
            "solo_st": [[*t, sum(1 for c in casos if (c["op"], c["estado"], c["codigo"]) == t)] for t in solo_st]}


def herramientas(comando):
    """Compara la configuración del CLI (comando del VCR) con tests/api/test_contrato.py."""
    fuente = (RAIZ / "tests" / "api" / "test_contrato.py").read_text(encoding="utf-8")
    checks_pytest = sorted(re.findall(r"schemathesis\.checks\.(\w+)", fuente))
    excluidas_pytest = (re.search(r'EXCLUIDAS = r"([^"]+)"', fuente) or [None, ""])[1]
    ejemplos_pytest = (re.search(r'CONTRATO_EJEMPLOS", "(\d+)"', fuente) or [None, "?"])[1]
    checks_cli = sorted((re.search(r"--checks (\S+)", comando) or [None, ""])[1].split(","))
    return {"checks_pytest": checks_pytest, "checks_cli": checks_cli,
            "excluidas_iguales": excluidas_pytest == (re.search(r"--exclude-path-regex (\S+)", comando) or [None, ""])[1],
            "ejemplos_pytest": ejemplos_pytest, "ejemplos_cli": (re.search(r"--max-examples (\d+)", comando) or [None, "?"])[1]}


def main():
    carpeta = RAIZ / "reporte-schemathesis"
    vcr = Path(sys.argv[1]) if len(sys.argv) > 1 else max(carpeta.glob("vcr-*.yaml"), key=lambda p: p.stat().st_mtime, default=None)
    if not vcr:
        sys.exit("No hay logs VCR: ejecuta python demo.py schemathesis")
    har = Path(sys.argv[2]) if len(sys.argv) > 2 else vcr.with_name(vcr.name.replace("vcr-", "har-").replace(".yaml", ".json"))
    documentadas, operacion, viola = contrato()
    comando, semilla, casos, duracion = schemathesis(vcr, har, operacion)
    for c in casos:
        c["modulo"] = modulo(c["op"].split(" ", 1)[1])
        c["documentada"] = c["op"] in documentadas
    resultados = RAIZ / "reportes" / "allure-results"
    escenarios = bdd(resultados, operacion, viola) if resultados.exists() else []
    datos = {
        "fuente": {"vcr": vcr.name, "har": har.name, "comando": comando, "semilla": semilla},
        "documentadas": sorted(documentadas), "modulos": {op: modulo(op.split(" ", 1)[1]) for op in documentadas},
        "fases": FASES, "casos": casos, "herramientas": herramientas(comando),
        "duracion": duracion, "p95": p95([c["ms"] for c in casos]),
        "escenarios": escenarios, "comparativa": comparar(casos, escenarios, documentadas) if escenarios else None,
    }
    plantilla = (Path(__file__).parent / "plantilla.html").read_text(encoding="utf-8")
    SALIDA.parent.mkdir(exist_ok=True)
    # </ escapado: el JSON va dentro de <script>
    SALIDA.write_text(plantilla.replace("/*DATOS*/null", json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")),
                      encoding="utf-8")
    print(f"Dashboard: {SALIDA}  ({len(casos)} casos de Schemathesis, {len(escenarios)} escenarios BDD)")
    return SALIDA


if __name__ == "__main__":
    main()
