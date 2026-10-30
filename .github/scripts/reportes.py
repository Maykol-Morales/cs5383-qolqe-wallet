"""Reportes del pipeline a partir de los JUnit XML y las etiquetas de los .feature (solo biblioteca estándar).

    python .github/scripts/reportes.py resumen TITULO junit.xml...   Markdown para $GITHUB_STEP_SUMMARY
    python .github/scripts/reportes.py sitio [DIR]                   docs/trazabilidad.md + sitio de Pages en DIR (sitio/)

Rutas que lee `sitio` (relativas a la raíz del repo, las mismas que dejan los jobs api y web):
  reportes/junit-api.xml               pytest; cada prueba BDD lleva la propiedad `escenario` (tests/api/conftest.py)
  tests/e2e/reportes/junit*/*.xml      WebdriverIO; el caso se reconoce por el `CP-Wnn` del nombre del escenario
  reportes/allure/, reportes/schemathesis/, reportes/dashboard-contrato.html, tests/e2e/reportes/allure/
Avisa (::warning::) si un escenario no tiene ejecución o una ejecución no tiene escenario: así se nota el desfase.
"""
import glob
import html
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REPO = os.environ.get("GITHUB_REPOSITORY", "Maykol-Morales/cs5383-qolqe-wallet")


def aviso(msg):
    print(f"::warning::{msg}", file=sys.stderr)


def norma(nombre):
    """Como el reporter JUnit de WebdriverIO: todo lo que no es [a-zA-Z0-9@] separa palabras."""
    return " ".join(p for p in re.split(r"[^a-zA-Z0-9@]+", nombre) if p)


# ── .feature → casos ────────────────────────────────────────────────────────────────────────────

def escenarios(archivo, nivel):
    """Un caso por Scenario; un Scenario Outline cuyos Examples llevan etiquetas propias (p. ej. @CP-W02)
    da un caso por bloque de Examples, con el nombre resuelto con la primera fila."""
    casos, pendientes, de_feature, plantilla, filas = [], [], [], None, None
    for linea in archivo.read_text(encoding="utf-8").splitlines() + [""]:
        s = linea.strip()
        if filas is not None and s.startswith("|"):
            filas.append([c.strip() for c in s.strip("|").split("|")])
            if len(filas) == 2:  # cabecera + primera fila: nombre del caso del bloque
                fila = dict(zip(*filas))
                casos[-1]["nombre"] = re.sub(r"<(\w+)>", lambda m: fila.get(m[1], m[0]), casos[-1]["nombre"])
            continue
        filas = None
        if s.startswith("@"):
            pendientes += [t[1:] for t in s.split() if t.startswith("@")]
        elif s.startswith("Feature:"):
            de_feature, pendientes = pendientes, []
        elif re.match(r"(Scenario|Scenario Outline|Example):", s):
            nombre = s.split(":", 1)[1].strip()
            plantilla = {"archivo": archivo.name, "plantilla": nombre, "nombre": nombre, "nivel": nivel,
                         "tags": de_feature + pendientes}
            casos.append(plantilla)
            pendientes = []
        elif s.startswith("Examples:") and pendientes and plantilla:
            if casos and casos[-1] is plantilla:
                casos.pop()  # el Outline se reparte en sus bloques de Examples
            casos.append({**plantilla, "tags": plantilla["tags"] + pendientes})
            pendientes, filas = [], []
    for n, c in enumerate(casos, 1):
        cp = next((t for t in c["tags"] if re.fullmatch(r"CP-\w+", t)), None)
        c["id"] = cp or (f"CP-A-{archivo.stem}-{n:02d}" if nivel == "API" else "—")
        c["hu"] = [t for t in c["tags"] if t.startswith("HU-")] or ["—"]
        c["defs"] = [t for t in c["tags"] if t.startswith("DEF-")]
        if "ia" in c["tags"]:
            c["nivel"] += " (IA)"
        c["clave"] = (f"{c['archivo']}::{c['plantilla']}" if nivel == "API" else cp or norma(c["nombre"]))
        c["ejecuciones"] = []
    return casos


