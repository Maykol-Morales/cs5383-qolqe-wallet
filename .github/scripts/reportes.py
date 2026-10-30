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
        resumen.append([hu if hu != "—" else "Contrato y humo", " + ".join(niveles), str(len(cs)), str(sum(x.startswith("pasa") for x in r)),
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


# ── Sitio de Pages: portada, dashboard y matriz ─────────────────────────────────────────────────
# Claro por defecto, oscuro si el sistema lo pide. Una sola familia (system-ui), un acento azul para enlaces y
# series únicas; los colores de estado (pasa / defecto conocido / falla) siempre van con icono y texto.

CSS = """:root{color-scheme:light;--plano:#f6f6f3;--sup:#fcfcfb;--tinta:#0b0b0b;--sec:#52514e;--mudo:#75736d;--linea:#e1e0d9;
--eje:#c3c2b7;--acento:#1c5cab;--serie:#2a78d6;--ok:#0ca30c;--ok-t:#006300;--def:#fab219;--def-t:#8a5a00;--mal:#d03b3b;--omit:#898781;--sombra:0 1px 2px rgba(11,11,11,.06);accent-color:var(--serie)}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--plano:#0d0d0d;--sup:#1a1a19;--tinta:#f4f4f1;--sec:#c3c2b7;--mudo:#9a988f;
--linea:#2c2c2a;--eje:#383835;--acento:#86b6ef;--serie:#3987e5;--ok-t:#3fc13f;--def-t:#fab219;--sombra:none}}
*{box-sizing:border-box}html{background:var(--plano)}::selection{background:var(--serie);color:#fff}
body{margin:0 auto;max-width:76rem;padding:2.5rem 1.25rem 4rem;color:var(--tinta);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--acento);text-underline-offset:.2em}a:focus-visible,[tabindex]:focus-visible,input:focus-visible,summary:focus-visible{outline:2px solid var(--serie);outline-offset:2px;border-radius:4px}
h1{font-size:1.75rem;line-height:1.2;letter-spacing:-.01em;margin:.25rem 0 .5rem}h2{font-size:1.15rem;margin:0}h3{font-size:.95rem;margin:0 0 .75rem}
p{margin:0}.sec{color:var(--sec)}.mudo{color:var(--mudo);font-size:.85rem}code{font:.85em ui-monospace,monospace}
.migas{font-size:.85rem;margin-bottom:1rem}.meta{display:flex;flex-wrap:wrap;gap:.25rem 1.25rem;color:var(--sec);font-size:.9rem;margin-top:.5rem}
.meta b{color:var(--tinta);font-weight:600}
.gate{display:inline-flex;align-items:center;gap:.5rem;margin-top:1.25rem;padding:.45rem .85rem;border-radius:999px;font-weight:600;font-size:.9rem;
background:color-mix(in srgb,var(--ok) 12%,var(--sup));color:var(--ok-t)}.gate.rojo{background:color-mix(in srgb,var(--mal) 12%,var(--sup));color:var(--mal)}
.gate svg,.est svg{width:1em;height:1em;flex:none}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));gap:1px;margin:2rem 0;background:var(--linea);border:1px solid var(--linea);border-radius:12px;overflow:hidden}
.kpi{background:var(--sup);padding:1rem 1.1rem}.kpi .v{font-size:1.9rem;font-weight:650;line-height:1.1;margin-top:.2rem}.kpi .v small{font-size:.9rem;font-weight:500;color:var(--sec)}
.kpi.hero .v{font-size:2.6rem}
section{margin-top:3rem}.cab{display:flex;align-items:baseline;gap:.75rem;flex-wrap:wrap;margin-bottom:.35rem}
.crit{font-size:.8em;font-weight:500;color:var(--mudo);margin-left:.35rem;white-space:nowrap}
.desc{color:var(--sec);max-width:62ch;margin-bottom:1.25rem}
.panel{background:var(--sup);border:1px solid var(--linea);border-radius:12px;padding:1.25rem;box-shadow:var(--sombra)}
.dos{display:grid;gap:1rem;align-items:start;grid-template-columns:repeat(auto-fit,minmax(min(100%,30rem),1fr))}
.leyenda{display:flex;flex-wrap:wrap;gap:.25rem 1rem;font-size:.8rem;color:var(--sec);margin-bottom:.9rem}
.leyenda i{display:inline-block;width:.7rem;height:.7rem;border-radius:2px;margin-right:.35rem;vertical-align:-1px}
.c-pasa{background:var(--ok)}.c-defecto{background:var(--def)}.c-falla{background:var(--mal)}.c-otro{background:var(--omit)}.c-serie{background:var(--serie)}
.filas{display:grid;grid-template-columns:minmax(6.5rem,max-content) 1fr max-content;gap:.45rem .9rem;align-items:center;font-size:.85rem}
.filas .et{color:var(--sec);white-space:nowrap}.filas .et b{color:var(--tinta);font-weight:600}.filas .num{font-variant-numeric:tabular-nums;color:var(--sec);text-align:right}
.grupo{grid-column:1/-1;font-size:.75rem;font-weight:600;color:var(--mudo);text-transform:uppercase;letter-spacing:.06em;margin-top:.5rem}
.barra{display:flex;gap:2px;height:14px;align-items:stretch}.barra span{min-width:2px;border-radius:2px}.barra span:last-child{border-radius:2px 4px 4px 2px}
.columnas{display:flex;align-items:flex-end;gap:8px;height:220px;border-bottom:1px solid var(--eje);padding-top:.5rem}
.columnas .col{flex:1;max-width:4.5rem;display:flex;flex-direction:column-reverse;gap:2px;height:100%;justify-content:flex-start}
.columnas .col span{border-radius:2px}.columnas .col span:last-child{border-radius:4px 4px 2px 2px}
.ejex{display:flex;gap:8px;font-size:.75rem;color:var(--mudo);margin-top:.35rem}.ejex span{flex:1;max-width:4.5rem;text-align:center}
.rejilla{width:100%;border-collapse:separate;border-spacing:4px;font-size:.85rem}.corto{display:none}.rejilla th{font-weight:500;color:var(--sec);text-align:left;padding:0 .25rem}
.rejilla td.c{height:2.4rem;border-radius:6px;text-align:center;font-weight:600;font-size:.8rem}
.rejilla td.pasa{background:color-mix(in srgb,var(--ok) 16%,var(--sup));color:var(--ok-t)}.rejilla td.falla{background:color-mix(in srgb,var(--mal) 14%,var(--sup));color:var(--mal)}
.rejilla td.esperada{background:color-mix(in srgb,var(--def) 22%,var(--sup));color:var(--def-t)}.rejilla td.na{background:transparent;color:var(--mudo);font-weight:400}
.est{display:inline-flex;align-items:center;gap:.35rem;white-space:nowrap}.est.pasa{color:var(--ok-t)}.est.defecto{color:var(--def-t)}.est.falla{color:var(--mal);font-weight:600}.est.otro{color:var(--mudo)}
.sev{display:inline-flex;align-items:center;gap:.4rem;font-size:.8rem;white-space:nowrap}.sev i{width:.55rem;height:.55rem;border-radius:50%}
.lista{list-style:none;margin:0;padding:0;border-top:1px solid var(--linea)}.lista li{border-bottom:1px solid var(--linea)}
.lista a{display:grid;grid-template-columns:1fr auto;gap:.15rem 1rem;padding:1rem .25rem;text-decoration:none;color:inherit}
.lista a:hover .t{color:var(--acento)}.lista .t{font-weight:600}.lista .d{color:var(--sec);font-size:.9rem;grid-column:1}.lista .flecha{grid-row:1/3;grid-column:2;align-self:center;color:var(--mudo)}
.lista .no{padding:1rem .25rem;color:var(--mudo)}
.destacado{display:grid;grid-template-columns:1fr auto;gap:.25rem 1rem;align-items:center;margin:2rem 0 1rem;padding:1.25rem 1.4rem;border-radius:12px;
background:var(--sup);border:1px solid var(--linea);box-shadow:var(--sombra);text-decoration:none;color:inherit}.destacado .t{font-size:1.1rem;font-weight:650}
.destacado:hover{border-color:var(--serie)}.destacado .flecha{grid-row:1/3;grid-column:2;color:var(--acento)}.ic{width:1rem;height:1rem;vertical-align:-.15em}.destacado .ic{width:1.4rem;height:1.4rem}.atras{display:inline-flex;align-items:center;gap:.25rem}.atras .ic{transform:scaleX(-1)}
table.datos{border-collapse:collapse;width:100%;font-size:.85rem}.datos th,.datos td{border-bottom:1px solid var(--linea);padding:.55rem .6rem;text-align:left;vertical-align:top}
.datos th{position:sticky;top:0;background:var(--plano);font-weight:600;color:var(--sec);font-size:.8rem}.datos tbody tr:hover{background:var(--sup)}
#detalle td:nth-child(-n+3){white-space:nowrap}.datos td.n{font-variant-numeric:tabular-nums;text-align:right;width:7rem}.angosta{max-width:46rem}.tabla{overflow-x:auto}
details{margin-top:1rem;font-size:.85rem}summary{cursor:pointer;color:var(--acento);width:max-content}details table{margin-top:.5rem}
.filtro{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin:1rem 0}
.filtro input{font:inherit;padding:.5rem .75rem;border:1px solid var(--eje);border-radius:8px;background:var(--sup);color:var(--tinta);min-width:min(100%,22rem)}
.filtro button{font:inherit;font-size:.85rem;padding:.4rem .75rem;border:1px solid var(--eje);border-radius:999px;background:var(--sup);color:var(--sec);cursor:pointer}
.filtro button[aria-pressed=true]{border-color:var(--serie);color:var(--tinta);background:color-mix(in srgb,var(--serie) 10%,var(--sup))}
#tip{position:fixed;pointer-events:none;background:var(--tinta);color:var(--plano);font-size:.8rem;padding:.4rem .6rem;border-radius:6px;max-width:18rem;opacity:0;transition:opacity .12s}
#tip b{display:block;font-size:.95rem}
@media (max-width:40rem){h1{font-size:1.45rem}.kpi .v{font-size:1.5rem}.kpi.hero .v{font-size:2rem}.filas{grid-template-columns:1fr max-content;row-gap:.2rem}.filas .et{grid-column:1/-1;margin-top:.35rem}.rejilla{font-size:.75rem;border-spacing:2px}.rejilla th .mudo{display:none}.rejilla td.c{height:2rem;font-size:.7rem;padding:0 .15rem}.largo{display:none}.corto{display:inline}.datos{min-width:40rem}#detalle{min-width:56rem}#detalle td:nth-child(4){min-width:18rem}.defs .datos{min-width:0}.defs .datos th:nth-child(n+4),.defs .datos td:nth-child(n+4){display:none}}
@media (prefers-reduced-motion:reduce){#tip{transition:none}}"""

# Tooltip único: lee data-tip (valor) y data-et (etiqueta) con textContent; el teclado ve lo mismo que el puntero.
JS = """const t=document.createElement('div');t.id='tip';t.setAttribute('role','tooltip');document.body.append(t);
const ver=(el,x,y)=>{t.replaceChildren();const b=document.createElement('b');b.textContent=el.dataset.tip;t.append(b,el.dataset.et||'');
t.style.left=Math.min(x+14,innerWidth-t.offsetWidth-8)+'px';t.style.top=(y+14)+'px';t.style.opacity=1};
document.querySelectorAll('[data-tip]').forEach(el=>{el.tabIndex=0;el.addEventListener('pointermove',e=>ver(el,e.clientX,e.clientY));
el.addEventListener('focus',()=>{const r=el.getBoundingClientRect();ver(el,r.left,r.bottom)});
['pointerleave','blur'].forEach(n=>el.addEventListener(n,()=>t.style.opacity=0))});
const q=document.querySelector('#q');if(q){const filas=[...document.querySelectorAll('#detalle tbody tr')],bs=[...document.querySelectorAll('.filtro button')];
let est='';const ap=()=>{const s=q.value.toLowerCase();let n=0;filas.forEach(f=>{const ok=f.textContent.toLowerCase().includes(s)&&(!est||f.dataset.est===est);
f.hidden=!ok;n+=ok});document.querySelector('#cuenta').textContent=n+' de '+filas.length+' filas'};
q.addEventListener('input',ap);bs.forEach(b=>b.addEventListener('click',()=>{est=b.getAttribute('aria-pressed')==='true'?'':b.dataset.est;
bs.forEach(x=>x.setAttribute('aria-pressed',x.dataset.est===est&&est?'true':'false'));ap()}));ap()}"""

ICONOS = {"pasa": '<path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
          "falla": '<path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
          "defecto": '<path d="M8 2.5l6 11H2z M8 6.5v3.5 M8 12v.01" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>',
          "otro": '<circle cx="8" cy="8" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/>'}
ESTADO = {"pasa": "Pasa", "defecto": "Defecto conocido", "falla": "Falla inesperada", "otro": "Omitido"}
SEVERIDAD = {"Crítica": "var(--mal)", "Alta": "#ec835a", "Media": "var(--def)", "Baja": "var(--omit)"}


def icono(clase):
    return f'<svg viewBox="0 0 16 16" aria-hidden="true">{ICONOS[clase]}</svg>'


def clase(res):
    return "pasa" if res.startswith("pasa") else "defecto" if res.startswith("defecto") else "otro" if res in ("omitido",) else "falla"


def pagina(titulo, cuerpo):
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
            f'initial-scale=1"><title>{html.escape(titulo)}</title><style>{CSS}</style></head><body>{cuerpo}'
            f'<script>{JS}</script></body></html>\n')


def cabecera(titulo, run, migas=True):
    enlace = lambda txt, url: f'<a href="{url}">{html.escape(txt)}</a>' if url else html.escape(txt)
    return ((f'<p class="migas"><a href="./" class="atras"><svg class="ic" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>Reportes</a></p>' if migas else "") + f"<h1>{html.escape(titulo)}</h1>"
            f'<p class="meta"><span>Run <b>{enlace("#" + run["numero"], run["url"])}</b></span>'
            f'<span>Commit <b>{enlace(run["corto"], run["commit"])}</b> {html.escape(run["rama"])}</span><span>{run["fecha"]}</span></p>')


def conteo(casos):
    n = defaultdict(int)
    for c in casos:
        n[clase(resultado(c))] += 1
    return n


def gate(n):
    if n["falla"]:
        return f'<p class="gate rojo">{icono("falla")}Quality gate: {n["falla"]} falla(s) inesperada(s)</p>'
    return f'<p class="gate">{icono("pasa")}Quality gate aprobado: todo pasa salvo los defectos conocidos</p>'


def kpis(items):
    return '<div class="kpis">' + "".join(
        f'<div class="kpi{" hero" if i == 0 else ""}"><p class="mudo">{html.escape(e)}</p><p class="v">{v}</p></div>'
        for i, (e, v) in enumerate(items)) + "</div>"


def seccion(crit, titulo, desc, cuerpo):
    return (f'<section><div class="cab"><h2>{html.escape(titulo)} <span class="crit">{crit}</span></h2></div>'
            f'<p class="desc">{desc}</p>{cuerpo}</section>')


def leyenda(*clases):
    return '<p class="leyenda">' + "".join(f'<span><i class="c-{c}"></i>{ESTADO[c]}</span>' for c in clases) + "</p>"


def tabla_simple(cab, filas, numericas=()):
    return ('<div class="tabla"><table class="datos"><thead><tr>' + "".join(f"<th>{html.escape(c)}</th>" for c in cab) +
            "</tr></thead><tbody>" + "".join("<tr>" + "".join(
                f'<td{" class=n" if i in numericas else ""}>{v}</td>' for i, v in enumerate(f)) + "</tr>" for f in filas) +
            "</tbody></table></div>")


def ver_tabla(cab, filas, numericas=()):
    return f"<details><summary>Ver como tabla</summary>{tabla_simple(cab, filas, numericas)}</details>"


# ── Datos extra para el dashboard ───────────────────────────────────────────────────────────────

def corridas_web():
    """{carpeta junit-*: {caso: estado}}; el caso es CP-Wnn o DEF-14 (que no lleva @CP)."""
    salida = {}
    for carpeta in sorted(glob.glob(str(RAIZ / "tests/e2e/reportes/junit*"))):
        res = {}
        for archivo in glob.glob(str(Path(carpeta) / "*.xml")):
            for tc in pruebas(archivo):
                m = re.match(r"CP W(\d+)\b", tc.get("name", ""))
                res[f"CP-W{m[1]}" if m else "DEF-14"] = estado(tc)
        if res:
            salida[Path(carpeta).name] = res
    return salida


def tiempos():
    """[(etiqueta, segundos)] por suite, sumando el `time` de cada testcase del JUnit."""
    suma = lambda tcs: sum(float(tc.get("time") or 0) for tc in tcs)
    api = pruebas(RAIZ / "reportes/junit-api.xml")
    filas = [("API · escenarios BDD", suma(t for t in api if "contrato" not in t.get("name", ""))),
             ("API · contrato Schemathesis", suma(t for t in api if "contrato" in t.get("name", "")))]
    nombres = {"junit-corrida-1": "Web · corrida 1", "junit-corrida-2": "Web · corrida 2", "junit-corrida-3": "Web · corrida 3",
               "junit-ia": "Web · @ia desde la caché", "junit-def14": "Web · DEF-14 (falla esperada)"}
    for carpeta, et in nombres.items():
        tcs = [tc for a in glob.glob(str(RAIZ / f"tests/e2e/reportes/{carpeta}/*.xml")) for tc in pruebas(a)]
        if tcs:
            filas.append((et, suma(tcs)))
    return [f for f in filas if f[1] > 0]


def defectos(casos):
    """[(DEF, título, severidad, casos que lo detectan, niveles)] desde docs/defectos.md (sin los descartados)."""
    texto = (RAIZ / "docs/defectos.md").read_text(encoding="utf-8")
    por_def = defaultdict(list)
    for c in casos:
        for d in c["defs"]:
            por_def[d].append(c)
    salida = []
    for bloque in re.split(r"^## ", texto, flags=re.M)[1:]:
        m, sev = re.match(r"(DEF-\d+): (.+)", bloque), re.search(r"\| Severidad \| (\w+)", bloque)
        if m and sev and "descartado" not in m[2]:
            cs = por_def.get(m[1], [])
            salida.append((m[1], m[2], sev[1], len(cs), " + ".join(sorted({c["nivel"].split(" (")[0] for c in cs})) or "—"))
    orden = list(SEVERIDAD)
    return sorted(salida, key=lambda d: (orden.index(d[2]) if d[2] in orden else 9, d[0]))


def cobertura():
    """(% total, [(archivo, %)]) de reportes/cobertura.xml (pytest-cov), solo api/ y reglas/."""
    ruta = RAIZ / "reportes/cobertura.xml"
    if not ruta.exists():
        return None, []
    raiz = ET.parse(ruta).getroot()
    archivos = [(c.get("filename"), float(c.get("line-rate")) * 100) for c in raiz.iter("class")
                if re.match(r"(qolqe/)?(api|reglas)/", c.get("filename", "")) and not c.get("filename").endswith("__init__.py")]
    return float(raiz.get("line-rate")) * 100, sorted(archivos, key=lambda a: -a[1])


def historial(run, n, segundos, destino):
    """Suma este run al historial publicado en Pages y guarda los últimos 30."""
    import json, urllib.request
    try:
        with urllib.request.urlopen("https://maykol-morales.github.io/cs5383-qolqe-wallet/historial.json", timeout=10) as r:
            previo = json.load(r)
    except Exception:  # sin red o antes del primer deploy con historial: runs #1 a #5, reconstruidos de sus artefactos
        previo = json.loads((RAIZ / ".github/historial-inicial.json").read_text(encoding="utf-8"))
    fila = {"run": run["numero"], "fecha": run["fecha"][:10], "sha": run["corto"], "pasa": n["pasa"], "defecto": n["defecto"],
            "falla": n["falla"], "otro": n["otro"], "segundos": round(segundos)}
    filas = [f for f in previo if f.get("run") != fila["run"]][-29:] + [fila]
    (destino / "historial.json").write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
    return filas


# ── Páginas ─────────────────────────────────────────────────────────────────────────────────────

def html_dashboard(casos, run, url_def, anclas, destino):
    n, total = conteo(casos), len(casos)
    resumen_hu, _ = tablas(casos)
    web, ts = corridas_web(), tiempos()
    segundos = sum(s for _, s in ts)
    cob_total, cob = cobertura()
    hist = historial(run, n, segundos, destino)
    ejecuciones = sum(len(c["ejecuciones"]) for c in casos)
    web_casos = sorted({c for r in web.values() for c in r if c.startswith("CP")})
    w = lambda x, m: f"{100 * x / m:.2f}%" if m else "0"

    cuerpo = cabecera("Dashboard de pruebas", run) + gate(n) + kpis([
        ("Casos que pasan", f'{n["pasa"]}<small> de {total}</small>'), ("Defectos conocidos", str(n["defecto"])),
        ("Fallas inesperadas", str(n["falla"])), ("Ejecuciones en este run", f"{ejecuciones:,}".replace(",", " ")),
        ("Casos web × corridas", f'{len(web.get("junit-corrida-1", {}))}<small> × 3</small>'),
        ("Cobertura de líneas", f"{cob_total:.0f}<small> %</small>" if cob_total is not None else "—")])

    # C1 + C2: casos web en cada corrida
    columnas = [("junit-corrida-1", "Corrida 1", "C1"), ("junit-corrida-2", "Corrida 2", "C2"), ("junit-corrida-3", "Corrida 3", "C3"),
                ("junit-ia", "@ia (caché)", "IA"), ("junit-def14", "DEF-14", "D14")]
    columnas = [c for c in columnas if c[0] in web]
    nombre = {c["id"]: c["nombre"].split(" · ", 1)[-1] for c in casos if c["nivel"].startswith("Web")}
    nombre["DEF-14"] = "Historial con el celular en hora UTC (falla esperada)"
    filas_web = ""
    for caso in web_casos + ["DEF-14"]:
        celdas = ""
        for k, *_ in columnas:
            e = web[k].get(caso)
            if e is None:
                celdas += '<td class="c na" aria-label="no aplica"></td>'
            elif caso == "DEF-14":
                ok = e in ("falla", "xfail")
                celdas += f'<td class="c {"esperada" if ok else "falla"}" data-tip="{"falla esperada" if ok else "¿se corrigió?"}" data-et="DEF-14">{"falla esperada" if ok else "pasa"}</td>'
            else:
                celdas += f'<td class="c {"pasa" if e == "pasa" else "falla"}" data-tip="{e}" data-et="{caso}">{"pasa" if e == "pasa" else e}</td>'
        filas_web += f'<tr><th scope="row"><b>{caso}</b> <span class="mudo">{html.escape(nombre.get(caso, ""))}</span></th>{celdas}</tr>'
    cuerpo += seccion("C1 · C2", "Criterios web, tres corridas seguidas",
                      "Cada caso E2E corre 3 veces seguidas sin reintentos; una celda roja haría fallar el job. "
                      "El escenario de IA repite browser.act desde su caché, sin clave. DEF-14 debe seguir fallando mientras exista.",
                      '<div class="panel tabla"><table class="rejilla"><thead><tr><th>Caso</th>' +
                      "".join(f'<th><span class="largo">{e}</span><span class="corto" aria-hidden="true">{c}</span></th>' for _, e, c in columnas) + f"</tr></thead><tbody>{filas_web}</tbody></table></div>")

    # C2 + C3: tiempos por suite
    mx = max((s for _, s in ts), default=0)
    barras = "".join(f'<span class="et">{html.escape(e)}</span><div class="barra"><span class="c-serie" style="width:{w(s, mx)}" '
                     f'data-tip="{s:.1f} s" data-et="{html.escape(e)}"></span></div><span class="num">{s:.1f} s</span>' for e, s in ts)
    cuerpo += seccion("C2 · C3", "Cuánto tarda cada suite",
                      f"Suma de los tiempos del JUnit: {segundos:.0f} s de pruebas en este run. Las corridas web casi iguales "
                      "indican que no hay esperas fijas ni reintentos escondidos.",
                      f'<div class="panel"><div class="filas">{barras}</div>' +
                      ver_tabla(["Suite", "Segundos"], [[html.escape(e), f"{s:.1f}"] for e, s in ts], (1,)) + "</div>")

    # C4: casos por historia
    mh = max(int(r[2]) for r in resumen_hu)
    filas_hu, grupo = "", None
    for hu, nivel, cs, pasa, dfc, otros in resumen_hu:
        g = "Núcleo" if hu.startswith("HU-N") else "G3 · Historial y categorías" if hu.startswith("HU-G3") else "Sin historia de usuario"
        if g != grupo:
            filas_hu += f'<p class="grupo">{g}</p>'
            grupo = g
        segs = "".join(f'<span class="c-{k}" style="width:{w(int(v), mh)}" data-tip="{v} {ESTADO[k].lower()}" data-et="{hu} · {nivel}"></span>'
                       for k, v in (("pasa", pasa), ("defecto", dfc), ("otro", otros)) if int(v))
        filas_hu += (f'<span class="et"><b>{hu}</b> · {"web + API" if "Web" in nivel else "API"}</span>'
                     f'<div class="barra">{segs}</div><span class="num">{pasa}/{cs}</span>')
    cuerpo += seccion("C4", "Trazabilidad: cada historia y sus casos",
                      f"Casos por historia de usuario y su resultado en este run. Las cuatro historias con flujos en pantalla "
                      f'se prueban por API y web. El detalle caso por caso está en la <a href="trazabilidad.html">matriz de trazabilidad</a>.',
                      f'<div class="panel">{leyenda("pasa", "defecto", "otro")}<div class="filas">{filas_hu}</div></div>')

    # C4: defectos
    filas_def = [[f'<a href="{url_def}#{html.escape(anclas.get(d, ""))}">{d}</a>', html.escape(t),
                  f'<span class="sev"><i style="background:{SEVERIDAD.get(s, "var(--omit)")}"></i>{s}</span>', str(k), html.escape(nv)]
                 for d, t, s, k, nv in defectos(casos)]
    cuerpo += seccion("C4", "Defectos que el pipeline vigila",
                      "Cada defecto abierto tiene al menos un caso que falla a propósito (xfail estricto en la API, paso invertido en la web). "
                      "Si alguien lo corrige, su caso pasa y el pipeline avisa para retirar la etiqueta.",
                      '<div class="panel defs">' + tabla_simple(["Defecto", "Qué pasa", "Severidad", "Casos", "Nivel"], filas_def, (3,)) + "</div>")

    # C3: tendencia y cobertura
    mx_run = max((f["pasa"] + f["defecto"] + f["falla"] + f["otro"] for f in hist), default=1)
    cols = "".join('<div class="col">' + "".join(
        f'<span class="c-{k}" style="height:{w(f[k], mx_run)}" data-tip="{f[k]} {ESTADO[k].lower()}" data-et="run #{f["run"]} · {f["fecha"]}"></span>'
        for k in ("pasa", "defecto", "falla", "otro") if f[k]) + "</div>" for f in hist)
    ejes = "".join(f'<span>#{f["run"]}</span>' for f in hist)
    tendencia = (f'<div class="panel"><h3>Resultado por run</h3>{leyenda("pasa", "defecto", "falla", "otro")}'
                 f'<div class="columnas">{cols}</div><div class="ejex">{ejes}</div>' +
                 ver_tabla(["Run", "Fecha", "Pasan", "Defecto conocido", "Fallas", "Omitidos", "Segundos"],
                           [[f'#{f["run"]}', f["fecha"], f["pasa"], f["defecto"], f["falla"], f["otro"], f["segundos"]] for f in hist],
                           (2, 3, 4, 5, 6)) + "</div>")
    filas_cob = "".join(f'<span class="et">{html.escape(a.split("/", 1)[-1] if a.startswith("qolqe/") else a)}</span><div class="barra">'
                        f'<span class="c-serie" style="width:{p:.1f}%" data-tip="{p:.0f} %" data-et="{html.escape(a)}"></span></div>'
                        f'<span class="num">{p:.0f} %</span>' for a, p in cob)
    cuadro_cob = (f'<div class="panel"><h3>Cobertura de líneas por módulo</h3><div class="filas">{filas_cob}</div></div>' if cob
                  else '<div class="panel"><h3>Cobertura</h3><p class="mudo">Sin reportes/cobertura.xml en este run.</p></div>')
    cuerpo += seccion("C3", "El pipeline en el tiempo",
                      f"Cada run suma una fila a <code>historial.json</code> en Pages ({len(hist)} run(s) registrados). "
                      "La cobertura sale de pytest-cov en el job de la API.", f'<div class="dos">{tendencia}{cuadro_cob}</div>')
    return pagina(f"Dashboard · run #{run['numero']}", cuerpo)


def html_matriz(casos, run, url_def, anclas):
    resumen_hu, detalle = tablas(casos)

    def celda(v, col):
        if isinstance(v, list):
            return ", ".join(f'<a href="{url_def}#{html.escape(anclas.get(d, ""))}">{d}</a>' for d in v)
        if col != 4:
            return html.escape(v)
        k = clase(v)
        return f'<span class="est {k}">{icono(k)}{html.escape(v)}</span>'

    filas = "".join(f'<tr data-est="{clase(f[4])}">' + "".join(f"<td>{celda(x, i)}</td>" for i, x in enumerate(f)) + "</tr>" for f in detalle)
    dobles = [c["id"] for c in casos if len(c["hu"]) > 1]
    nota = (f'<p class="mudo" style="margin-top:.75rem">{len(casos)} casos en {len(detalle)} filas: '
            f'{", ".join(dobles)} cubre{"n" if len(dobles) > 1 else ""} más de una historia y aparece{"n" if len(dobles) > 1 else ""} una vez por cada una.</p>' if dobles else "")
    botones = "".join(f'<button type="button" data-est="{k}" aria-pressed="false">{ESTADO[k]}</button>' for k in ("pasa", "defecto", "falla", "otro"))
    return pagina("Matriz de trazabilidad", cabecera("Matriz de trazabilidad", run) + (
        '<p class="desc" style="margin-top:1rem">HU → caso → nivel → resultado de este run, generada desde los JUnit del pipeline y las '
        f'etiquetas de los <code>.feature</code>. «Defecto conocido» es una falla esperada, enlazada a <a href="{url_def}">docs/defectos.md</a>.</p>'
        '<section><h2>Resumen por historia</h2><div class="panel angosta" style="margin-top:1rem">' +
        tabla_simple(CAB_RESUMEN, [[html.escape(x) for x in f] for f in resumen_hu], (2, 3, 4, 5)) + "</div>" + nota + "</section>"
        '<section><h2>Detalle</h2><div class="filtro"><input id="q" type="search" placeholder="Buscar HU, caso o escenario" '
        f'aria-label="Buscar en la matriz">{botones}<span id="cuenta" class="mudo" aria-live="polite"></span></div>'
        '<div class="tabla"><table class="datos" id="detalle"><thead><tr>' + "".join(f"<th>{c}</th>" for c in CAB_DETALLE) +
        f"</tr></thead><tbody>{filas}</tbody></table></div></section>"))


def sitio(destino):
    destino = RAIZ / destino
    destino.mkdir(parents=True, exist_ok=True)
    run, anclas = datos_run(), anclas_defectos()
    casos = casos_con_resultados()
    md = markdown(casos, run, anclas)
    (RAIZ / "docs/trazabilidad.md").write_text(md, encoding="utf-8")
    (destino / "trazabilidad.md").write_text(md, encoding="utf-8")

    url_def = f"https://github.com/{REPO}/blob/{run['sha']}/docs/defectos.md"
    (destino / "trazabilidad.html").write_text(html_matriz(casos, run, url_def, anclas), encoding="utf-8")
    (destino / "dashboard.html").write_text(html_dashboard(casos, run, url_def, anclas, destino), encoding="utf-8")

    copias = {"api/index.html": "reportes/allure/index.html", "web/index.html": "tests/e2e/reportes/allure/index.html",
              "schemathesis": "reportes/schemathesis", "contrato/index.html": "reportes/dashboard-contrato.html"}
    for dst, src in copias.items():
        src, dst = RAIZ / src, destino / dst
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
    enlaces = [("trazabilidad.html", "Matriz de trazabilidad", "HU → caso → nivel → resultado de este run, con buscador"),
               ("api/", "Allure · API", "pytest-bdd: núcleo + G3, defectos conocidos como xfail"),
               ("web/", "Allure · Web E2E", "WebdriverIO + Cucumber: 3 corridas seguidas y el escenario de IA"),
               ("schemathesis/", "Schemathesis", "Reporte del CLI: contrato OpenAPI con semilla fija"),
               ("contrato/", "Dashboard de contrato", "Logs VCR + HAR y comparativa con los escenarios BDD")]
    items = "".join(f'<li><a href="{href}"><span class="t">{t}</span><span class="d">{d}</span><span class="flecha"><svg class="ic" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg></span></a></li>'
                    if (destino / href.rstrip("/")).exists() else f'<li><p class="no"><b>{t}</b> · no generado en este run</p></li>'
                    for href, t, d in enlaces)
    n = conteo(casos)
    (destino / "index.html").write_text(pagina("Qolqe · Reportes de pruebas", (
        cabecera("Qolqe Wallet · Reportes de pruebas", run, migas=False) +
        f'<p class="sec" style="margin-top:.75rem">CS5383 · Grupo 3 (G3 · Historial y categorías). Pipeline '
        f'<code>.github/workflows/pruebas.yml</code> · <a href="https://github.com/{REPO}">repositorio</a></p>' + gate(n) +
        kpis([("Casos que pasan", f'{n["pasa"]}<small> de {len(casos)}</small>'), ("Defectos conocidos", str(n["defecto"])),
              ("Fallas inesperadas", str(n["falla"])), ("Omitidos", str(n["otro"]))]) +
        '<a class="destacado" href="dashboard.html"><span class="t">Dashboard del run</span><span class="flecha"><svg class="ic" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg></span>'
        '<span class="sec">Casos web × 3 corridas, tiempos, trazabilidad por historia, defectos, tendencia y cobertura</span></a>'
        f'<ul class="lista">{items}</ul>')), encoding="utf-8")

    print(f"### Trazabilidad (run {run['numero']})\n")
    print(md_tabla(CAB_RESUMEN, tablas(casos)[0], anclas).replace("](defectos.md", f"]({url_def}"))
    print("\nMatriz completa: `docs/trazabilidad.md` (artefacto `sitio`) y Pages → `trazabilidad.html` y `dashboard.html`.\n")


if __name__ == "__main__":
    comando, *args = sys.argv[1:] or ["?"]
    if comando == "resumen" and args:
        resumen(args[0], args[1:])
    elif comando == "sitio":
        sitio(args[0] if args else "sitio")
    else:
        sys.exit(__doc__)
