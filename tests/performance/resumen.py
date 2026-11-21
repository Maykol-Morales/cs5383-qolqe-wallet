"""Resumen de una corrida de k6 en HTML: python resumen.py [<carpeta>]

Con una carpeta deja <carpeta>/resumen.html; sin argumentos lo hace con todas las corridas de resultados/ y arma
resultados/index.html (una fila por corrida).

Por qué existe: el dashboard web de k6 solo grafica las métricas globales (sin etiquetas) y no dice si los umbrales
pasaron; el total de peticiones sale abreviado («7.3k»). Los percentiles por tipo de operación (consulta / dinero),
los veredictos de los umbrales y los totales exactos sí están en la consola y en summary.json. Este script los junta
con el resto de lo que mide correr.py (recursos, integridad, endpoints, minutos). Solo biblioteca estándar.
"""
import csv
import html
import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RESULTADOS = AQUI / "resultados"

PRUEBAS = {"humo": "Humo", "carga": "Carga (hora punta)", "pico": "Pico", "estres": "Estrés"}
NOTAS = {  # por qué se conserva cada corrida
    "carga-20261112-1949-docker": "Corrida de carga que cita el Informe_Rendimiento_G3.docx.",
    "pico-20261112-2008-docker": "Corrida de pico que cita el Informe_Rendimiento_G3.docx.",
    "estres-20261112-2024-docker": "Corrida de estrés que cita el Informe_Rendimiento_G3.docx (capacidad de 700 usuarios).",
    "humo-20261120-0847-docker-ec2": "Validación en EC2 (informe §4.7).",
    "carga-20261120-0853-docker-ec2": "Validación en EC2 (informe §4.7).",
    "pico-20261120-0911-docker-ec2": "Validación en EC2 (informe §4.7).",
    "estres-20261120-0926-docker-ec2": "Validación en EC2 (informe §4.7): sin quiebre hasta 1 000 usuarios.",
    "carga-20261111-0422-docker": "Modelo de carga anterior (por operación, sin flujos). Se conserva porque "
                                  "docs/comparativa-rendimiento.md cita su CPU de k6 (2,6 %).",
    "estres-20261111-2048-docker-rampa-1min": "Modelo de carga anterior. Evidencia de DEF-16 en docs/defectos.md.",
}
UMBRAL = re.compile(r"^(p\(\d+\)|avg|med|min|max|rate|count|value)\s*(<=|>=|<|>|==)\s*([\d.]+)$")