# ── JUnit → ejecuciones ─────────────────────────────────────────────────────────────────────────

def estado(tc):
    for hijo in tc:
        if hijo.tag in ("failure", "error"):  # XPASS(strict): un @DEF que ya pasa, no es "defecto conocido"
            return "xpass" if "XPASS" in hijo.get("message", "") else "falla"
        if hijo.tag == "skipped":
            xfail = "xfail" in hijo.get("type", "") or "Defecto conocido" in hijo.get("message", "")
            return "xfail" if xfail else "omitida"
    return "pasa"


def pruebas(archivo):
    try:
        return list(ET.parse(archivo).getroot().iter("testcase"))
    except ET.ParseError:  # los specs sin escenarios del filtro dejan un XML vacío
        return []


def resumen(titulo, archivos):
    grupos = defaultdict(list)
    for a in archivos:
        grupos[Path(a).parent.name if "junit" in Path(a).parent.name else Path(a).stem] += pruebas(a)
    print(f"### {titulo}\n\n| Corrida | Pruebas | Pasan | Fallan | Defecto conocido (xfail) | Omitidas |\n|---|---|---|---|---|---|")
    fallas = []
    for nombre, tcs in sorted(grupos.items()):
        c = defaultdict(int)
        for tc in tcs:
            c[estado(tc)] += 1
            if estado(tc) in ("falla", "xpass"):
                fallas.append(f"{nombre}: {tc.get('name')}")
        print(f"| {nombre} | {len(tcs)} | {c['pasa']} | {c['falla'] + c['xpass']} | {c['xfail']} | {c['omitida']} |")
    if not grupos:
        print("| (sin JUnit) | | | | | |")
    if fallas:
        print("\n**Fallas:**\n" + "\n".join(f"- `{f}`" for f in fallas[:20]))
    print("\nDefectos conocidos: `docs/defectos.md`. Matriz HU → caso → resultado: `docs/trazabilidad.md` (job reportes).\n")


def resultado(c):
    est = c["ejecuciones"]
    n, ok = len(est), est.count("pasa")
    if not n:
        return "sin ejecutar"
    if c["defs"]:
        if ok == n or "xpass" in est:
            return f"XPASS: ¿se corrigió {', '.join(c['defs'])}?"
        return f"defecto conocido ({n} ejec.)"
    if "falla" in est:
        return f"FALLA {est.count('falla')}/{n}"
    if ok == 0:
        return "omitido"
    return f"pasa {ok}/{n}" if n > 1 else "pasa"


def casos_con_resultados():
    casos = [c for f in sorted((RAIZ / "features").glob("*.feature")) for c in escenarios(f, "API")]
    casos += [c for f in sorted((RAIZ / "tests/e2e/features").glob("*.feature")) for c in escenarios(f, "Web E2E")]
    por_clave = {c["clave"]: c for c in casos}
    # pruebas omitidas antes del hook de pytest-bdd (@concurrencia) no llevan la propiedad: nombre como pytest-bdd
    python = lambda n: "test_" + re.sub(r"^\d+_*", "", re.sub(r"\W", "", n.replace(" ", "_"))).lower()
    por_nombre = {python(c["plantilla"]): c for c in casos if c["nivel"] == "API"}
    extras = {}  # pruebas sin .feature (contrato Schemathesis, humo)
    for tc in pruebas(RAIZ / "reportes/junit-api.xml"):
        prop = tc.find("properties/property[@name='escenario']")
        if prop is not None:
            clave = prop.get("value")
        elif tc.get("name").split("[")[0] in por_nombre:
            clave = por_nombre[tc.get("name").split("[")[0]]["clave"]
        elif tc.get("classname", "").startswith("tests."):
            nombre = tc.get("name").split("[")[0]
            clave = f"extra::{nombre}"
            extras.setdefault(clave, {"id": nombre, "nombre": "Contrato OpenAPI (Schemathesis, 1 prueba + subpruebas)"
                                      if "contrato" in nombre else nombre, "nivel": "API", "hu": ["—"], "defs": [],
                                      "clave": clave, "ejecuciones": [], "archivo": tc.get("classname")})
            por_clave.setdefault(clave, extras[clave])
        else:
            clave = None
        if clave in por_clave:
            por_clave[clave]["ejecuciones"].append(estado(tc))
        else:
            aviso(f"Prueba API sin escenario: {tc.get('classname')}::{tc.get('name')}")
    for archivo in sorted(glob.glob(str(RAIZ / "tests/e2e/reportes/junit*/*.xml"))):
        for tc in pruebas(archivo):
            m = re.match(r"CP W(\d+)\b", tc.get("name", ""))
            clave = f"CP-W{m[1]}" if m else tc.get("name")
            if clave in por_clave:
                por_clave[clave]["ejecuciones"].append(estado(tc))
            else:
                aviso(f"Prueba web sin escenario: {tc.get('name')}")
    for c in casos:
        if not c["ejecuciones"]:
            aviso(f"Escenario sin ejecución en el JUnit: {c['archivo']} · {c['nombre']}")
    return casos + list(extras.values())


# ── Matriz (Markdown + HTML) y portada ──────────────────────────────────────────────────────────

def datos_run():
    sha = os.environ.get("GITHUB_SHA") or subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    servidor, run_id = os.environ.get("GITHUB_SERVER_URL", "https://github.com"), os.environ.get("GITHUB_RUN_ID")
    return {"numero": os.environ.get("GITHUB_RUN_NUMBER", "local"), "sha": sha, "corto": sha[:7],
            "rama": os.environ.get("GITHUB_REF_NAME", ""), "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "url": f"{servidor}/{REPO}/actions/runs/{run_id}" if run_id else "",
            "commit": f"{servidor}/{REPO}/commit/{sha}"}


def anclas_defectos():
    """DEF-nn → ancla del encabezado en docs/defectos.md, como la arma GitHub."""
    texto = (RAIZ / "docs/defectos.md").read_text(encoding="utf-8")
    return {m[2]: re.sub(r"[^\w\- ]", "", m[1].lower()).replace(" ", "-")
            for m in re.finditer(r"^## ((DEF-\d+): .+)$", texto, re.M)}


def tablas(casos):
    """(resumen por HU, detalle): listas de filas; la celda de defectos es la lista de DEF-nn."""
    por_hu = defaultdict(list)
    for c in casos:
        for hu in c["hu"]:
            por_hu[hu].append(c)
    orden = lambda hu: (hu == "—", hu.startswith("HU-G"), [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", hu)])
    resumen, detalle = [], []
    for hu in sorted(por_hu, key=orden):
        cs = por_hu[hu]
        niveles = sorted({c["nivel"].split(" (")[0] for c in cs})
        r = [resultado(c) for c in cs]
        resumen.append([hu, " + ".join(niveles), str(len(cs)), str(sum(x.startswith("pasa") for x in r)),
                        str(sum(x.startswith("defecto") for x in r)),
                        str(sum(not x.startswith(("pasa", "defecto")) for x in r))])
        for c in cs:
            detalle.append([hu, c["id"], c["nivel"], c["nombre"], resultado(c), c["defs"] or "—"])
    return resumen, detalle


CAB_RESUMEN = ["HU", "Nivel", "Casos", "Pasan", "Defecto conocido", "Otros"]
CAB_DETALLE = ["HU", "Caso", "Nivel", "Escenario", "Resultado", "Defecto"]


def md_tabla(cab, filas, anclas):
    def celda(v):
        if isinstance(v, list):
            return ", ".join(f"[{d}](defectos.md#{anclas.get(d, '')})" for d in v)
        return str(v).replace("|", "\\|")
    return "\n".join([f"| {' | '.join(cab)} |", "|" + "---|" * len(cab)] +
                     [f"| {' | '.join(celda(x) for x in f)} |" for f in filas])


def markdown(casos, run, anclas):
    resumen, detalle = tablas(casos)
    run_txt = f"[run #{run['numero']}]({run['url']})" if run["url"] else f"run {run['numero']}"
    return f"""# Matriz de trazabilidad · HU → caso → nivel → resultado

Generada por `.github/scripts/reportes.py` desde los JUnit del {run_txt} (commit `{run['corto']}`, {run['fecha']}).
No se edita a mano: el pipeline la regenera y la publica en https://maykol-morales.github.io/cs5383-qolqe-wallet/trazabilidad.html.

- **Caso**: `CP-Wnn` (web, etiqueta del `.feature`) o `CP-A-<feature>-nn` (API, n.º de escenario en su `.feature`).
- **Resultado**: `pasa k/n` (n ejecuciones: ejemplos de un Outline o las 3 corridas web); `defecto conocido` = falla
  esperada (`xfail` estricto en pytest, paso invertido en web) enlazada a [docs/defectos.md](defectos.md).
- Un caso con varias HU aparece una vez por HU.

## Resumen por historia

{md_tabla(CAB_RESUMEN, resumen, anclas)}

## Detalle

{md_tabla(CAB_DETALLE, detalle, anclas)}
"""


CSS = """:root{--fondo:#fafaf7;--texto:#1d1f1c;--suave:#5f645c;--borde:#dcdcd4;--acento:#2f6f4f;--ok:#2f6f4f;--mal:#b3261e;--aviso:#8a5a00;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--fondo:#151714;--texto:#e6e7e2;--suave:#a3a89f;--borde:#33372f;--acento:#7cc49c;--ok:#7cc49c;--mal:#ff8a80;--aviso:#e0b45c}}
body{margin:0 auto;max-width:72rem;padding:2rem 1rem;background:var(--fondo);color:var(--texto);font:16px/1.5 system-ui,sans-serif}
a{color:var(--acento)}h1{font-size:1.6rem;margin:0 0 .25rem}h2{font-size:1.15rem;margin-top:2rem}p,li{color:var(--suave)}
table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{border-bottom:1px solid var(--borde);padding:.4rem .5rem;text-align:left;vertical-align:top}
th{position:sticky;top:0;background:var(--fondo)}.tabla{overflow-x:auto}code{font-size:.85em}
.pasa{color:var(--ok)}.falla{color:var(--mal);font-weight:600}.defecto{color:var(--aviso)}
ul.enlaces{list-style:none;padding:0;display:grid;gap:.75rem;grid-template-columns:repeat(auto-fill,minmax(16rem,1fr))}
ul.enlaces li{border:1px solid var(--borde);border-radius:.5rem;padding:.9rem 1rem}ul.enlaces a{font-weight:600}
dl{display:grid;grid-template-columns:max-content 1fr;gap:.25rem 1rem}dt{color:var(--suave)}dd{margin:0}"""


def pagina(titulo, cuerpo):
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
            f'initial-scale=1"><title>{html.escape(titulo)}</title><style>{CSS}</style></head><body>{cuerpo}</body></html>\n')


def tabla_html(cab, filas, url_def, anclas):
    def celda(v, col):
        if isinstance(v, list):
            return ", ".join(f'<a href="{url_def}#{html.escape(anclas.get(d, ""))}">{d}</a>' for d in v)
        if cab[col] != "Resultado":
            return html.escape(v)
        clase = "pasa" if v.startswith("pasa") else "defecto" if v.startswith("defecto") else "falla"
        return f'<span class="{clase}">{html.escape(v)}</span>'
    return ('<div class="tabla"><table><thead><tr>' + "".join(f"<th>{html.escape(c)}</th>" for c in cab) + "</tr></thead><tbody>" +
            "".join("<tr>" + "".join(f"<td>{celda(x, i)}</td>" for i, x in enumerate(f)) + "</tr>" for f in filas) + "</tbody></table></div>")


def datos_html(run):
    enlace = lambda txt, url: f'<a href="{url}">{html.escape(txt)}</a>' if url else html.escape(txt)
    return (f"<dl><dt>Run</dt><dd>{enlace('#' + run['numero'], run['url'])}</dd>"
            f"<dt>Commit</dt><dd>{enlace(run['corto'], run['commit'])} {html.escape(run['rama'])}</dd>"
            f"<dt>Fecha</dt><dd>{run['fecha']}</dd></dl>")


def sitio(destino):
    destino = RAIZ / destino
    destino.mkdir(parents=True, exist_ok=True)
    run, anclas = datos_run(), anclas_defectos()
    casos = casos_con_resultados()
    md = markdown(casos, run, anclas)
    (RAIZ / "docs/trazabilidad.md").write_text(md, encoding="utf-8")
    (destino / "trazabilidad.md").write_text(md, encoding="utf-8")

    url_def = f"https://github.com/{REPO}/blob/{run['sha']}/docs/defectos.md"
    resumen_hu, detalle = tablas(casos)
    (destino / "trazabilidad.html").write_text(pagina("Matriz de trazabilidad", (
        '<p><a href="./">← Reportes</a></p><h1>Matriz de trazabilidad</h1><p>HU → caso → nivel → resultado. '
        'Generada desde los JUnit del pipeline y las etiquetas de los <code>.feature</code>; '
        f'«defecto conocido» = falla esperada, enlazada a <a href="{url_def}">docs/defectos.md</a>.</p>'
        + datos_html(run) + "<h2>Resumen por historia</h2>" + tabla_html(CAB_RESUMEN, resumen_hu, url_def, anclas)
        + "<h2>Detalle</h2>" + tabla_html(CAB_DETALLE, detalle, url_def, anclas))), encoding="utf-8")

    copias = {"api/index.html": "reportes/allure/index.html", "web/index.html": "tests/e2e/reportes/allure/index.html",
              "schemathesis": "reportes/schemathesis", "contrato/index.html": "reportes/dashboard-contrato.html"}
    for dst, src in copias.items():
        src, dst = RAIZ / src, destino / dst
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
    enlaces = [("trazabilidad.html", "Matriz de trazabilidad", "HU → caso → nivel → resultado de este run"),
               ("api/", "Allure · API", "pytest-bdd: núcleo + G3, defectos conocidos como xfail"),
               ("web/", "Allure · Web E2E", "WebdriverIO + Cucumber, 3 corridas seguidas + escenario de IA"),
               ("schemathesis/", "Schemathesis (CLI)", "contrato OpenAPI, todas las operaciones"),
               ("contrato/", "Dashboard de contrato", "logs VCR + HAR y comparativa con los escenarios BDD")]
    items = "".join(f'<li><a href="{href}">{t}</a><p>{d}</p></li>' if (destino / href.rstrip("/")).exists()
                    else f"<li><strong>{t}</strong><p>No generado en este run.</p></li>" for href, t, d in enlaces)
    n = defaultdict(int)
    for c in casos:
        n[resultado(c).split()[0].lower()] += 1
    (destino / "index.html").write_text(pagina("Qolqe · Reportes", (
        "<h1>Qolqe Wallet · Reportes de pruebas</h1><p>CS5383 · Grupo 3 (G3 · Historial y categorías). "
        f'Pipeline <code>.github/workflows/pruebas.yml</code> · <a href="https://github.com/{REPO}">repositorio</a></p>'
        + datos_html(run) + f"<p>{len(casos)} casos: {n['pasa']} pasan, {n['defecto']} con defecto conocido, "
        f"{len(casos) - n['pasa'] - n['defecto']} otros.</p><ul class=\"enlaces\">{items}</ul>")), encoding="utf-8")

    print(f"### Trazabilidad (run {run['numero']})\n")
    print(md_tabla(CAB_RESUMEN, resumen_hu, anclas).replace("](defectos.md", f"]({url_def}"))
    print("\nMatriz completa: `docs/trazabilidad.md` (artefacto `sitio`) y Pages → `trazabilidad.html`.\n")


if __name__ == "__main__":
    comando, *args = sys.argv[1:] or ["?"]
    if comando == "resumen" and args:
        resumen(args[0], args[1:])
    elif comando == "sitio":
        sitio(args[0] if args else "sitio")
    else:
        sys.exit(__doc__)