def leer_json(ruta):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def leer_csv(ruta):
    try:
        with open(ruta, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def num(n):
    """Miles con espacio fino, como en el informe: 7 328."""
    return f"{int(round(n)):,}".replace(",", "\u202f")


def dec(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def ms(v):
    if v is None:
        return "—"
    return f"{dec(v / 1000, 2)} s" if v >= 1000 else f"{dec(v, 1)} ms"


def esc(x):
    return html.escape(str(x))


def metadatos(carpeta):
    nombre = carpeta.name
    m = re.match(r"([a-z]+)-(\d{8})-(\d{4})", nombre)
    prueba = PRUEBAS.get(m.group(1), m.group(1).capitalize()) if m else nombre
    fecha = None
    if m:
        fecha = datetime.strptime(m.group(2) + m.group(3), "%Y%m%d%H%M")
    entorno = "AWS EC2 c7i.large (Qolqe en el núcleo 1, k6 en el 0)" if "ec2" in nombre else "Docker en Windows (Qolqe a 1 CPU / 1 GB)"
    duracion = None
    h = carpeta / "horario.txt"
    if h.exists():
        t = re.findall(r"(\d\d:\d\d:\d\d)", h.read_text(encoding="utf-8"))
        if len(t) >= 2:
            a, b = (datetime.strptime(x, "%H:%M:%S") for x in t[:2])
            seg = (b - a).total_seconds()
            duracion = seg + 86400 if seg < 0 else seg
    return nombre, prueba, fecha, entorno, duracion


def valor_umbral(metricas, metrica, agg):
    v = metricas.get(metrica, {})
    if agg == "rate" and "passes" in v:  # Rate: k6 lo guarda como «value»
        return v.get("value")
    return v.get(agg if agg != "value" else "value")


def umbrales(summary):
    """[(métrica, condición, medido, incumplido)] en el orden de summary.json."""
    metricas = (summary or {}).get("metrics", {})
    filas = []
    for metrica, v in metricas.items():
        for expr, incumplido in (v.get("thresholds") or {}).items():
            m = UMBRAL.match(expr.strip())
            medido = valor_umbral(metricas, metrica, m.group(1)) if m else None
            filas.append((metrica, expr, medido, bool(incumplido)))
    return filas


def formatear_medido(metrica, expr, medido):
    if medido is None:
        return "—"
    agg = expr.split("<")[0].split(">")[0].split("=")[0].strip()
    if agg == "rate":
        return f"{dec(medido * 100, 2)} %"
    if agg == "count":
        return num(medido)
    return ms(medido)


def recursos(ruta):
    filas = leer_csv(ruta)
    cpu = [float(f["cpu_%"]) for f in filas if f.get("cpu_%") not in (None, "")]
    mem = [float(f["memoria_MB"]) for f in filas if f.get("memoria_MB") not in (None, "")]
    if not cpu:
        return None
    return {"cpu_prom": statistics.mean(cpu), "cpu_max": max(cpu), "mem_max": max(mem) if mem else None}


CSS = """
:root{color-scheme:light dark;--fondo:#f7f6f1;--sup:#fff;--borde:#dcd9cc;--texto:#1d2a22;--texto2:#4b5a50;--suave:#7a857e;
--ok:#1a7f4b;--mal:#c0392b;--aviso:#b7791f;--acento:#1f5d46;--acento-suave:#e3efe8}
@media (prefers-color-scheme:dark){:root{--fondo:#121a15;--sup:#1a241e;--borde:#2c3a31;--texto:#eef2ec;--texto2:#bcc8bf;--suave:#8a978e;
--ok:#4cc38a;--mal:#ef6f60;--aviso:#e6b04a;--acento:#7fc8a1;--acento-suave:#1d2c24}}
*{box-sizing:border-box}body{margin:0;background:var(--fondo);color:var(--texto);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 56px}h1{font-size:24px;margin:0 0 2px}h2{font-size:17px;margin:28px 0 8px}
.sub{color:var(--texto2);margin:0 0 4px}.nota{color:var(--suave);font-size:13px}
.veredicto{display:inline-block;font-weight:700;padding:3px 12px;border-radius:999px;border:1px solid currentColor;margin:10px 0}
.ok{color:var(--ok)}.mal{color:var(--mal)}.aviso{color:var(--aviso)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:14px 0}
.kpi{background:var(--sup);border:1px solid var(--borde);border-radius:10px;padding:12px 14px}
.kpi .etq{font-size:12.5px;color:var(--texto2)}.kpi .val{font-size:24px;font-weight:700;letter-spacing:-.01em}.kpi .det{font-size:12.5px;color:var(--suave)}
.tarjeta{background:var(--sup);border:1px solid var(--borde);border-radius:10px;padding:14px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}th{text-align:left;font-size:12.5px;color:var(--texto2);border-bottom:1px solid var(--borde);padding:6px 8px;white-space:nowrap}
td{padding:6px 8px;border-bottom:1px solid var(--borde);vertical-align:top}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:0}code{font:12.5px ui-monospace,Consolas,monospace}
img{max-width:100%;height:auto;border:1px solid var(--borde);border-radius:8px;background:#fff}
a{color:var(--acento)}details summary{cursor:pointer;color:var(--texto2);font-size:13.5px}
.chip{display:inline-block;font-size:12px;border:1px solid var(--borde);border-radius:6px;padding:0 6px;color:var(--texto2)}
.aviso-caja{background:var(--acento-suave);border-left:3px solid var(--acento);padding:8px 12px;border-radius:4px;font-size:13.5px;color:var(--texto2)}
"""


def pagina_corrida(carpeta):
    summary = leer_json(carpeta / "summary.json")
    if not summary:
        return None
    metricas = summary["metrics"]
    nombre, prueba, fecha, entorno, duracion = metadatos(carpeta)
    ums = umbrales(summary)
    fallan = [u for u in ums if u[3]]
    integridad = (carpeta / "integridad.txt").read_text(encoding="utf-8").strip().splitlines() if (carpeta / "integridad.txt").exists() else []
    integridad_ok = any(l.strip() == "INTEGRIDAD OK" for l in integridad)
    avisos_integridad = [l for l in integridad if l.startswith("AVISO")]

    reqs = metricas.get("http_reqs", {})
    fallas = metricas.get("http_req_failed", {}).get("passes", 0)
    total = reqs.get("count", 0)
    iters = metricas.get("iterations", {})
    vus = metricas.get("vus_max", {}).get("max") or metricas.get("vus_max", {}).get("value")
    q, k = recursos(carpeta / "recursos-qolqe.csv"), recursos(carpeta / "recursos-k6.csv")

    veredicto = ('<span class="veredicto ok">✓ Todos los umbrales cumplidos</span>' if not fallan else
                 f'<span class="veredicto mal">✗ {len(fallan)} de {len(ums)} umbrales incumplidos</span>')
    if prueba == "Estrés" and fallan:
        veredicto += ' <span class="nota">En el estrés es lo esperado: se sube la carga hasta que algo quiebre.</span>'

    def kpi(etq, val, det=""):
        return f'<div class="kpi"><div class="etq">{esc(etq)}</div><div class="val">{val}</div><div class="det">{det}</div></div>'

    kpis = [
        kpi("Peticiones HTTP", num(total), f"{dec(reqs.get('rate', 0), 1)} por segundo en promedio"),
        kpi("Fallas HTTP", f"{num(fallas)}", f"{dec(100 * fallas / total, 2) if total else '0'} % de las peticiones"),
        kpi("Iteraciones (sesiones)", num(iters.get("count", 0)), f"{dec(iters.get('rate', 0), 2)} por segundo"),
        kpi("Usuarios virtuales máx.", num(vus) if vus else "—"),
    ]
    if duracion:
        kpis.append(kpi("Duración", f"{int(duracion // 60)} min", f"{int(duracion)} s"))
    if q:
        kpis.append(kpi("CPU de Qolqe", f"{dec(q['cpu_prom'], 0)} %", f"máx. {dec(q['cpu_max'], 0)} %" + (f" · memoria máx. {dec(q['mem_max'], 0)} MB" if q["mem_max"] else "")))
    if k:
        kpis.append(kpi("CPU del generador (k6)", f"{dec(k['cpu_prom'], 1)} %", f"máx. {dec(k['cpu_max'], 0)} %"))
    if integridad:
        estado = ('<span class="ok">INTEGRIDAD OK</span>' if integridad_ok else '<span class="mal">revisar</span>')
        kpis.append(kpi("Integridad de los datos", estado, esc(integridad[0])))

    filas_um = "".join(
        f'<tr><td><code>{esc(m)}</code></td><td><code>{esc(e)}</code></td><td class="n">{esc(formatear_medido(m, e, v))}</td>'
        f'<td class="{"mal" if inc else "ok"}">{"✗ incumplido" if inc else "✓ cumplido"}</td></tr>' for m, e, v, inc in ums)

    def fila_trend(etq, clave):
        v = metricas.get(clave)
        if not v:
            return ""
        return (f'<tr><td>{esc(etq)}</td>' + "".join(f'<td class="n">{ms(v.get(c))}</td>' for c in ("avg", "med", "p(90)", "p(95)", "p(99)", "max")) + "</tr>")

    latencia = (fila_trend("Todas las peticiones", "http_req_duration") + fila_trend("Consultas (tipo consulta)", "http_req_duration{tipo:consulta}")
                + fila_trend("Operaciones de dinero (tipo dinero)", "http_req_duration{tipo:dinero}") + fila_trend("Sesión completa (iteración)", "iteration_duration"))

    endpoints = leer_csv(carpeta / "por-endpoint.csv")
    filas_ep = "".join(f'<tr><td><code>{esc(e["endpoint"])}</code></td><td class="n">{num(float(e["peticiones"]))}</td>'
                       f'<td class="n">{esc(e["p95_ms"])} ms</td><td class="n">{esc(e["max_ms"])} ms</td></tr>'
                       for e in sorted(endpoints, key=lambda e: -float(e["peticiones"])))
    minutos = leer_csv(carpeta / "por-minuto.csv")
    filas_min = "".join("<tr>" + f'<td>{esc(f["minuto"])}</td><td class="n">{esc(f["vus"])}</td><td class="n">{esc(f["req_s"])}</td>'
                        f'<td class="n">{esc(f["p95_consulta_ms"])}</td><td class="n">{esc(f["p95_dinero_ms"])}</td><td class="n">{esc(f["fallas_%"])}</td></tr>' for f in minutos)

    imagenes = "".join(f'<p><img src="{n}" alt="{esc(t)}"></p>' for n, t in (("k6.png", "Gráfico de k6"), ("recursos.png", "Recursos de Qolqe y del generador"))
                       if (carpeta / n).exists())
    enlaces = " · ".join(f'<a href="{n}">{n}</a>' for n in ("dashboard.html", "k6.txt", "summary.json", "por-minuto.csv", "por-endpoint.csv", "integridad.txt") if (carpeta / n).exists())
    nota = NOTAS.get(nombre)

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resumen · {esc(nombre)}</title><style>{CSS}</style></head><body><main>
<p class="nota"><a href="../index.html">← Todas las corridas</a></p>
<h1>{esc(prueba)} · {fecha.strftime('%d/%m/%Y %H:%M') if fecha else ''}</h1>
<p class="sub">{esc(entorno)} · carpeta <code>{esc(nombre)}</code></p>
{f'<p class="aviso-caja">{esc(nota)}</p>' if nota else ''}
{veredicto}
<div class="kpis">{''.join(kpis)}</div>
{''.join(f'<p class="aviso-caja">{esc(a)}</p>' for a in avisos_integridad)}
<h2>Umbrales (criterios de aceptación)</h2>
<div class="tarjeta"><table><tr><th>Métrica</th><th>Condición</th><th class="n">Medido</th><th>Resultado</th></tr>{filas_um or '<tr><td colspan="4">Sin umbrales.</td></tr>'}</table></div>
<h2>Latencia</h2>
<div class="tarjeta"><table><tr><th>Medida</th><th class="n">Promedio</th><th class="n">Mediana</th><th class="n">p90</th><th class="n">p95</th><th class="n">p99</th><th class="n">Máx.</th></tr>{latencia}</table></div>
<p class="nota">El dashboard de k6 solo muestra la fila «Todas las peticiones»; el corte por tipo sale de las etiquetas que pone <code>qolqe.js</code>.</p>
{f'<h2>Por endpoint</h2><div class="tarjeta"><table><tr><th>Endpoint</th><th class="n">Peticiones</th><th class="n">p95</th><th class="n">Máx.</th></tr>{filas_ep}</table></div>' if filas_ep else ''}
{f'<h2>Por minuto</h2><div class="tarjeta"><details {"open" if len(minutos) <= 12 else ""}><summary>{len(minutos)} minutos (usuarios, peticiones por segundo, p95 en ms, % de fallas)</summary><table><tr><th>Minuto</th><th class="n">Usuarios</th><th class="n">Req/s</th><th class="n">p95 consulta</th><th class="n">p95 dinero</th><th class="n">Fallas %</th></tr>{filas_min}</table></details></div>' if filas_min else ''}
{f'<h2>Gráficos</h2>{imagenes}' if imagenes else ''}
<h2>Archivos de la corrida</h2><p>{enlaces}</p>
<p class="nota">Datos de k6 (<code>summary.json</code>, <code>k6.json.gz</code>), de <code>monitor.py</code> (recursos) y de la verificación de integridad. Generado por <code>resumen.py</code>.</p>
</main></body></html>"""


def pagina_indice(corridas):
    orden = list(PRUEBAS)

    def clave(c):
        """Primero las del informe .docx, luego las de EC2 y al final las históricas; dentro, humo → carga → pico → estrés."""
        n = c.name
        grupo = 0 if "Informe_Rendimiento_G3.docx" in NOTAS.get(n, "") else 1 if "ec2" in n else 2
        prueba = n.split("-")[0]
        return grupo, orden.index(prueba) if prueba in orden else 9, n

    filas = []
    for carpeta in sorted(corridas, key=clave):
        s = leer_json(carpeta / "summary.json")
        if not s:
            continue
        nombre, prueba, fecha, entorno, duracion = metadatos(carpeta)
        m = s["metrics"]
        ums = umbrales(s)
        fallan = sum(1 for u in ums if u[3])
        total = m.get("http_reqs", {}).get("count", 0)
        f = m.get("http_req_failed", {}).get("passes", 0)
        cons, din = m.get("http_req_duration{tipo:consulta}", {}).get("p(95)"), m.get("http_req_duration{tipo:dinero}", {}).get("p(95)")
        ok = '<span class="ok">✓ cumple</span>' if not fallan else f'<span class="mal">✗ {fallan}/{len(ums)}</span>'
        filas.append(f'<tr><td><a href="{esc(nombre)}/resumen.html">{esc(prueba)}</a><br><span class="nota">{fecha.strftime("%d/%m %H:%M") if fecha else ""}</span></td>'
                     f'<td>{"EC2" if "ec2" in nombre else "Docker"}</td><td class="n">{num(total)}</td><td class="n">{num(f)}</td>'
                     f'<td class="n">{ms(cons)}</td><td class="n">{ms(din)}</td><td style="white-space:nowrap">{ok}</td><td class="nota">{esc(NOTAS.get(nombre, ""))}</td></tr>')
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resultados de rendimiento · Qolqe</title><style>{CSS}</style></head><body><main>
<h1>Resultados de rendimiento · Qolqe Wallet</h1>
<p class="sub">Corridas de k6 (Parte 3). Clic en el nombre para ver el resumen completo de cada una.</p>
<div class="tarjeta"><table><tr><th>Prueba</th><th>Entorno</th><th class="n">Peticiones</th><th class="n">Fallas</th><th class="n">p95 consulta</th><th class="n">p95 dinero</th><th>Umbrales</th><th>Por qué se conserva</th></tr>{''.join(filas)}</table></div>
<p class="nota">La carpeta <code>comparativa-20261111-2236</code> es la medición k6 contra Locust (<code>docs/comparativa-rendimiento.md</code>) y no tiene resumen.
Cada <code>resumen.html</code> muestra lo que el dashboard de k6 no trae: percentiles por tipo de operación, veredicto de cada umbral y totales exactos.</p>
</main></body></html>"""


def main():
    if len(sys.argv) > 1:
        carpeta = Path(sys.argv[1]).resolve()
        pagina = pagina_corrida(carpeta)
        if pagina is None:
            sys.exit(f"{carpeta}: no hay summary.json")
        (carpeta / "resumen.html").write_text(pagina, encoding="utf-8")
        print(f"Resumen: {carpeta / 'resumen.html'}")
        return
    corridas = [c for c in sorted(RESULTADOS.iterdir()) if c.is_dir() and (c / "summary.json").exists()]
    for c in corridas:
        (c / "resumen.html").write_text(pagina_corrida(c), encoding="utf-8")
    (RESULTADOS / "index.html").write_text(pagina_indice(corridas), encoding="utf-8")
    print(f"{len(corridas)} resúmenes e índice: {RESULTADOS / 'index.html'}")


if __name__ == "__main__":
    main()
